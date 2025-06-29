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
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Optional

from camel.logger import get_logger

from .actions import ActionExecutor
from .snapshot import PageSnapshot

if TYPE_CHECKING:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Page,
        Playwright,
    )


logger = get_logger(__name__)


class NVBrowserSession:
    """Lightweight wrapper around Playwright for non-visual (headless)
    browsing.

    It provides a single *Page* instance plus helper utilities (snapshot &
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
        cls, *, headless: bool = True, user_data_dir: Optional[str] = None
    ) -> "NVBrowserSession":
        # Defer event loop lookup until we actually need it
        # This allows creation outside of async context
        instance = super().__new__(cls)
        instance._initialized = False
        return instance

    def __init__(
        self, *, headless: bool = True, user_data_dir: Optional[str] = None
    ):
        if self._initialized:
            return
        self._initialized = True

        self._headless = headless
        self._user_data_dir = user_data_dir

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        self.snapshot: Optional[PageSnapshot] = None
        self.executor: Optional[ActionExecutor] = None

        # Protect browser initialisation against concurrent calls
        self._ensure_lock: "asyncio.Lock" = asyncio.Lock()

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
        if self._user_data_dir:
            Path(self._user_data_dir).mkdir(parents=True, exist_ok=True)
            pl = self._playwright
            assert pl is not None
            self._context = await pl.chromium.launch_persistent_context(
                user_data_dir=self._user_data_dir,
                headless=self._headless,
            )
            self._browser = self._context.browser
        else:
            pl = self._playwright
            assert pl is not None
            self._browser = await pl.chromium.launch(headless=self._headless)
            self._context = await self._browser.new_context()

        # Reuse an already open page (persistent context may restore last
        # session)
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()

        # Debug information to help trace concurrency issues
        logger.debug(
            "Session %s created browser=%s context=%s page=%s (url=%s)",
            hex(id(self)),
            hex(id(self._browser)) if self._browser else None,
            hex(id(self._context)) if self._context else None,
            hex(id(self._page)),
            self._page.url if self._page else "<none>",
        )

        # helpers
        self.snapshot = PageSnapshot(self._page)
        self.executor = ActionExecutor(self._page)

    async def close(self) -> None:
        r"""Close all browser resources, ensuring cleanup even if some
        operations fail.
        """
        # Remove this session from the sessions dict and close resources
        try:
            loop = asyncio.get_running_loop()
            if loop in self._sessions and self._sessions[loop] is self:
                del self._sessions[loop]
        except RuntimeError:
            pass  # No running loop, that's okay

        # Clean up any stale loop references
        stale_loops = [loop for loop in self._sessions if loop.is_closed()]
        for loop in stale_loops:
            del self._sessions[loop]

        await self._close_session()

    async def _close_session(self) -> None:
        r"""Internal session cleanup with comprehensive error handling."""
        errors: list[str] = []

        # Close context first (which closes pages)
        if self._context is not None:
            try:
                await self._context.close()
            except Exception as e:
                errors.append(f"Context close error: {e}")

        # Close browser
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception as e:
                errors.append(f"Browser close error: {e}")

        # Stop playwright
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception as e:
                errors.append(f"Playwright stop error: {e}")

        # Reset all references
        self._playwright = self._browser = self._context = self._page = None
        self.snapshot = self.executor = None

        # Log errors if any occurred during cleanup
        if errors:
            logger.warning(
                "Errors during browser session cleanup: %s", "; ".join(errors)
            )

    @classmethod
    async def close_all_sessions(cls) -> None:
        r"""Iterate over all stored sessions and close them."""
        for loop, session in cls._sessions.items():
            if loop.is_running():
                await session._close_session()
            else:
                try:
                    if not loop.is_closed():
                        loop.run_until_complete(session._close_session())
                except Exception as e:
                    logger.warning(
                        "Failed to close session for loop %s: %s",
                        hex(id(loop)),
                        e,
                    )
        cls._sessions.clear()

    # ------------------------------------------------------------------
    # Convenience wrappers around common actions
    # ------------------------------------------------------------------
    async def visit(self, url: str) -> str:
        r"""Navigate to a URL with proper error handling."""
        await self.ensure_browser()
        assert self._page is not None

        try:
            await self._page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self.DEFAULT_NAVIGATION_TIMEOUT,
            )
            # Try to wait for network idle, but don't fail if it times out
            try:
                await self._page.wait_for_load_state(
                    "networkidle", timeout=self.NETWORK_IDLE_TIMEOUT
                )
            except Exception:
                pass  # Network idle timeout is not critical
            return f"Visited {url}"
        except Exception as e:
            return f"Error visiting {url}: {e}"

    async def get_snapshot(
        self, *, force_refresh: bool = False, diff_only: bool = False
    ) -> str:
        await self.ensure_browser()
        assert self.snapshot is not None
        return await self.snapshot.capture(
            force_refresh=force_refresh, diff_only=diff_only
        )

    async def exec_action(self, action: Dict[str, Any]) -> str:
        await self.ensure_browser()
        assert self.executor is not None
        return await self.executor.execute(action)

    # Low-level accessors -------------------------------------------------
    async def get_page(self) -> "Page":
        await self.ensure_browser()
        assert self._page is not None
        return self._page
