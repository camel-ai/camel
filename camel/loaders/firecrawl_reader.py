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

from pydantic import BaseModel

from .base_loader import BaseLoader


class Firecrawl:
    r"""Firecrawl allows you to turn entire websites into LLM-ready markdown.

    Args:
        api_key (Optional[str]): API key for authenticating with the Firecrawl
            API.
        api_url (Optional[str]): Base URL for the Firecrawl API.

    References:
        https://docs.firecrawl.dev/introduction
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> None:
        from firecrawl import FirecrawlApp

        self._api_key = api_key or os.environ.get("FIRECRAWL_API_KEY")
        self._api_url = api_url or os.environ.get("FIRECRAWL_API_URL")

        self.app = FirecrawlApp(api_key=self._api_key, api_url=self._api_url)

    def crawl(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        r"""Crawl a URL and all accessible subpages. Customize the crawl by
        setting different parameters, and receive the full response or a job
        ID based on the specified options.

        Args:
            url (str): The URL to crawl.
            params (Optional[Dict[str, Any]]): Additional parameters for the
                crawl request. Defaults to `None`.
            **kwargs (Any): Additional keyword arguments, such as
                `poll_interval`, `idempotency_key`.

        Returns:
            Any: The crawl job ID or the crawl results if waiting until
                completion.

        Raises:
            RuntimeError: If the crawling process fails.
        """

        try:
            crawl_response = self.app.crawl_url(
                url=url,
                params=params,
                **kwargs,
            )
            return crawl_response
        except Exception as e:
            raise RuntimeError(f"Failed to crawl the URL: {e}")

    def check_crawl_job(self, job_id: str) -> Dict:
        r"""Check the status of a crawl job.

        Args:
            job_id (str): The ID of the crawl job.

        Returns:
            Dict: The response including status of the crawl job.

        Raises:
            RuntimeError: If the check process fails.
        """

        try:
            return self.app.check_crawl_status(job_id)
        except Exception as e:
            raise RuntimeError(f"Failed to check the crawl job status: {e}")

    def scrape(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        r"""To scrape a single URL. This function supports advanced scraping
        by setting different parameters and returns the full scraped data as a
        dictionary.

        Reference: https://docs.firecrawl.dev/advanced-scraping-guide

        Args:
            url (str): The URL to read.
            params (Optional[Dict[str, Any]]): Additional parameters for the
                scrape request.

        Returns:
            Dict: The scraped data.

        Raises:
            RuntimeError: If the scrape process fails.
        """
        try:
            return self.app.scrape_url(url=url, params=params)
        except Exception as e:
            raise RuntimeError(f"Failed to scrape the URL: {e}")

    def structured_scrape(self, url: str, response_format: BaseModel) -> Dict:
        r"""Use LLM to extract structured data from given URL.

        Args:
            url (str): The URL to read.
            response_format (BaseModel): A pydantic model
                that includes value types and field descriptions used to
                generate a structured response by LLM. This schema helps
                in defining the expected output format.

        Returns:
            Dict: The content of the URL.

        Raises:
            RuntimeError: If the scrape process fails.
        """
        try:
            data = self.app.scrape_url(
                url,
                {
                    'formats': ['extract'],
                    'extract': {'schema': response_format.model_json_schema()},
                },
            )
            return data.get("extract", {})
        except Exception as e:
            raise RuntimeError(f"Failed to perform structured scrape: {e}")

    def map_site(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> list:
        r"""Map a website to retrieve all accessible URLs.

        Args:
            url (str): The URL of the site to map.
            params (Optional[Dict[str, Any]]): Additional parameters for the
                map request. Defaults to `None`.

        Returns:
            list: A list containing the URLs found on the site.

        Raises:
            RuntimeError: If the mapping process fails.
        """
        try:
            return self.app.map_url(url=url, params=params)
        except Exception as e:
            raise RuntimeError(f"Failed to map the site: {e}")


class FirecrawlLoader(BaseLoader):
    def __init__(
        self,
        config: Optional[Dict[str, Any]],
    ) -> None:
        super().__init__(config)
        self.config = config if config else {}
        self._api_key = self.config.get("api_key") or os.environ.get(
            "FIRECRAWL_API_KEY"
        )
        self._api_url = self.config.get("api_url") or os.environ.get(
            "FIRECRAWL_API_URL"
        )

        self.firecrawl = Firecrawl(
            api_key=self._api_key, api_url=self._api_url
        )

    def load(self, source: str, **kwargs: Any) -> Any:
        r"""Load website data using Firecrawl.

        Args:
            source (str): The URL to load.
            **kwargs: Additional parameters for the scrape function.

        Returns:
            The scraped data.
        """
        functionality = kwargs.get("functionality", "scrape")
        if functionality == "crawl":
            return self.crawl(source, params=kwargs.get("params"), **kwargs)
        elif functionality == "structured_scrape":
            response_format = kwargs.get("response_format")
            if response_format is None:
                raise ValueError(
                    "For structured_scrape, 'response_format' must \
                    be provided."
                )
            return self.structured_scrape(source, response_format)
        elif functionality == "map_site":
            return self.map_site(source, params=kwargs.get("params"))
        else:  # Default is scrape.
            return self.scrape(source, params=kwargs.get("params"))

    def crawl(
        self, url: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> Any:
        return self.firecrawl.crawl(url=url, params=params, **kwargs)

    def check_crawl_job(self, job_id: str) -> Dict:
        return self.firecrawl.check_crawl_job(job_id)

    def scrape(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict:
        return self.firecrawl.scrape(url=url, params=params)

    def structured_scrape(self, url: str, response_format: BaseModel) -> Dict:
        return self.firecrawl.structured_scrape(url, response_format)

    def map_site(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> list:
        return self.firecrawl.map_site(url=url, params=params)

    @property
    def supported_formats(self) -> set:
        return {'html', 'url'}
