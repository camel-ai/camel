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

import os
from typing import Any, Dict, Optional


class ScrapeGraphAI:
    r"""ScrapeGraphAI allows you to perform AI-powered web scraping and
    searching.

    Args:
        api_key (Optional[str]): API key for authenticating with the
            ScrapeGraphAI API.

    References:
        https://scrapegraph.ai/
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
    ) -> None:
        from scrapegraph_py import Client
        from scrapegraph_py.logger import sgai_logger

        self._api_key = api_key or os.environ.get("SCRAPEGRAPH_API_KEY")
        sgai_logger.set_logging(level="INFO")
        self.client = Client(api_key=self._api_key)

    def search(
        self,
        user_prompt: str,
    ) -> Dict[str, Any]:
        r"""Perform an AI-powered web search using ScrapeGraphAI.

        Args:
            user_prompt (str): The search query or instructions.

        Returns:
            Dict[str, Any]: The search results including answer and reference
                URLs.

        Raises:
            RuntimeError: If the search process fails.
        """
        try:
            response = self.client.searchscraper(user_prompt=user_prompt)
            return response
        except Exception as e:
            raise RuntimeError(f"Failed to perform search: {e}")

    def scrape(
        self,
        website_url: str,
        user_prompt: str,
        website_html: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Perform AI-powered web scraping using ScrapeGraphAI.

        Args:
            website_url (str): The URL to scrape.
            user_prompt (str): Instructions for what data to extract.
            website_html (Optional[str]): Optional HTML content to use instead
                of fetching from the URL.

        Returns:
            Dict[str, Any]: The scraped data including request ID and result.

        Raises:
            RuntimeError: If the scrape process fails.
        """
        try:
            response = self.client.smartscraper(
                website_url=website_url,
                user_prompt=user_prompt,
                website_html=website_html,
            )
            return response
        except Exception as e:
            raise RuntimeError(f"Failed to perform scrape: {e}")

    def close(self) -> None:
        r"""Close the ScrapeGraphAI client connection."""
        self.client.close()
