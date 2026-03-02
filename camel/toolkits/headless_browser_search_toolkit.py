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

import asyncio
import json
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool

logger = get_logger(__name__)

EngineType = Literal["google", "bing", "brave"]


@dataclass
class SearchResult:
    r"""A single search result.

    Attributes:
        title (str): The title of the search result.
        url (str): The URL of the search result.
        snippet (str): A short text snippet from the result.
    """

    title: str
    url: str
    snippet: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
        }


@dataclass
class SearchResponse:
    r"""Response from a search query.

    Attributes:
        query (str): The original search query.
        engine (str): The search engine used.
        page (int): The page number of this response.
        results (List[SearchResult]): Extracted structured results.
        raw_snapshot (str): Raw page snapshot when JS extraction
            fails or page is blocked.
    """

    query: str
    engine: str
    page: int
    results: List[SearchResult] = field(default_factory=list)
    raw_snapshot: str = ""

    def to_dict(self) -> Dict:
        d: Dict = {
            "query": self.query,
            "engine": self.engine,
            "page": self.page,
            "total_results": len(self.results),
            "results": [r.to_dict() for r in self.results],
        }
        if self.raw_snapshot:
            d["raw_snapshot"] = self.raw_snapshot
        return d


def _parse_console_result(raw: str) -> str:
    """Strip the 'Console execution result: ' prefix and unquote."""
    prefix = "Console execution result: "
    if raw.startswith(prefix):
        raw = raw[len(prefix) :]
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
        raw = (
            raw.replace('\\"', '"')
            .replace('\\n', '\n')
            .replace('\\t', '\t')
            .replace('\\\\', '\\')
        )
    return raw


