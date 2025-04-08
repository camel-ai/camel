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

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class Crawl4AI:
    r"""Class for converting websites into LLM-ready data.

    This class uses asynchronous crawling with CSS selectors or LLM-based
    extraction to convert entire websites into structured data.

    References:
        https://docs.crawl4ai.com/
    """

    def __init__(self) -> None:
        from crawl4ai import AsyncWebCrawler

        self.crawler_class = AsyncWebCrawler

    async def _run_crawler(self, url: str, **kwargs) -> Any:
        r"""Run the asynchronous web crawler on a given URL.

        Args:
            url (str): URL to crawl or scrape.
            **kwargs: Additional keyword arguments for crawler configuration.

        Returns:
            Any: The result from the crawler.

        Raises:
            RuntimeError: If crawler execution fails.
        """

        try:
            async with self.crawler_class() as c:
                return await c.arun(url, **kwargs)
        except Exception as e:
            logger.error("Crawler run failed: %s", e)
            raise RuntimeError(f"Crawler run failed: {e}") from e

    async def crawl(
        self,
        start_url: str,
        max_depth: int = 1,
        extraction_strategy=None,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        r"""Crawl a URL and its subpages using breadth-first search.

        Args:
            start_url (str): URL to start crawling from.
            max_depth (int, optional): Maximum depth of links to follow
                (default: :obj:`1`)
            extraction_strategy (ExtractionStrategy, optional): Strategy
                for data extraction. (default: :obj:`None`)
            **kwargs: Additional arguments for crawler configuration.

        Returns:
            List[Dict[str, Any]]: List of crawled page results.

        Raises:
            RuntimeError: If an error occurs during crawling.
        """

        all_results: List[Dict[str, Any]] = []
        visited_urls: Set[str] = set()
        queue: asyncio.Queue = asyncio.Queue()

        await queue.put((start_url, 1))
        visited_urls.add(start_url)

        while not queue.empty():
            url, depth = await queue.get()
            try:
                result = await self._run_crawler(
                    url, extraction_strategy=extraction_strategy, **kwargs
                )
                all_results.append(
                    {
                        "url": url,
                        "raw_result": result,
                        "markdown": result.markdown,
                        "cleaned_html": result.cleaned_html,
                        "links": result.links,
                    }
                )

                if depth < max_depth and result.links:
                    for _, links in result.links.items():
                        for link in links:
                            if (
                                'href' in link
                                and link['href'] not in visited_urls
                            ):
                                visited_urls.add(link['href'])
                                await queue.put((link['href'], depth + 1))

            except Exception as e:
                logger.error("Error crawling %s: %s", url, e)
                raise RuntimeError(f"Error crawling {url}: {e}") from e

            queue.task_done()

        await queue.join()

        return all_results

    async def scrape(
        self,
        url: str,
        extraction_strategy=None,
        **kwargs,
    ) -> Dict[str, Any]:
        r"""Scrape a single URL using CSS or LLM-based extraction.

        Args:
            url (str): URL to scrape.
            extraction_strategy (ExtractionStrategy, optional): Extraction
                strategy to use. (default: :obj:`None`)
            **kwargs: Additional arguments for crawler configuration.

        Returns:
            Dict[str, Any]: Dictionary containing scraped data such as markdown
                and HTML content.

        Raises:
            RuntimeError: If scraping fails.
        """

        result = await self._run_crawler(
            url, extraction_strategy=extraction_strategy, **kwargs
        )
        return {
            "url": url,
            "raw_result": result,
            "markdown": result.markdown,
            "cleaned_html": result.cleaned_html,
            "links": result.links,
        }

    async def structured_scrape(
        self,
        url: str,
        response_format: BaseModel,
        api_key: Optional[str] = None,
        llm_provider: str = 'ollama/llama3',
        **kwargs,
    ) -> Any:
        r"""Extract structured data from a URL using an LLM.

        Args:
            url (str): URL to scrape.
            response_format (BaseModel): Model defining the expected output
                schema.
            api_key (str, optional): API key for the LLM provider
                (default: :obj:`None`).
            llm_provider (str, optional): Identifier for the LLM provider
                (default: :obj:`'ollama/llama3'`).
            **kwargs: Additional arguments for crawler configuration.

        Returns:
            Any: Crawl result containing the extracted data
                structured according to the schema.

        Raises:
            ValidationError: If extracted data does not match the schema.
            RuntimeError: If extraction fails.
        """

        from crawl4ai.extraction_strategy import (
            LLMExtractionStrategy,
        )

        extraction_strategy = LLMExtractionStrategy(
            provider=llm_provider,
            api_token=api_key,
            schema=response_format.model_json_schema(),
            extraction_type="schema",
            instruction="Extract the data according to the schema.",
        )

        try:
            return await self._run_crawler(
                url, extraction_strategy=extraction_strategy, **kwargs
            )
        except ValidationError as e:
            raise ValidationError(
                f"Extracted data does not match schema: {e}"
            ) from e
        except Exception as e:
            raise RuntimeError(e) from e

    async def map_site(self, start_url: str, **kwargs) -> List[str]:
        r"""Map a website by extracting all accessible URLs.

        Args:
            start_url (str): Starting URL to map.
            **kwargs: Additional configuration arguments.

        Returns:
            List[str]: List of URLs discovered on the website.

        Raises:
            RuntimeError: If mapping fails.
        """

        try:
            result = await self.crawl(start_url, **kwargs)
            return [page["url"] for page in result]
        except Exception as e:
            raise RuntimeError(f"Failed to map url: {e}") from e
