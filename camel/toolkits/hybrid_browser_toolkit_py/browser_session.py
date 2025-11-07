# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
from __future__ import annotations

import asyncio
from collections import deque
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Tuple

from camel.logger import get_logger

from .actions import ActionExecutor
from .config_loader import ConfigLoader
from .snapshot import PageSnapshot

if TYPE_CHECKING:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        ConsoleMessage,
        Page,
        Playwright,
    )

logger = get_logger(__name__)


class TabIdGenerator:
    """Monotonically increasing tab ID generator."""

    _counter: int = 0
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    @classmethod
    async def generate_tab_id(cls) -> str:
        """Generate a monotonically increasing tab ID."""
        async with cls._lock:
            cls._counter += 1
            return f"tab-{cls._counter:03d}"


class HybridBrowserSession:
    """Lightweight wrapper around Playwright for
    browsing with multi-tab support.

    It provides multiple *Page* instances plus helper utilities (snapshot &
    executor).  Multiple toolkits or agents can reuse this class without
    duplicating Playwright setup code.

    This class is a singleton per event-loop and session-id combination.
    """

    # Class-level registry for singleton instances
    # Format: {(loop_id, session_id): HybridBrowserSession}
    _instances: ClassVar[Dict[Tuple[Any, str], "HybridBrowserSession"]] = {}
    _instances_lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    _initialized: bool
    _creation_params: Dict[str, Any]

    def __new__(
        cls,
        *,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        stealth: bool = False,
        session_id: Optional[str] = None,
        default_timeout: Optional[int] = None,
        short_timeout: Optional[int] = None,
        navigation_timeout: Optional[int] = None,
        network_idle_timeout: Optional[int] = None,
    ) -> "HybridBrowserSession":
        # Create a unique key for this event loop and session combination
        # We defer the event loop lookup to avoid issues with creation
        # outside async context
        instance = super().__new__(cls)
        instance._initialized = False
        instance._session_id = session_id or "default"
        instance._creation_params = {
            "headless": headless,
            "user_data_dir": user_data_dir,
            "stealth": stealth,
            "session_id": session_id,
            "default_timeout": default_timeout,
            "short_timeout": short_timeout,
            "navigation_timeout": navigation_timeout,
            "network_idle_timeout": network_idle_timeout,
        }
        return instance

    @classmethod
    async def _get_or_create_instance(
        cls,
        instance: "HybridBrowserSession",
    ) -> "HybridBrowserSession":
        """Get or create singleton instance for the current event loop and
        session."""
        try:
            loop = asyncio.get_running_loop()
            loop_id = str(id(loop))
        except RuntimeError:
            # No event loop running, use a unique identifier for sync context
            import threading

            loop_id = f"sync_{threading.current_thread().ident}"

        # Ensure session_id is never None for the key
        session_id = (
            instance._session_id
            if instance._session_id is not None
            else "default"
        )
        session_key = (loop_id, session_id)

        # Use class-level lock to protect the instances registry
        async with cls._instances_lock:
            if session_key in cls._instances:
                existing_instance = cls._instances[session_key]
                logger.debug(
                    f"Reusing existing browser session for session_id: "
                    f"{session_id}"
                )
                return existing_instance

            # Register this new instance
            cls._instances[session_key] = instance
            logger.debug(
                f"Created new browser session for session_id: {session_id}"
            )
            return instance

    def __init__(
        self,
        *,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        stealth: bool = False,
        session_id: Optional[str] = None,
        default_timeout: Optional[int] = None,
        short_timeout: Optional[int] = None,
        navigation_timeout: Optional[int] = None,
        network_idle_timeout: Optional[int] = None,
    ):
        if self._initialized:
            return
        self._initialized = True

        self._headless = headless
        self._user_data_dir = user_data_dir
        self._stealth = stealth
        self._session_id = session_id or "default"

        # Store timeout configuration for ActionExecutor instances and
        # browser operations
        self._default_timeout = default_timeout
        self._short_timeout = short_timeout
        self._navigation_timeout = ConfigLoader.get_navigation_timeout(
            navigation_timeout
        )
        self._network_idle_timeout = ConfigLoader.get_network_idle_timeout(
            network_idle_timeout
        )

        # Initialize _creation_params to fix linter error
        self._creation_params = {
            "headless": headless,
            "user_data_dir": user_data_dir,
            "stealth": stealth,
            "session_id": session_id,
            "default_timeout": default_timeout,
            "short_timeout": short_timeout,
            "navigation_timeout": navigation_timeout,
            "network_idle_timeout": network_idle_timeout,
        }

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        # Dictionary-based tab management with monotonic IDs
        self._pages: Dict[str, Page] = {}  # tab_id -> Page object
        self._console_logs: Dict[str, Any] = {}  # tab_id -> page logs
        self._current_tab_id: Optional[str] = None  # Current active tab ID
        self.log_limit: int = ConfigLoader.get_max_log_limit() or 1000

        self.snapshot: Optional[PageSnapshot] = None
        self.executor: Optional[ActionExecutor] = None

        # Protect browser initialisation against concurrent calls
        self._ensure_lock: "asyncio.Lock" = asyncio.Lock()

        # Load stealth script and config on initialization
        self._stealth_script: Optional[str] = None
        self._stealth_config: Optional[Dict[str, Any]] = None
        if self._stealth:
            self._stealth_script = self._load_stealth_script()
            stealth_config_class = ConfigLoader.get_stealth_config()
            self._stealth_config = stealth_config_class.get_stealth_config()

    def _load_stealth_script(self) -> str:
        r"""Load the stealth JavaScript script from file."""
        import os

        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "stealth_script.js"
        )

        try:
            with open(
                script_path, "r", encoding='utf-8', errors='replace'
            ) as f:
                script_content = f.read()

            if not script_content.strip():
                raise ValueError(f"Stealth script is empty: {script_path}")

            logger.debug(
                f"Loaded stealth script ({len(script_content)} chars)"
            )
            return script_content
        except FileNotFoundError:
            logger.error(f"Stealth script not found: {script_path}")
            raise FileNotFoundError(f"Stealth script not found: {script_path}")
        except Exception as e:
            logger.error(f"Error loading stealth script: {e}")
            raise RuntimeError(f"Failed to load stealth script: {e}") from e

    # ------------------------------------------------------------------
    # Multi-tab management methods
    # ------------------------------------------------------------------
    async def create_new_tab(self, url: Optional[str] = None) -> str:
        r"""Create a new tab and optionally navigate to a URL.

        Args:
            url: Optional URL to navigate to in the new tab

        Returns:
            str: ID of the newly created tab
        """
        await self.ensure_browser()

        if self._context is None:
            raise RuntimeError("Browser context is not available")

        # Generate unique tab ID
        tab_id = await TabIdGenerator.generate_tab_id()

        # Create new page
        new_page = await self._context.new_page()

        # Apply stealth modifications if enabled
        if self._stealth and self._stealth_script:
            try:
                await new_page.add_init_script(self._stealth_script)
                logger.debug("Applied stealth script to new tab")
            except Exception as e:
                logger.warning(
                    f"Failed to apply stealth script to new tab: {e}"
                )

        # Store in pages dictionary
        await self._register_new_page(tab_id, new_page)

        # Navigate if URL provided
        if url:
            try:
                await new_page.goto(url, timeout=self._navigation_timeout)
                await new_page.wait_for_load_state('domcontentloaded')
            except Exception as e:
                logger.warning(f"Failed to navigate new tab to {url}: {e}")

        logger.info(
            f"Created new tab {tab_id}, total tabs: {len(self._pages)}"
        )
        return tab_id

    async def _register_new_page(self, tab_id: str, new_page: "Page") -> None:
        r"""Register a page and add console event listerers.

        Args:
            new_page (Page): The new page object to register.
        """
        # Add new page
        self._pages[tab_id] = new_page
        # Create log for the page
        self._console_logs[tab_id] = deque(maxlen=self.log_limit)

        # Add event function
        def handle_console_log(msg: ConsoleMessage):
            logs = self._console_logs.get(tab_id)
            if logs is not None:
                logs.append({"type": msg.type, "text": msg.text})

        # Add event listener for console logs
        new_page.on(event="console", f=handle_console_log)

        def handle_page_close(page: "Page"):
            self._console_logs.pop(tab_id, None)

        # Add event listener for cleanup
        new_page.on(event="close", f=handle_page_close)

    async def register_page(self, new_page: "Page") -> str:
        r"""Register a page that was created externally (e.g., by a click).

        Args:
            new_page (Page): The new page object to register.

        Returns:
            str: The ID of the (newly) registered tab.
        """
        # Check if page is already registered
        for tab_id, page in self._pages.items():
            if page is new_page:
                return tab_id

        # Create new ID for the page
        tab_id = await TabIdGenerator.generate_tab_id()
        await self._register_new_page(tab_id, new_page)

        logger.info(
            f"Registered new tab {tab_id} (opened by user action). "
            f"Total tabs: {len(self._pages)}"
        )
        return tab_id

    async def switch_to_tab(self, tab_id: str) -> bool:
        r"""Switch to a specific tab by ID.

        Args:
            tab_id: ID of the tab to switch to

        Returns:
            bool: True if successful, False if tab ID is invalid
        """
        if tab_id not in self._pages:
            logger.warning(f"Invalid tab ID: {tab_id}")
            return False

        page = self._pages[tab_id]

        # Check if page is still valid
        if page.is_closed():
            logger.warning(f"Tab {tab_id} is closed, removing from registry")
            # Clean up closed tab
            del self._pages[tab_id]
            return False

        try:
            # Switch to the tab
            self._current_tab_id = tab_id
            self._page = page

            # Bring the tab to the front in the browser window
            await page.bring_to_front()

            # Update utilities for new tab
            self.executor = ActionExecutor(
                page,
                self,
                default_timeout=self._default_timeout,
                short_timeout=self._short_timeout,
            )
            self.snapshot = PageSnapshot(page)

            logger.info(f"Switched to tab {tab_id}")
            return True

        except Exception as e:
            logger.warning(f"Error switching to tab {tab_id}: {e}")
            return False

    async def close_tab(self, tab_id: str) -> bool:
        r"""Close a specific tab by ID.

        Args:
            tab_id: ID of the tab to close

        Returns:
            bool: True if successful, False if tab ID is invalid
        """
        if tab_id not in self._pages:
            logger.warning(f"Invalid tab ID: {tab_id}")
            return False

        page = self._pages[tab_id]

        try:
            # Close the page if not already closed
            if not page.is_closed():
                await page.close()

            # Remove from our dictionary
            del self._pages[tab_id]

            # If we closed the current tab, switch to another one
            if tab_id == self._current_tab_id:
                if self._pages:
                    # Switch to any available tab (first one we find)
                    next_tab_id = next(iter(self._pages.keys()))
                    await self.switch_to_tab(next_tab_id)
                else:
                    # No tabs left
                    self._current_tab_id = None
                    self._page = None
                    self.executor = None
                    self.snapshot = None

            logger.info(
                f"Closed tab {tab_id}, remaining tabs: {len(self._pages)}"
            )
            return True

        except Exception as e:
            logger.warning(f"Error closing tab {tab_id}: {e}")
            return False

    async def get_tab_info(self) -> List[Dict[str, Any]]:
        r"""Get information about all open tabs including IDs.

        Returns:
            List of dictionaries containing tab information
        """
        tab_info = []
        tabs_to_cleanup = []

        # Process all tabs in dictionary
        for tab_id, page in list(self._pages.items()):
            try:
                if not page.is_closed():
                    title = await page.title()
                    url = page.url
                    is_current = tab_id == self._current_tab_id
                    tab_info.append(
                        {
                            "tab_id": tab_id,
                            "title": title,
                            "url": url,
                            "is_current": is_current,
                        }
                    )
                else:
                    # Mark for cleanup
                    tabs_to_cleanup.append(tab_id)
            except Exception as e:
                logger.warning(f"Error getting info for tab {tab_id}: {e}")
                tabs_to_cleanup.append(tab_id)

        # Clean up closed/invalid tabs
        for tab_id in tabs_to_cleanup:
            if tab_id in self._pages:
                del self._pages[tab_id]

        return tab_info

    async def get_current_tab_id(self) -> Optional[str]:
        r"""Get the id for the current active tab."""
        if not self._current_tab_id or not self._pages:
            return None
        return self._current_tab_id

    # ------------------------------------------------------------------
    # Browser lifecycle helpers
    # ------------------------------------------------------------------
    async def ensure_browser(self) -> None:
        r"""Ensure browser is ready. Each session_id gets its own browser
        instance."""
        # First, get the singleton instance for this session
        singleton_instance = await self._get_or_create_instance(self)

        # If this isn't the singleton instance, delegate to the singleton
        if singleton_instance is not self:
            await singleton_instance.ensure_browser()
            # Copy the singleton's browser state to this instance
            self._playwright = singleton_instance._playwright
            self._browser = singleton_instance._browser
            self._context = singleton_instance._context
            self._page = singleton_instance._page
            self._pages = singleton_instance._pages
            self._console_logs = singleton_instance._console_logs
            self._current_tab_id = singleton_instance._current_tab_id
            self.snapshot = singleton_instance.snapshot
            self.executor = singleton_instance.executor
            return

        # Serialise initialisation to avoid race conditions where multiple
        # concurrent coroutine calls create multiple browser instances for
        # the same HybridBrowserSession.
        async with self._ensure_lock:
            await self._ensure_browser_inner()

    # Moved original logic to helper
    async def _ensure_browser_inner(self) -> None:
        r"""Internal browser initialization logic."""
        from playwright.async_api import async_playwright

        if self._page is not None:
            return

        self._playwright = await async_playwright().start()

        # Prepare stealth options
        launch_options: Dict[str, Any] = {"headless": self._headless}
        context_options: Dict[str, Any] = {}
        if self._stealth and self._stealth_config:
            # Use preloaded stealth configuration
            launch_options['args'] = self._stealth_config['launch_args']
            context_options.update(self._stealth_config['context_options'])

        if self._user_data_dir:
            context = (
                await self._playwright.chromium.launch_persistent_context(
                    user_data_dir=self._user_data_dir,
                    **launch_options,
                    **context_options,
                )
            )
            self._context = context
            # Get the first (default) page
            pages = context.pages
            if pages:
                self._page = pages[0]
                # Create ID for initial page
                initial_tab_id = await TabIdGenerator.generate_tab_id()
                await self._register_new_page(initial_tab_id, pages[0])
                self._current_tab_id = initial_tab_id
                # Handle additional pages if any
                for page in pages[1:]:
                    tab_id = await TabIdGenerator.generate_tab_id()
                    await self._register_new_page(tab_id, page)
            else:
                self._page = await context.new_page()
                initial_tab_id = await TabIdGenerator.generate_tab_id()
                await self._register_new_page(initial_tab_id, self._page)
                self._current_tab_id = initial_tab_id
        else:
            self._browser = await self._playwright.chromium.launch(
                **launch_options
            )
            self._context = await self._browser.new_context(**context_options)
            self._page = await self._context.new_page()

            # Create ID for initial page
            initial_tab_id = await TabIdGenerator.generate_tab_id()
            await self._register_new_page(initial_tab_id, self._page)
            self._current_tab_id = initial_tab_id

        # Apply stealth modifications if enabled
        if self._stealth and self._stealth_script:
            try:
                await self._page.add_init_script(self._stealth_script)
                logger.debug("Applied stealth script to main page")
            except Exception as e:
                logger.warning(f"Failed to apply stealth script: {e}")

        # Set up timeout for navigation
        self._page.set_default_navigation_timeout(self._navigation_timeout)
        self._page.set_default_timeout(self._navigation_timeout)

        # Initialize utilities
        self.snapshot = PageSnapshot(self._page)
        self.executor = ActionExecutor(
            self._page,
            self,
            default_timeout=self._default_timeout,
            short_timeout=self._short_timeout,
        )

        logger.info("Browser session initialized successfully")

    async def close(self) -> None:
        r"""Close browser session and clean up resources."""
        if self._page is None:
            return

        try:
            logger.debug("Closing browser session...")
            await self._close_session()

            # Remove from singleton registry
            try:
                try:
                    loop = asyncio.get_running_loop()
                    loop_id = str(id(loop))
                except RuntimeError:
                    # Use same logic as _get_or_create_instance
                    import threading

                    loop_id = f"sync_{threading.current_thread().ident}"

                session_id = (
                    self._session_id
                    if self._session_id is not None
                    else "default"
                )
                session_key = (loop_id, session_id)

                async with self._instances_lock:
                    if (
                        session_key in self._instances
                        and self._instances[session_key] is self
                    ):
                        del self._instances[session_key]
                        logger.debug(
                            f"Removed session {session_id} from registry"
                        )

            except Exception as registry_error:
                logger.warning(f"Error cleaning up registry: {registry_error}")

            logger.debug("Browser session closed successfully")
        except Exception as e:
            logger.error(f"Error during browser session close: {e}")
        finally:
            self._page = None
            self._pages = {}
            self._current_tab_id = None
            self.snapshot = None
            self.executor = None

    async def _close_session(self) -> None:
        r"""Internal session close logic with thorough cleanup."""
        try:
            # Close all pages first
            pages_to_close = list(self._pages.values())
            for page in pages_to_close:
                try:
                    if not page.is_closed():
                        await page.close()
                        logger.debug(
                            f"Closed page: "
                            f"{page.url if hasattr(page, 'url') else 'unknown'}"  # noqa:E501
                        )
                except Exception as e:
                    logger.warning(f"Error closing page: {e}")

            # Clear the pages dictionary
            self._pages.clear()

            # Close context with explicit wait
            if self._context:
                try:
                    await self._context.close()
                    logger.debug("Browser context closed")
                except Exception as e:
                    logger.warning(f"Error closing context: {e}")
                finally:
                    self._context = None

            # Close browser with explicit wait
            if self._browser:
                try:
                    await self._browser.close()
                    logger.debug("Browser instance closed")
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
                finally:
                    self._browser = None

            # Stop playwright with increased delay for cleanup
            if self._playwright:
                try:
                    await self._playwright.stop()
                    logger.debug("Playwright stopped")

                    # Give more time for complete subprocess cleanup
                    import asyncio

                    await asyncio.sleep(0.5)

                except Exception as e:
                    logger.warning(f"Error stopping playwright: {e}")
                finally:
                    self._playwright = None

        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
        finally:
            # Ensure all attributes are cleared regardless of errors
            self._page = None
            self._pages = {}
            self._current_tab_id = None
            self._context = None
            self._browser = None
            self._playwright = None

    @classmethod
    async def close_all_sessions(cls) -> None:
        r"""Close all browser sessions and clean up the singleton registry."""
        logger.debug("Closing all browser sessions...")
        async with cls._instances_lock:
            # Close all active sessions
            instances_to_close = list(cls._instances.values())
            cls._instances.clear()
            logger.debug(f"Closing {len(instances_to_close)} sessions.")

        # Close sessions outside the lock to avoid deadlock
        for instance in instances_to_close:
            try:
                await instance._close_session()
                logger.debug(f"Closed session: {instance._session_id}")
            except Exception as e:
                logger.error(
                    f"Error closing session {instance._session_id}: {e}"
                )

        logger.debug("All browser sessions closed and registry cleared")

    @classmethod
    async def close_all(cls) -> None:
        """Alias for close_all_sessions for backward compatibility."""
        await cls.close_all_sessions()

    # ------------------------------------------------------------------
    # Page interaction
    # ------------------------------------------------------------------
    async def visit(self, url: str) -> str:
        r"""Navigate current tab to URL."""
        await self.ensure_browser()
        page = await self.get_page()

        await page.goto(url, timeout=self._navigation_timeout)
        await page.wait_for_load_state('domcontentloaded')

        # Try to wait for network idle
        try:
            await page.wait_for_load_state(
                'networkidle', timeout=self._network_idle_timeout
            )
        except Exception:
            logger.debug("Network idle timeout - continuing anyway")

        return f"Navigated to {url}"

    async def get_snapshot(
        self,
        *,
        force_refresh: bool = False,
        diff_only: bool = False,
        viewport_limit: bool = False,
    ) -> str:
        r"""Get snapshot for current tab."""
        if not self.snapshot:
            return "<empty>"
        return await self.snapshot.capture(
            force_refresh=force_refresh,
            diff_only=diff_only,
            viewport_limit=viewport_limit,
        )

    async def exec_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        r"""Execute action on current tab."""
        if not self.executor:
            return {
                "success": False,
                "message": "No executor available",
                "details": {},
            }
        return await self.executor.execute(action)

    async def get_page(self) -> "Page":
        r"""Get current active page."""
        await self.ensure_browser()
        if self._page is None:
            raise RuntimeError("No active page available")
        return self._page

    async def get_console_logs(self) -> Dict[str, Any]:
        r"""Get current active logs."""
        await self.ensure_browser()
        if self._current_tab_id is None:
            raise RuntimeError("No active tab available")
        logs = self._console_logs.get(self._current_tab_id, None)
        if logs is None:
            raise RuntimeError("No active logs available for the page")
        return logs
