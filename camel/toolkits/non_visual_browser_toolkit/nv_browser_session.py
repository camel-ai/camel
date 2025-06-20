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
from typing import Any, Optional

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from .actions import ActionExecutor
from .snapshot import PageSnapshot

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.sync_api import Playwright


class NVBrowserSession:
    """Lightweight wrapper around Playwright for non-visual (headless)
    browsing.

    It provides a single *Page* instance plus helper utilities (snapshot &
    executor).  Multiple toolkits or agents can reuse this class without
    duplicating Playwright setup code.
    """

    def __init__(
        self, *, headless: bool = True, user_data_dir: Optional[str] = None
    ):
        self._headless = headless
        self._user_data_dir = user_data_dir

        self._playwright: Optional["Playwright"] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        self.snapshot: Optional[PageSnapshot] = None
        self.executor: Optional[ActionExecutor] = None

    # ------------------------------------------------------------------
    # Browser lifecycle helpers
    # ------------------------------------------------------------------
    def ensure_browser(self) -> None:
        if self._page is not None:
            return

        self._playwright = sync_playwright().start()
        if self._user_data_dir:
            Path(self._user_data_dir).mkdir(parents=True, exist_ok=True)
            pl = self._playwright
            assert pl is not None
            self._context = (
                pl.chromium.launch_persistent_context(
                    user_data_dir=self._user_data_dir,
                    headless=self._headless,
                )
            )
            self._browser = self._context.browser
        else:
            pl = self._playwright
            assert pl is not None
            self._browser = pl.chromium.launch(
                headless=self._headless
            )
            self._context = self._browser.new_context()

        # Reuse an already open page (persistent context may restore last
        # session)
        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = self._context.new_page()
        # helpers
        self.snapshot = PageSnapshot(self._page)
        self.executor = ActionExecutor(self._page)

    def close(self) -> None:
        if self._context is not None:
            self._context.close()
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

        self._playwright = self._browser = self._context = self._page = None
        # type: ignore[assignment]
        self.snapshot = self.executor = None

    # ------------------------------------------------------------------
    # Convenience wrappers around common actions
    # ------------------------------------------------------------------
    def visit(self, url: str) -> str:
        self.ensure_browser()
        assert self._page is not None
        self._page.goto(url, wait_until="domcontentloaded", timeout=2000)
        try:
            self._page.wait_for_load_state("networkidle", timeout=2000)
        except Exception:
            pass
        return f"Visited {url}"

    def get_snapshot(
        self, *, force_refresh: bool = False, diff_only: bool = False
    ) -> str:
        self.ensure_browser()
        assert self.snapshot is not None
        return self.snapshot.capture(
            force_refresh=force_refresh, diff_only=diff_only
        )

    def exec_action(self, action: dict[str, Any]) -> str:
        self.ensure_browser()
        assert self.executor is not None
        return self.executor.execute(action)

    # Low-level accessors -------------------------------------------------
    @property
    def page(self) -> Page:
        self.ensure_browser()
        assert self._page is not None
        return self._page
