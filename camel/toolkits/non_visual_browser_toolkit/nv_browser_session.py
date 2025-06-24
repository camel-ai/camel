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

from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from .actions import ActionExecutor
from .snapshot import PageSnapshot

if TYPE_CHECKING:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Page,
        Playwright,
    )


class NVBrowserSession:
    """Lightweight wrapper around Playwright for non-visual (headless)
    browsing.

    It provides a single *Page* instance plus helper utilities (snapshot &
    executor).  Multiple toolkits or agents can reuse this class without
    duplicating Playwright setup code.
    """

    # Configuration constants
    DEFAULT_NAVIGATION_TIMEOUT = 10000  # 10 seconds
    NETWORK_IDLE_TIMEOUT = 5000  # 5 seconds

    def __init__(
        self, *, headless: bool = True, user_data_dir: Optional[str] = None
    ):
        self._headless = headless
        self._user_data_dir = user_data_dir

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        self.snapshot: Optional[PageSnapshot] = None
        self.executor: Optional[ActionExecutor] = None

        # Protect browser initialisation against concurrent calls
        import asyncio

        self._ensure_lock: "asyncio.Lock" = asyncio.Lock()

    # ------------------------------------------------------------------
    # Browser lifecycle helpers
    # ------------------------------------------------------------------
    async def ensure_browser(self) -> None:
        # Serialise initialisation to avoid race conditions where multiple
        # concurrent coroutine calls create multiple browser instances for
        # the same NVBrowserSession.
        async with self._ensure_lock:
            await self._ensure_browser_inner()

    # Moved original logic to helper
    async def _ensure_browser_inner(self) -> None:
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

        from camel.logger import get_logger

        _dbg_logger = get_logger(__name__)

        # Reuse an already open page (persistent context may restore last
        # session)
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = await self._context.new_page()

        # Debug information to help trace concurrency issues
        _dbg_logger.debug(
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
            from camel.logger import get_logger

            logger = get_logger(__name__)
            logger.warning(
                "Errors during browser session cleanup: %s", "; ".join(errors)
            )

    # ------------------------------------------------------------------
    # Convenience wrappers around common actions
    # ------------------------------------------------------------------
    async def visit(self, url: str) -> str:
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

    async def exec_action(self, action: dict[str, Any]) -> str:
        await self.ensure_browser()
        assert self.executor is not None
        return await self.executor.execute(action)

    # Low-level accessors -------------------------------------------------
    async def get_page(self) -> "Page":
        await self.ensure_browser()
        assert self._page is not None
        return self._page