def _parse_json_from_response(raw: str) -> list:
    """Parse JSON array from a console exec response string."""
    cleaned = _parse_console_result(raw)
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        pass
    match = re.search(r'\[.*\]', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except (json.JSONDecodeError, TypeError):
            pass
    return []


# ---------------------------------------------------------------------------
# ES5-compatible extraction JS for each engine.
# We avoid const/let/arrow/template-literals because
# browser_console_exec wraps code in a way that can choke on them.
# ---------------------------------------------------------------------------

_GOOGLE_JS = """
(function() {
    var results = [];
    var seen = {};
    var items = document.querySelectorAll('#search .g, #rso .g');
    for (var i = 0; i < items.length; i++) {
        var item = items[i];
        var linkEl = item.querySelector('a[href]');
        var titleEl = item.querySelector('h3');
        var snippetEl = item.querySelector(
            '[data-sncf], .VwiC3b, .IsZvec, .lEBKkf span, .st'
        );
        if (linkEl && titleEl) {
            var url = linkEl.href;
            if (url && url.indexOf('google.com/search') === -1 &&
                url.indexOf('accounts.google') === -1 &&
                url.indexOf('javascript:') !== 0 && !seen[url]) {
                seen[url] = true;
                results.push({
                    title: titleEl.innerText.trim(),
                    url: url,
                    snippet: snippetEl
                        ? snippetEl.innerText.trim() : ''
                });
            }
        }
    }
    return JSON.stringify(results);
})()
"""

_BING_JS = """
(function() {
    var results = [];
    var items = document.querySelectorAll(
        '#b_results > li.b_algo'
    );
    for (var i = 0; i < items.length; i++) {
        var item = items[i];
        var linkEl = item.querySelector('h2 a')
            || item.querySelector('h3 a');
        if (!linkEl) continue;
        var title = linkEl.innerText.trim();
        var url = linkEl.href;
        try {
            var u = new URL(url);
            if (u.hostname.indexOf('bing.com') !== -1
                && u.pathname === '/ck/a') {
                var uParam = u.searchParams.get('u');
                if (uParam
                    && uParam.indexOf('a1') === 0) {
                    url = decodeURIComponent(
                        atob(uParam.substring(2))
                    );
                }
            }
        } catch(e) {}
        if (url.indexOf('bing.com/ck/a') !== -1) {
            var citeEl = item.querySelector('cite');
            if (citeEl) {
                var citeUrl = citeEl.innerText.trim();
                if (citeUrl.indexOf('http') !== 0)
                    citeUrl = 'https://' + citeUrl;
                url = citeUrl;
            }
        }
        var snippetEl = item.querySelector(
            '.b_caption p, .b_lineclamp2, .b_paractl'
        );
        var snippet = snippetEl
            ? snippetEl.innerText.trim() : '';
        if (title && url) {
            results.push({
                title: title, url: url, snippet: snippet
            });
        }
    }
    return JSON.stringify(results);
})()
"""

_BRAVE_JS = """
(function() {
    var results = [];
    var seen = {};
    var items = document.querySelectorAll(
        '[data-type="web"]'
    );
    for (var i = 0; i < items.length; i++) {
        var item = items[i];
        var url = '';
        var titleEl = item.querySelector(
            '.title a, a.svelte-14r20fy'
        );
        if (!titleEl) {
            var links = item.querySelectorAll('a[href]');
            for (var j = 0; j < links.length; j++) {
                var a = links[j];
                var h = a.href || '';
                if (h.indexOf('search.brave.com') === -1
                    && h.indexOf('javascript:') !== 0
                    && h.indexOf('http') === 0) {
                    titleEl = a;
                    break;
                }
            }
        }
        if (!titleEl) continue;
        url = titleEl.href;
        if (!url || seen[url]) continue;
        seen[url] = true;
        var titleDiv = item.querySelector('.title');
        var title = titleDiv
            ? titleDiv.innerText.trim()
            : titleEl.innerText.trim()
                .split('\\n').pop().trim();
        var snippetEl = item.querySelector(
            '.generic-snippet, '
            + '.snippet-description, '
            + '.snippet-content'
        );
        var snippet = snippetEl
            ? snippetEl.innerText.trim() : '';
        if (title && url) {
            results.push({
                title: title, url: url, snippet: snippet
            });
        }
    }
    return JSON.stringify(results);
})()
"""

_BLOCK_DETECT_JS = """
(function() {
    var body = document.body
        ? document.body.innerText : '';
    var url = window.location.href;
    return JSON.stringify({
        url: url,
        title: document.title,
        hasCaptcha: !!(document.querySelector(
            '#captcha-form, '
            + '.g-recaptcha, '
            + 'iframe[src*="recaptcha"]'
        )),
        hasConsent: !!(document.querySelector(
            'form[action*="consent"]'
        )),
        isSorryPage:
            url.indexOf('/sorry/') !== -1 ||
            body.indexOf('unusual traffic') !== -1,
        bodyLength: body.length
    });
})()
"""

_ENGINE_JS = {
    "google": _GOOGLE_JS,
    "bing": _BING_JS,
    "brave": _BRAVE_JS,
}


class HeadlessBrowserSearchToolkit(BaseToolkit):
    r"""Headless browser search toolkit using HybridBrowserToolkit.

    Performs web searches via a stealth headless browser, supporting
    Google, Bing, and Brave search engines. Automatically constructs
    search URLs, navigates pages, and extracts structured results.

    Args:
        engine (EngineType): Search engine to use.
            Options: ``"brave"``, ``"bing"``, ``"google"``.
            (default: :obj:`"brave"`)
        num_pages (int): Number of result pages to fetch per search.
            (default: :obj:`1`)
        headless (bool): Run browser in headless mode.
            (default: :obj:`True`)
        stealth (bool): Enable anti-fingerprint stealth mode.
            (default: :obj:`True`)
        lang (str): Language hint for search results.
            (default: :obj:`"en"`)

    Example:
        >>> from camel.toolkits import (
        ...     HeadlessBrowserSearchToolkit,
        ... )
        >>> toolkit = HeadlessBrowserSearchToolkit(
        ...     engine="brave", num_pages=2
        ... )
        >>> tools = toolkit.get_tools()
    """

    def __init__(
        self,
        engine: EngineType = "brave",
        num_pages: int = 1,
        headless: bool = True,
        stealth: bool = True,
        lang: str = "en",
    ):
        super().__init__()
        if engine not in _ENGINE_JS:
            raise ValueError(
                f"Unsupported engine: {engine!r}. "
                f"Choose from: {list(_ENGINE_JS.keys())}"
            )
        self.engine = engine
        self.num_pages = num_pages
        self.lang = lang
        self._toolkit: Any = None
        self._headless = headless
        self._stealth = stealth
        self._browser_opened = False

    async def _ensure_browser(self) -> Any:
        r"""Initialize the browser toolkit if not already done."""
        if self._toolkit is None:
            from camel.toolkits.hybrid_browser_toolkit import (
                HybridBrowserToolkit,
            )

            self._toolkit = HybridBrowserToolkit(
                headless=self._headless,
                stealth=self._stealth,
                enabled_tools=[
                    "browser_open",
                    "browser_close",
                    "browser_visit_page",
                    "browser_click",
                    "browser_scroll",
                    "browser_get_page_snapshot",
                    "browser_console_exec",
                    "browser_enter",
                ],
            )
        if not self._browser_opened:
            await self._toolkit.browser_open()
            self._browser_opened = True
        return self._toolkit

    async def close(self) -> None:
        r"""Close the browser and release resources."""
        if self._toolkit and self._browser_opened:
            await self._toolkit.browser_close()
            self._browser_opened = False

    def _build_search_url(self, query: str, page: int = 0) -> str:
        r"""Build search URL for the given query and page number.

        Args:
            query (str): The search query.
            page (int): Zero-based page index. (default: :obj:`0`)

        Returns:
            str: The full search URL.
        """
        q = urllib.parse.quote_plus(query)
        if self.engine == "google":
            return (
                f"https://www.google.com/search?q={q}"
                f"&start={page * 10}&hl={self.lang}"
            )
        elif self.engine == "bing":
            return (
                f"https://www.bing.com/search?q={q}" f"&first={page * 10 + 1}"
            )
        else:  # brave
            return (
                f"https://search.brave.com/search?q={q}"
                f"&source=web&offset={page}"
            )

    async def _check_blocked(self, toolkit: Any) -> dict:
        r"""Check if the current page is a captcha/block page.

        Args:
            toolkit: The browser toolkit instance.

        Returns:
            dict: Block detection info with keys like
                ``hasCaptcha``, ``isSorryPage``, etc.
        """
        resp = await toolkit.browser_console_exec(_BLOCK_DETECT_JS)
        raw = resp.get("result", "")
        cleaned = _parse_console_result(raw)
        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, TypeError):
            return {}

    async def _extract_results(self, toolkit: Any) -> List[SearchResult]:
        r"""Extract search results from current page via JS.

        Args:
            toolkit: The browser toolkit instance.

        Returns:
            List[SearchResult]: Extracted search results.
        """
        js_code = _ENGINE_JS[self.engine]
        resp = await toolkit.browser_console_exec(js_code)
        raw = resp.get("result", "")

        try:
            items = _parse_json_from_response(raw)
            return [
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                )
                for item in items
                if item.get("url")
            ]
        except Exception as e:
            logger.warning(f"JS extraction failed: {e}, " f"raw={raw[:300]}")
            return []

    async def search(
        self,
        query: str,
        num_pages: int = 0,
    ) -> str:
        r"""Perform a web search and return structured results.

        Uses a headless browser to search the configured engine,
        extract structured results (title, URL, snippet), and
        return them as a JSON string.

        Args:
            query (str): The search query string.
            num_pages (int): Number of result pages to fetch.
                If ``0``, uses the instance default
                ``self.num_pages``. (default: :obj:`0`)

        Returns:
            str: JSON string containing a list of page results.
                Each page has ``query``, ``engine``, ``page``,
                ``total_results``, ``results``, and optionally
                ``raw_snapshot`` fields.
        """
        pages_to_fetch = num_pages if num_pages > 0 else self.num_pages
        toolkit = await self._ensure_browser()
        all_pages: List[SearchResponse] = []

        for page_num in range(pages_to_fetch):
            url = self._build_search_url(query, page_num)
            logger.info(f"[{self.engine}] Page {page_num + 1}: {url}")

            await toolkit.browser_visit_page(url)
            await asyncio.sleep(3)

            # Check for blocks/captcha
            block_info = await self._check_blocked(toolkit)
            is_blocked = block_info.get("hasCaptcha") or block_info.get(
                "isSorryPage"
            )

            if is_blocked:
                logger.warning(
                    f"[{self.engine}] Page {page_num + 1} "
                    f"BLOCKED: captcha="
                    f"{block_info.get('hasCaptcha')}, "
                    f"sorry={block_info.get('isSorryPage')}, "
                    f"url={block_info.get('url', '')}"
                )
                snapshot = await toolkit.browser_get_page_snapshot()
                all_pages.append(
                    SearchResponse(
                        query=query,
                        engine=self.engine,
                        page=page_num + 1,
                        results=[],
                        raw_snapshot=snapshot,
                    )
                )
                continue

            results = await self._extract_results(toolkit)

            # Retry once if no results (page may still load)
            if not results:
                await asyncio.sleep(3)
                results = await self._extract_results(toolkit)

            # Fallback: attach snapshot if JS got nothing
            snapshot = ""
            if not results:
                logger.info(
                    f"[{self.engine}] Page {page_num + 1}: "
                    f"JS extraction empty, "
                    f"falling back to snapshot"
                )
                snapshot = await toolkit.browser_get_page_snapshot()

            page_response = SearchResponse(
                query=query,
                engine=self.engine,
                page=page_num + 1,
                results=results,
                raw_snapshot=snapshot,
            )
            all_pages.append(page_response)
            logger.info(
                f"[{self.engine}] Page {page_num + 1}: "
                f"{len(results)} results"
                + (
                    f" (snapshot fallback: " f"{len(snapshot)} chars)"
                    if snapshot
                    else ""
                )
            )

        return json.dumps(
            [p.to_dict() for p in all_pages],
            ensure_ascii=False,
            indent=2,
        )

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing
        the functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects.
        """
        return [
            FunctionTool(self.search),
        ]
