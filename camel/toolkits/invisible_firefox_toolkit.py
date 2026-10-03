# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

"""InvisibleFirefoxToolkit (proposal stub).

Optional Firefox-based stealth fetcher toolkit, parallel to BrowserToolkit,
AsyncBrowserToolkit, HybridBrowserToolkit, HeadlessBrowserSearchToolkit.

Wraps invisible_playwright which drives a patched Firefox 150 binary with
fingerprint patches applied at the C++ source code level (no JS shims to
detect). Useful for downstream consumers (notably OWL GAIA agents, see
sibling OWL Issue #613 / PR #614) that hit anti-bot walls on protected
sites.

Tracking discussion: TBD
"""

from typing import List, Optional

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool

try:
    from invisible_playwright import InvisiblePlaywright
except ImportError:
    raise ImportError(
        "`invisible_playwright` not installed. "
        "Install with `pip install invisible_playwright` and run "
        "`python -m invisible_playwright fetch` to download the patched "
        "Firefox binary."
    )

logger = get_logger(__name__)


class InvisibleFirefoxToolkit(BaseToolkit):
    """Firefox-based stealth fetcher toolkit.

    Args:
        seed (Optional[int]): Integer seed for deterministic fingerprint
            across runs. Same seed produces identical fingerprint.
        headless (bool): When True, render on a hidden virtual display so
            the browser stays in real headed mode without showing windows.
            Default True.
        proxy (Optional[dict]): Proxy dict in Playwright format
            ({"server": "...", "username": "...", "password": "..."}).
    """

    def __init__(
        self,
        seed: Optional[int] = None,
        headless: bool = True,
        proxy: Optional[dict] = None,
    ):
        self._seed = seed
        self._headless = headless
        self._proxy = proxy

    def fetch_page(self, url: str, wait_for_selector: Optional[str] = None) -> str:
        r"""Fetch the rendered HTML of a URL using a patched stealth Firefox.

        Use when sites behind Cloudflare, Akamai, Datadome, or hCaptcha
        return empty content or 403 from the standard browser toolkits.

        Args:
            url (str): The URL to fetch.
            wait_for_selector (Optional[str]): Optional CSS selector to wait
                for before returning. Useful for JS-rendered pages.

        Returns:
            str: The page HTML, or an error string if the fetch failed.
        """
        try:
            with InvisiblePlaywright(
                seed=self._seed,
                headless=self._headless,
                proxy=self._proxy,
            ) as browser:
                page = browser.new_page()
                page.goto(url)
                if wait_for_selector:
                    page.wait_for_selector(wait_for_selector)
                return page.content()
        except Exception as e:
            logger.error(f"InvisibleFirefoxToolkit.fetch_page failed: {e}")
            return f"Error fetching {url}: {e}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Return the list of available tools."""
        return [FunctionTool(self.fetch_page)]
