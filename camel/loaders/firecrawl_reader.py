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

import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from camel.utils import dependencies_required


def _to_dict(response: Any) -> Any:
    r"""Normalize a Firecrawl SDK response into plain Python data.

    The Firecrawl v2 SDK returns typed pydantic models (e.g. ``Document``,
    ``CrawlJob``). Convert these to dictionaries so the loader keeps returning
    JSON-like, dict-subscriptable data as before.
    """
    if isinstance(response, BaseModel):
        return response.model_dump()
    return response


class Firecrawl:
    r"""[Firecrawl](https://www.firecrawl.dev) allows you to turn entire
    websites into LLM-ready markdown.

    Args:
        api_key (Optional[str]): API key for authenticating with the Firecrawl
            API.
        api_url (Optional[str]): Base URL for the Firecrawl API.

    References:
        https://docs.firecrawl.dev/introduction
    """

    @dependencies_required('firecrawl')
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> None:
        from firecrawl import Firecrawl as FirecrawlApp

        self._api_key = api_key or os.environ.get("FIRECRAWL_API_KEY")
        self._api_url = api_url or os.environ.get("FIRECRAWL_API_URL")

        # The v2 client defaults ``api_url`` to the production endpoint, so
        # only forward it when an explicit value is provided.
        kwargs: Dict[str, Any] = {"api_key": self._api_key}
        if self._api_url is not None:
            kwargs["api_url"] = self._api_url
        self.app = FirecrawlApp(**kwargs)

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
                crawl request (e.g. ``limit``, ``include_paths``,
                ``scrape_options``). Defaults to `None`.
            **kwargs (Any): Additional keyword arguments forwarded to the
                Firecrawl client, such as ``poll_interval`` or ``timeout``.

        Returns:
            Any: The crawl job result, including its status and the crawled
                documents.

        Raises:
            RuntimeError: If the crawling process fails.
        """

        try:
            crawl_response = self.app.crawl(
                url=url,
                **(params or {}),
                **kwargs,
            )
            return _to_dict(crawl_response)
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
            return _to_dict(self.app.get_crawl_status(job_id))
        except Exception as e:
            raise RuntimeError(f"Failed to check the crawl job status: {e}")

    def scrape(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        r"""To scrape a single URL. This function supports advanced scraping
        by setting different parameters and returns the full scraped data as a
        dictionary.

        Reference: https://docs.firecrawl.dev/advanced-scraping-guide

        Args:
            url (str): The URL to read.
            params (Optional[Dict[str, Any]]): Additional parameters for the
                scrape request (e.g. ``formats``, ``only_main_content``).
                Defaults to `None`.

        Returns:
            Dict[str, Any]: The scraped data.

        Raises:
            RuntimeError: If the scrape process fails.
        """
        try:
            return _to_dict(self.app.scrape(url, **(params or {})))
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
            Dict: The structured data extracted from the URL.

        Raises:
            RuntimeError: If the scrape process fails.
        """
        try:
            document = self.app.scrape(
                url,
                formats=[
                    {
                        "type": "json",
                        "schema": response_format.model_json_schema(),
                    }
                ],
            )
            data = _to_dict(document)
            return data.get("json", {})
        except Exception as e:
            raise RuntimeError(f"Failed to perform structured scrape: {e}")

    def map_site(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        r"""Map a website to retrieve all accessible URLs.

        Args:
            url (str): The URL of the site to map.
            params (Optional[Dict[str, Any]]): Additional parameters for the
                map request (e.g. ``search``, ``limit``). Defaults to `None`.

        Returns:
            List[str]: A list containing the URLs found on the site.

        Raises:
            RuntimeError: If the mapping process fails.
        """
        try:
            map_result = self.app.map(url=url, **(params or {}))
            links = getattr(map_result, "links", map_result)
            urls: List[str] = []
            for link in links or []:
                url_value = getattr(link, "url", None)
                if url_value is None and isinstance(link, dict):
                    url_value = link.get("url")
                urls.append(url_value if url_value is not None else link)
            return urls
        except Exception as e:
            raise RuntimeError(f"Failed to map the site: {e}")

    def search(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        r"""Search the web and optionally scrape the result pages.

        Args:
            query (str): The search query.
            params (Optional[Dict[str, Any]]): Additional parameters for the
                search request (e.g. ``limit``, ``sources``, ``location``,
                ``scrape_options``). Defaults to `None`.

        Returns:
            Any: The search results, grouped by source.

        Raises:
            RuntimeError: If the search process fails.
        """
        try:
            return _to_dict(self.app.search(query, **(params or {})))
        except Exception as e:
            raise RuntimeError(f"Failed to search: {e}")
