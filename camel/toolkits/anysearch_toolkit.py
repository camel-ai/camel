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

from concurrent.futures import ThreadPoolExecutor
from typing import ClassVar, Dict, List, Optional
from urllib.parse import urlparse

import requests

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer

logger = get_logger(__name__)


@MCPServer()
class AnySearchToolkit(BaseToolkit):
    r"""A toolkit for web search and page extraction powered by AnySearch.

    AnySearch is a search infrastructure built for AI agents. This toolkit
    exposes the full capability set:

    - General web search, usable anonymously (no API key required).
    - Parallel search: several queries issued concurrently.
    - Vertical domain search, through a ``tag`` plus its ``params``
      (for example ``tag="code.doc"`` with ``params={"library":
      "golang"}``).
    - Extract: fetch and parse the readable content of a web page.

    Args:
        api_key (Optional[str]): The AnySearch API key. When :obj:`None`,
            the value of the ``ANYSEARCH_API_KEY`` environment variable is
            used; when that is also unset, requests are sent anonymously.
            (default: :obj:`None`)
        zone (Optional[str]): Search zone, either :obj:`"cn"` or
            :obj:`"intl"`. When :obj:`None`, the server default is used.
            (default: :obj:`None`)
        language (Optional[str]): Default language code for search results.
            (default: :obj:`None`)
        base_url (str): Base URL of the AnySearch API.
            (default: :obj:`"https://api.anysearch.com"`)
        timeout (Optional[float]): The timeout value for API requests
            in seconds. If None, no timeout is applied.
            (default: :obj:`None`)

    Raises:
        ValueError: If zone is provided but is not ``"cn"`` or ``"intl"``.
    """

    _DEFAULT_BASE_URL: ClassVar[str] = "https://api.anysearch.com"
    _VALID_ZONES: ClassVar[List[str]] = ["cn", "intl"]
    _MAX_NUM_RESULTS: ClassVar[int] = 10

    def __init__(
        self,
        api_key: Optional[str] = None,
        zone: Optional[str] = None,
        language: Optional[str] = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: Optional[float] = None,
    ) -> None:
        super().__init__(timeout=timeout)
        if zone is not None:
            self._validate_zone(zone)

        self.api_key = api_key
        self.zone = zone
        self.language = language
        self.base_url = base_url.rstrip('/')

    def _validate_zone(self, zone: str) -> None:
        r"""Validate the search zone.

        Args:
            zone (str): The zone to validate.

        Raises:
            ValueError: If the zone is not :obj:`"cn"` or :obj:`"intl"`.
        """
        if zone not in self._VALID_ZONES:
            raise ValueError(
                f"Invalid zone: {zone}. Must be one of: "
                f"{self._VALID_ZONES}"
            )

    @staticmethod
    def _validate_url(url: str) -> None:
        r"""Validate that a string is an absolute HTTP/HTTPS URL.

        Args:
            url (str): The URL to validate.

        Raises:
            ValueError: If the URL is not a valid HTTP/HTTPS URL.
        """
        result = urlparse(url)
        if result.scheme not in ('http', 'https') or not result.netloc:
            raise ValueError(
                f"Invalid URL: {url}. Must be an absolute HTTP/HTTPS URL."
            )

    def _headers(self) -> Dict[str, str]:
        r"""Build the HTTP headers for an API request.

        Returns:
            Dict[str, str]: Request headers, including the bearer token
                when an API key is configured.
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "camel-ai/anysearch-toolkit",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _post(
        self,
        endpoint: str,
        payload: Dict[str, object],
    ) -> Optional[Dict[str, object]]:
        r"""Send a POST request to the AnySearch API.

        Both HTTP level failures and business level failures (a non-zero
        ``code`` in the response envelope) are logged and reported as
        :obj:`None`, so that a single failing query never breaks an agent
        loop.

        Args:
            endpoint (str): API endpoint, for example :obj:`"/v1/search"`.
            payload (Dict[str, object]): JSON body of the request.

        Returns:
            Optional[Dict[str, object]]: The ``data`` object of the
                response, or :obj:`None` when the request did not succeed.
        """
        try:
            response = requests.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            body = response.json()
        except Exception as error:
            logger.error(f"AnySearch request to {endpoint} failed: {error}")
            return None

        if not isinstance(body, dict):
            logger.error(f"AnySearch returned a non-object body: {body!r}")
            return None

        code = body.get("code", 0)
        if code != 0:
            logger.error(
                f"AnySearch returned code {code}: "
                f"{body.get('message', 'no message')}"
            )
            return None

        data = body.get("data")
        if not isinstance(data, dict):
            logger.error(f"AnySearch returned no data object: {body!r}")
            return None
        return data

    @staticmethod
    def _format_results(
        raw_results: object,
        num_results: int,
    ) -> List[Dict[str, str]]:
        r"""Normalize raw search results.

        Args:
            raw_results (object): The ``results`` value returned by the API.
            num_results (int): Maximum number of results to keep.

        Returns:
            List[Dict[str, str]]: A list of results with the keys
                ``title``, ``link``, ``snippet`` and ``content``. Malformed
                rows are skipped instead of raising.
        """
        if not isinstance(raw_results, list):
            return []

        formatted: List[Dict[str, str]] = []
        for item in raw_results[:num_results]:
            if not isinstance(item, dict):
                continue
            formatted.append(
                {
                    "title": str(item.get("title", "")),
                    "link": str(item.get("url", "")),
                    "snippet": str(item.get("snippet", "")),
                    "content": str(item.get("content", "")),
                }
            )
        return formatted

    def search(
        self,
        query: str,
        num_results: int = 10,
        tag: Optional[str] = None,
        params: Optional[Dict[str, object]] = None,
        zone: Optional[str] = None,
        language: Optional[str] = None,
        result_format: str = "markdown",
    ) -> List[Dict[str, str]]:
        r"""Perform a web search with AnySearch.

        The call works without an API key: anonymous access is rate limited
        per IP but is otherwise functional, so the toolkit can be used
        straight away.

        Args:
            query (str): The search query string to execute.
            num_results (int, optional): Maximum number of results to
                return. Clamped to :obj:`[1, 10]`. (default: :obj:`10`)
            tag (Optional[str], optional): Vertical domain tag, for example
                :obj:`"code.doc"` or :obj:`"finance.news"`. When :obj:`None`
                a general web search is performed. (default: :obj:`None`)
            params (Optional[Dict[str, object]], optional): Tag specific
                parameters, for example :obj:`{"library": "golang"}` for the
                :obj:`"code.doc"` tag. (default: :obj:`None`)
            zone (Optional[str], optional): Overrides the toolkit zone for
                this call, :obj:`"cn"` or :obj:`"intl"`.
                (default: :obj:`None`)
            language (Optional[str], optional): Overrides the toolkit
                language for this call. (default: :obj:`None`)
            result_format (str, optional): Result body format, either
                :obj:`"markdown"` or :obj:`"json"`.
                (default: :obj:`"markdown"`)

        Returns:
            List[Dict[str, str]]: List of search results, where each result
                contains the keys ``title``, ``link``, ``snippet`` and
                ``content``. ``content`` holds the parsed page body, so a
                separate scraping step is usually unnecessary. An empty list
                is returned when the request fails.

        Raises:
            ValueError: If zone is provided but is not ``"cn"`` or ``"intl"``
        """
        if zone is not None:
            self._validate_zone(zone)

        limit = max(1, min(int(num_results), self._MAX_NUM_RESULTS))
        payload: Dict[str, object] = {
            "query": query,
            "max_results": limit,
            "format": result_format,
        }
        if tag:
            payload["tag"] = tag
        if params:
            payload["params"] = params
        effective_zone = zone or self.zone
        if effective_zone:
            payload["zone"] = effective_zone
        effective_language = language or self.language
        if effective_language:
            payload["language"] = effective_language

        data = self._post("/v1/search", payload)
        if data is None:
            return []
        results = self._format_results(data.get("results", []), limit)
        logger.debug(f"AnySearch returned {len(results)} results")
        return results

    def search_vertical(
        self,
        query: str,
        tag: str,
        params: Optional[Dict[str, object]] = None,
        num_results: int = 10,
        zone: Optional[str] = None,
        language: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        r"""Search a single vertical domain with AnySearch.

        Args:
            query (str): The search query string to execute.
            tag (str): The vertical domain tag, for example
                :obj:`"code.doc"` or :obj:`"finance.news"`.
            params (Optional[Dict[str, object]], optional): Tag specific
                parameters. Some tags reject a request whose params are
                missing; in that case the API returns a business error and
                an empty list is returned. (default: :obj:`None`)
            num_results (int, optional): Maximum number of results to
                return. Clamped to :obj:`[1, 10]`. (default: :obj:`10`)
            zone (Optional[str], optional): Overrides the toolkit zone for
                this call. (default: :obj:`None`)
            language (Optional[str], optional): Overrides the toolkit
                language for this call. (default: :obj:`None`)

        Returns:
            List[Dict[str, str]]: List of search results with the keys
                ``title``, ``link``, ``snippet`` and ``content``.
        """
        return self.search(
            query=query,
            num_results=num_results,
            tag=tag,
            params=params,
            zone=zone,
            language=language,
        )

    def search_parallel(
        self,
        queries: List[str],
        num_results: int = 10,
        max_workers: int = 4,
        tag: Optional[str] = None,
        params: Optional[Dict[str, object]] = None,
    ) -> Dict[str, List[Dict[str, str]]]:
        r"""Run several searches concurrently.

        AnySearch exposes no batch endpoint, so parallel search is done by
        issuing one request per query from a thread pool.

        Args:
            queries (List[str]): The queries to execute. Duplicates are
                collapsed, order of the mapping follows the input order.
            num_results (int, optional): Maximum number of results per
                query. Clamped to :obj:`[1, 10]`. (default: :obj:`10`)
            max_workers (int, optional): Size of the thread pool.
                (default: :obj:`4`)
            tag (Optional[str], optional): Vertical domain tag applied to
                every query. (default: :obj:`None`)
            params (Optional[Dict[str, object]], optional): Tag specific
                parameters applied to every query. (default: :obj:`None`)

        Returns:
            Dict[str, List[Dict[str, str]]]: Mapping from query to its list
                of results. A query that failed maps to an empty list.
        """
        unique_queries = list(dict.fromkeys(queries))
        if not unique_queries:
            return {}

        workers = max(1, min(int(max_workers), len(unique_queries)))

        def run(query: str) -> List[Dict[str, str]]:
            return self.search(
                query=query,
                num_results=num_results,
                tag=tag,
                params=params,
            )

        with ThreadPoolExecutor(max_workers=workers) as pool:
            batches = list(pool.map(run, unique_queries))
        return dict(zip(unique_queries, batches))

    def extract(self, url: str) -> Dict[str, str]:
        r"""Fetch a web page and return its parsed content.

        Args:
            url (str): Absolute HTTP/HTTPS URL of the page to parse.

        Returns:
            Dict[str, str]: A dictionary with the keys ``url``, ``title``
                and ``content``. On failure an empty dictionary is
                returned.

        Raises:
            ValueError: If url is not a valid absolute HTTP/HTTPS URL.
        """
        self._validate_url(url)
        data = self._post("/v1/extract", {"url": url})
        if data is None:
            return {}
        return {
            "url": str(data.get("url", url)),
            "title": str(data.get("title", "")),
            "content": str(data.get("content", "")),
        }

    def get_tools(self) -> List[FunctionTool]:
        r"""Get the list of available tools in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the available functions in the toolkit.
        """
        return [
            FunctionTool(self.search),
            FunctionTool(self.search_vertical),
            FunctionTool(self.search_parallel),
            FunctionTool(self.extract),
        ]
