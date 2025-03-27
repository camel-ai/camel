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

from typing import ClassVar, Dict, List, Optional, Union
from urllib.parse import urlparse

import requests

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool

logger = get_logger(__name__)


class SearxNGToolkit(BaseToolkit):
    r"""A toolkit for performing web searches using SearxNG search engine.

    This toolkit provides methods to search the web using SearxNG,
    a privacy-respecting metasearch engine. It supports customizable
    search parameters and safe search levels.

    Args:
        searxng_host (str): The URL of the SearxNG instance to use for
            searches. Must be a valid HTTP/HTTPS URL.
        language (str, optional): Search language code for results.
            (default: :obj:`"en"`)
        categories (List[str], optional): List of search categories to use.
            (default: :obj:`None`)
        time_range (str, optional): Time range filter for search results.Valid
            values are "day", "week", "month", "year". (default: :obj:`None`)
        safe_search (int, optional): Safe search level (0: None, 1: Moderate,
            2: Strict). (default: :obj:`1`)

    Raises:
        ValueError: If searxng_host is not a valid HTTP/HTTPS URL.
        ValueError: If safe_search is not in the valid range [0, 2].
        ValueError: If time_range is provided but not in valid options.
    """

    # Constants for validation
    _SAFE_SEARCH_LEVELS: ClassVar[Dict[int, str]] = {
        0: "Disabled",
        1: "Moderate",
        2: "Strict",
    }
    _VALID_TIME_RANGES: ClassVar[List[str]] = ["day", "week", "month", "year"]
    _DEFAULT_CATEGORY: ClassVar[str] = "general"

    def __init__(
        self,
        searxng_host: str,
        language: str = "en",
        categories: Optional[List[str]] = None,
        time_range: Optional[str] = None,
        safe_search: int = 1,
    ) -> None:
        self._validate_searxng_host(searxng_host)
        self._validate_safe_search(safe_search)
        if time_range is not None:
            self._validate_time_range(time_range)

        self.searxng_host = searxng_host.rstrip('/')
        self.language = language
        self.categories = categories or [self._DEFAULT_CATEGORY]
        self.time_range = time_range
        self.safe_search = safe_search

        logger.info(
            f"Initialized SearxNG toolkit with host: {searxng_host}, "
            f"safe_search: {self._SAFE_SEARCH_LEVELS[safe_search]}"
        )

    def _validate_searxng_host(self, url: str) -> None:
        r"""Validate if the given URL is a proper HTTP/HTTPS URL.

        Args:
            url (str): The URL to validate.

        Raises:
            ValueError: If the URL is not valid.
        """
        try:
            result = urlparse(url)
            is_valid = all(
                [
                    result.scheme in ('http', 'https'),
                    result.netloc,
                ]
            )
            if not is_valid:
                raise ValueError
        except Exception:
            raise ValueError(
                "Invalid searxng_host URL. Must be a valid HTTP/HTTPS URL."
            )

    def _validate_safe_search(self, level: int) -> None:
        r"""Validate if the safe search level is valid.

        Args:
            level (int): The safe search level to validate.

        Raises:
            ValueError: If the safe search level is not valid.
        """
        if level not in self._SAFE_SEARCH_LEVELS:
            raise ValueError(
                f"Invalid safe_search level: {level}. Must be one of: "
                f"{list(self._SAFE_SEARCH_LEVELS.keys())}"
            )

    def _validate_time_range(self, time_range: str) -> None:
        r"""Validate if the time range is valid.

        Args:
            time_range (str): The time range to validate.

        Raises:
            ValueError: If the time range is not valid.
        """
        if time_range not in self._VALID_TIME_RANGES:
            raise ValueError(
                f"Invalid time_range: {time_range}. Must be one of: "
                f"{self._VALID_TIME_RANGES}"
            )

    def search(
        self,
        query: str,
        num_results: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        r"""Perform a web search using the configured SearxNG instance.

        Args:
            query (str): The search query string to execute.
            num_results (int, optional): Maximum number of results to return.
                (default: :obj:`10`)
            category (str, optional): Specific search category to use. If not
                provided, uses the first category from self.categories.
                (default: :obj:`None`)

        Returns:
            List[Dict[str, str]]: List of search results, where each result is
                dictionary containing 'title', 'link', and 'snippet' keys.
        """
        params: Dict[str, Union[str, int]] = {
            "q": query,
            "format": "json",
            "language": self.language,
            "categories": category or self.categories[0],
            "pageno": 1,
            "safe": self.safe_search,
        }

        if self.time_range:
            params["time_range"] = self.time_range

        try:
            logger.debug(f"Sending search request with query: {query}")
            response = requests.get(
                f"{self.searxng_host}/search",
                params=params,  # type: ignore[arg-type]
                headers={"User-Agent": "camel-ai/searxng-toolkit"},
            )
            response.raise_for_status()
            results = response.json().get("results", [])

            formatted_results = []
            for result in results[:num_results]:
                formatted_results.append(
                    {
                        "title": result.get("title", ""),
                        "link": result.get("url", ""),
                        "snippet": result.get("content", ""),
                    }
                )

            logger.debug(f"Retrieved {len(formatted_results)} results")
            return formatted_results

        except Exception as error:
            logger.error(f"Search failed: {error!s}")
            return []

    def get_tools(self) -> List[FunctionTool]:
        r"""Get the list of available tools in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing the
                available functions in the toolkit.
        """
        return [
            FunctionTool(self.search),
        ]
