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

from typing import List, Optional

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer

logger = get_logger(__name__)


@MCPServer()
class Crawl4AIToolkit(BaseToolkit):
    r"""A class representing a toolkit for Crawl4AI."""

    def __init__(
        self,
        timeout: Optional[float] = None,
    ):
        super().__init__(timeout=timeout)
        self._client = None

    async def _get_client(self):
        r"""Get or create the AsyncWebCrawler client."""
        if self._client is None:
            from crawl4ai import AsyncWebCrawler

            self._client = AsyncWebCrawler()
            await self._client.__aenter__()
        return self._client

    async def scrape(self, url: str) -> str:
        r"""Scrapes a webpage and returns its content.

        This function is designed to fetch the content of a given URL and
        return it as a single string. It's particularly useful for extracting
        text from web pages for further processing. The function
        will try to get the most meaningful content from the page.

        Args:
            url (str): The URL of the webpage to scrape.

        Returns:
            str: The scraped content of the webpage as a string. If the
                scraping fails, it will return an error message.
        """
        from crawl4ai import CrawlerRunConfig

        try:
            client = await self._get_client()
            config = CrawlerRunConfig(
                only_text=True,
            )
            content = await client.arun(url, crawler_config=config)
            return str(content.markdown) if content.markdown else ""
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return f"Error scraping {url}: {e}"

    async def __aenter__(self):
        r"""Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        r"""Async context manager exit - cleanup the client."""
        if self._client is not None:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
            self._client = None

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.scrape),
        ]
