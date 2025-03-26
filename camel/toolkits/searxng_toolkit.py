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

from typing import Dict, List, Optional, Union
from urllib.parse import urlparse

import requests

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool

logger = get_logger(__name__)


class SearxNGToolkit(BaseToolkit):
    r"""A toolkit for performing web searches using SearxNG.

    This toolkit provides methods for searching web using a SearxNG instance,
    with support for different search categories and customizable parameters.

    Args:
        searxng_host (str): The URL of the SearxNG instance.
        language (str): Search language code. (default: :obj:`"en"`)
        categories (Optional[List[str]]): List of search categories.
            (default: :obj:`None`), which uses ["general"].
        time_range (Optional[str]): Time range for results (e.g., "day",
            "week", "month", "year"). (default: :obj:`None`)
        safe_search (int): Safe search level (0: None, 1: Moderate,
            2: Strict). (default: :obj:`1`)
        timeout (Optional[float]): The timeout for the toolkit.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        searxng_host: str,
        language: str = "en",
        categories: Optional[List[str]] = None,
        time_range: Optional[str] = None,
        safe_search: int = 1,
        timeout: Optional[float] = None,
    ) -> None:
        # Validate URL format
        parsed_url = urlparse(searxng_host)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            raise ValueError(f"Invalid SearxNG host URL: {searxng_host}")

        # Validate safe_search parameter
        if safe_search not in [0, 1, 2]:
            raise ValueError(
                f"safe_search must be 0, 1, or 2, got {safe_search}"
            )

        self.searxng_host = searxng_host.rstrip('/')
        self.language = language
        self.categories = categories or ["general"]
        self.time_range = time_range
        self.safe_search = safe_search
        self.timeout = timeout
        logger.info(f"Initialized SearxNG toolkit with host: {searxng_host}")

    def search(
        self,
        query: str,
        num_results: int = 10,
        category: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        r"""Perform a web search using SearxNG.

        Args:
            query (str): The search query string.
            num_results (int): Maximum number of results to return.
                (default: :obj:`10`)
            category (Optional[str]): Specific search category to use.
                (default: :obj:`None`), which uses the first category from
                self.categories.

        Returns:
            List[Dict[str, str]]: List of search results, where each result
                contains 'title', 'link', and 'snippet' keys.
        """
        # Define params with proper typing
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
                params=params,
                headers={"User-Agent": "camel-ai/searxng-toolkit"},
                timeout=self.timeout,
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

    def get_available_categories(self) -> List[str]:
        r"""Retrieve available search categories from the SearxNG instance.

        Returns:
            List[str]: List of available search category names.
        """
        try:
            logger.debug("Fetching available categories")
            response = requests.get(
                f"{self.searxng_host}/config",
                headers={"User-Agent": "camel-ai/searxng-toolkit"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            categories = response.json().get("categories", [])
            logger.debug(f"Retrieved {len(categories)} categories")
            return categories
        except Exception as error:
            logger.error(f"Failed to get categories: {error!s}")
            return []

    def get_tools(self) -> List[FunctionTool]:
        r"""Get the list of available tools in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the available functions in the toolkit.
        """
        return [
            FunctionTool(self.search),
            FunctionTool(self.get_available_categories),
        ]
