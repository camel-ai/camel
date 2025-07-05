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
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional

from camel.logger import get_logger

from .actions import ActionExecutor
from .snapshot import PageSnapshot
from .stealth_config import StealthConfig

if TYPE_CHECKING:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Page,
        Playwright,
    )

logger = get_logger(__name__)


class NVBrowserSession:
    """Lightweight wrapper around Playwright for
    browsing with multi-tab support.

    It provides multiple *Page* instances plus helper utilities (snapshot &
    executor).  Multiple toolkits or agents can reuse this class without
    duplicating Playwright setup code.

    This class is a singleton per event-loop.
    """

    # Configuration constants
    DEFAULT_NAVIGATION_TIMEOUT = 10000  # 10 seconds
    NETWORK_IDLE_TIMEOUT = 5000  # 5 seconds

    _sessions: ClassVar[
        Dict[asyncio.AbstractEventLoop, "NVBrowserSession"]
    ] = {}

    _initialized: bool

    def __new__(
        cls,
        *,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        stealth: bool = False,
    ) -> "NVBrowserSession":
        # Defer event loop lookup until we actually need it
        # This allows creation outside of async context
        instance = super().__new__(cls)
        instance._initialized = False
        return instance

    def __init__(
        self,
        *,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
        stealth: bool = False,
    ):
        if self._initialized:
            return
        self._initialized = True

        self._headless = headless
        self._user_data_dir = user_data_dir
        self._stealth = stealth

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        # Multi-tab support
        self._pages: List[Page] = []  # All tabs
        self._current_tab_index: int = 0  # Current active tab index

        self.snapshot: Optional[PageSnapshot] = None
        self.executor: Optional[ActionExecutor] = None

        # Protect browser initialisation against concurrent calls
        self._ensure_lock: "asyncio.Lock" = asyncio.Lock()

        # Load stealth script and config on initialization
        self._stealth_script: Optional[str] = None
        self._stealth_config: Optional[Dict[str, Any]] = None
        if self._stealth:
            self._stealth_script = self._load_stealth_script()
            self._stealth_config = StealthConfig.get_all_config()

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
    async def create_new_tab(self, url: Optional[str] = None) -> int:
        r"""Create a new tab and optionally navigate to a URL.

        Args:
            url: Optional URL to navigate to in the new tab

        Returns:
            int: Index of the newly created tab
        """
        await self.ensure_browser()

        if self._context is None:
            raise RuntimeError("Browser context is not available")

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

        # Add to our pages list
        self._pages.append(new_page)
        new_tab_index = len(self._pages) - 1

        # Navigate if URL provided
        if url:
            try:
                await new_page.goto(
                    url, timeout=self.DEFAULT_NAVIGATION_TIMEOUT
                )
                await new_page.wait_for_load_state('domcontentloaded')
            except Exception as e:
                logger.warning(f"Failed to navigate new tab to {url}: {e}")

        logger.info(
            f"Created new tab {new_tab_index}, total tabs: {len(self._pages)}"
        )
        return new_tab_index

    async def register_page(self, new_page: "Page") -> int:
        r"""Register a page that was created externally (e.g., by a click).

        Args:
            new_page (Page): The new page object to register.

        Returns:
            int: The index of the (newly) registered tab.
        """
        if new_page in self._pages:
            try:
                # Page is already known, just return its index
                return self._pages.index(new_page)
            except ValueError:
                # Should not happen if `in` check passed, but handle anyway
                pass

        # Add new page to our list
        self._pages.append(new_page)
        new_tab_index = len(self._pages) - 1
        logger.info(
            f"Registered new tab {new_tab_index} (opened by user action). "
            f"Total tabs: {len(self._pages)}"
        )
        return new_tab_index

    async def switch_to_tab(self, tab_index: int) -> bool:
        r"""Switch to a specific tab by index.

        Args:
            tab_index: Index of the tab to switch to

        Returns:
            bool: True if successful, False if tab index is invalid
        """
        if not self._pages or tab_index < 0 or tab_index >= len(self._pages):
            logger.warning(
                f"Invalid tab index {tab_index}, available tabs: "
                f"{len(self._pages)}"
            )
            return False

        # Check if the page is still valid
        try:
            page = self._pages[tab_index]
            if page.is_closed():
                logger.warning(
                    f"Tab {tab_index} is closed, removing from list"
                )
                self._pages.pop(tab_index)
                # Adjust current tab index if necessary
                if self._current_tab_index >= len(self._pages):
                    self._current_tab_index = max(0, len(self._pages) - 1)
                return False
        except Exception as e:
            logger.warning(f"Error checking tab {tab_index}: {e}")
            return False

        self._current_tab_index = tab_index
        self._page = self._pages[tab_index]

        # Bring the tab to the front in the browser window
        await self._page.bring_to_front()

        # Update executor and snapshot for new tab
        self.executor = ActionExecutor(self._page, self)
        self.snapshot = PageSnapshot(self._page)

        logger.info(f"Switched to tab {tab_index}")
        return True

    async def close_tab(self, tab_index: int) -> bool:
        r"""Close a specific tab.

        Args:
            tab_index: Index of the tab to close

        Returns:
            bool: True if successful, False if tab index is invalid
        """
        if not self._pages or tab_index < 0 or tab_index >= len(self._pages):
            return False

        try:
            page = self._pages[tab_index]
            if not page.is_closed():
                await page.close()

            # Remove from our list
            self._pages.pop(tab_index)

            # If we closed the current tab, switch to another one
            if tab_index == self._current_tab_index:
                if self._pages:
                    # Switch to the previous tab, or first tab if we closed
                    # the first one
                    new_index = max(
                        0, min(tab_index - 1, len(self._pages) - 1)
                    )
                    await self.switch_to_tab(new_index)
                else:
                    # No tabs left
                    self._current_tab_index = 0
                    self._page = None
                    self.executor = None
                    self.snapshot = None
            elif tab_index < self._current_tab_index:
                # Adjust current tab index since we removed a tab before it
                self._current_tab_index -= 1

            logger.info(
                f"Closed tab {tab_index}, remaining tabs: {len(self._pages)}"
            )
            return True

        except Exception as e:
            logger.warning(f"Error closing tab {tab_index}: {e}")
            return False

    async def get_tab_info(self) -> List[Dict[str, Any]]:
        r"""Get information about all open tabs.

        Returns:
            List of dictionaries containing tab information
        """
        tab_info = []
        for i, page in enumerate(self._pages):
            try:
                if not page.is_closed():
                    title = await page.title()
                    url = page.url
                    is_current = i == self._current_tab_index
                    tab_info.append(
                        {
                            "index": i,
                            "title": title,
                            "url": url,
                            "is_current": is_current,
                        }
                    )
                else:
                    # Mark closed tab for removal
                    tab_info.append(
                        {
                            "index": i,
                            "title": "[CLOSED]",
                            "url": "",
                            "is_current": False,
                        }
                    )
            except Exception as e:
                logger.warning(f"Error getting info for tab {i}: {e}")
                tab_info.append(
                    {
                        "index": i,
                        "title": "[ERROR]",
                        "url": "",
                        "is_current": False,
                    }
                )

        return tab_info

    async def get_current_tab_index(self) -> int:
        r"""Get the index of the current active tab."""
        return self._current_tab_index

    # ------------------------------------------------------------------
    # Browser lifecycle helpers
    # ------------------------------------------------------------------
    async def ensure_browser(self) -> None:
        r"""Ensure browser is ready, implementing singleton pattern per event
        loop.
        """
        # Check if we need to reuse or create a session for this event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError as e:
            raise RuntimeError(
                "ensure_browser() must be called from within an async context"
            ) from e

        # Check if there's already a session for this loop
        if loop in self._sessions and self._sessions[loop] is not self:
            # Copy the existing session's browser resources
            existing = self._sessions[loop]
            # Wait for existing session to be fully initialized
            async with existing._ensure_lock:
                if (
                    existing._initialized
                    and existing._page is not None
                    and existing._playwright is not None
                ):
                    try:
                        # Verify the page is still responsive
                        await existing._page.title()
                        self._playwright = existing._playwright
                        self._browser = existing._browser
                        self._context = existing._context
                        self._page = existing._page
                        self._pages = existing._pages
                        self._current_tab_index = existing._current_tab_index
                        self.snapshot = existing.snapshot
                        self.executor = existing.executor
                        self._initialized = True
                        return
                    except Exception:
                        # Existing session is broken, continue with new
                        # initialization
                        pass

        # Register this instance for the current loop
        self._sessions[loop] = self

        # Serialise initialisation to avoid race conditions where multiple
        # concurrent coroutine calls create multiple browser instances for
        # the same NVBrowserSession.
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
                self._pages = list(pages)
            else:
                self._page = await context.new_page()
                self._pages = [self._page]
        else:
            self._browser = await self._playwright.chromium.launch(
                **launch_options
            )
            self._context = await self._browser.new_context(**context_options)
            self._page = await self._context.new_page()
            self._pages = [self._page]

        # Apply stealth modifications if enabled
        if self._stealth and self._stealth_script:
            try:
                await self._page.add_init_script(self._stealth_script)
                logger.debug("Applied stealth script to main page")
            except Exception as e:
                logger.warning(f"Failed to apply stealth script: {e}")

        # Set up timeout for navigation
        self._page.set_default_navigation_timeout(
            self.DEFAULT_NAVIGATION_TIMEOUT
        )
        self._page.set_default_timeout(self.DEFAULT_NAVIGATION_TIMEOUT)

        # Initialize utilities
        self.snapshot = PageSnapshot(self._page)
        self.executor = ActionExecutor(self._page, self)
        self._current_tab_index = 0

        logger.info("Browser session initialized successfully")

    async def close(self) -> None:
        r"""Close browser session and clean up resources."""
        if self._page is None:
            return

        try:
            logger.debug("Closing browser session...")
            await self._close_session()
            logger.debug("Browser session closed successfully")
        except Exception as e:
            logger.error(f"Error during browser session close: {e}")
        finally:
            self._page = None
            self._pages = []
            self._current_tab_index = 0
            self.snapshot = None
            self.executor = None

    async def _close_session(self) -> None:
        r"""Internal session close logic."""
        # Close all pages
        for page in self._pages:
            try:
                if not page.is_closed():
                    await page.close()
            except Exception as e:
                logger.warning(f"Error closing page: {e}")

        # Close context
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None

        # Close browser
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None

        # Stop playwright - give it time to clean up subprocesses
        if self._playwright:
            try:
                await self._playwright.stop()
                # Small delay to allow subprocess cleanup
                import asyncio

                await asyncio.sleep(0.1)
            except Exception:
                pass
            self._playwright = None

    @classmethod
    async def close_all_sessions(cls) -> None:
        r"""Close all browser sessions across all event loops."""
        sessions_to_close = list(cls._sessions.values())
        cls._sessions.clear()

        logger.debug(f"Closing {len(sessions_to_close)} browser sessions...")
        for session in sessions_to_close:
            try:
                await session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")

        if sessions_to_close:
            # Give extra time for all processes to terminate
            import asyncio

            await asyncio.sleep(0.2)
            logger.debug("All browser sessions closed")

    # ------------------------------------------------------------------
    # Page interaction
    # ------------------------------------------------------------------
    async def visit(self, url: str) -> str:
        r"""Navigate current tab to URL."""
        await self.ensure_browser()
        page = await self.get_page()

        await page.goto(url, timeout=self.DEFAULT_NAVIGATION_TIMEOUT)
        await page.wait_for_load_state('domcontentloaded')

        # Try to wait for network idle
        try:
            await page.wait_for_load_state(
                'networkidle', timeout=self.NETWORK_IDLE_TIMEOUT
            )
        except Exception:
            logger.debug("Network idle timeout - continuing anyway")

        return f"Navigated to {url}"

    async def get_snapshot(
        self, *, force_refresh: bool = False, diff_only: bool = False
    ) -> str:
        r"""Get snapshot for current tab."""
        if not self.snapshot:
            return "<empty>"
        return await self.snapshot.capture(
            force_refresh=force_refresh, diff_only=diff_only
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
