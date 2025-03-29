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


# TODO: add `logger` statements to log info throughout the process
# TODO: recheck type hinting and the methods added


import asyncio
import os
from typing import Any, Dict, List, Optional

from crawl4ai import (  # type: ignore[import-untyped]
    AsyncWebCrawler,
    CrawlerRunConfig,
    CrawlResult,
    LLMConfig,
)
from crawl4ai.extraction_strategy import (  # type: ignore[import-untyped]
    LLMExtractionStrategy,
)
from pydantic import BaseModel, ValidationError


class Crawl4AI:
    r"""
    Crawl4AI allows you to turn entire websites into LLM-ready data,
    using either CSS selectors or LLM-based extraction for structured data.

    Args:
        None (for now - no API keys like Firecrawl)

    References:
       [https://docs.crawl4ai.com/](https://docs.crawl4ai.com/)
    """

    def __init__(self) -> None:
        self.crawler = AsyncWebCrawler

    async def _run_crawler(
        self,
        url: str,
        config: CrawlerRunConfig,
    ) -> Any:
        r"""
        Helper function to encapsulate the crawler execution.

        Args:
            url: URL to crawl/scrape.
            config: CrawlerRunConfig object.
        Returns:
            The result from the crawler.
        """
        try:
            async with self.crawler() as c:
                result = await c.arun(url, config=config)
                return result
        except Exception as e:
            raise RuntimeError(f"Crawler run failed: {e}") from e

    async def crawl(
        self,
        start_url: str,
        max_depth: int = 1,
        extraction_strategy: Optional[LLMExtractionStrategy] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        r"""Crawl a URL and its subpages using BREADTH-FIRST SEARCH (BFS).

        Args:
            start_url (str): The URL to start crawling from.
            max_depth (int): Maximum depth of links to follow.
            extraction_strategy (Optional): Extraction strategy.
            **kwargs: Additional keyword arguments for CrawlerRunConfig.

        Returns:
            List[Dict[str, Any]]: Crawled pages.

        Raises:
            RuntimeError: If the crawling process fails.
        """
        all_results: List[Dict[str, Any]] = []
        visited_urls: set[str] = set()
        queue: asyncio.Queue[tuple[str, int]] = asyncio.Queue()

        await queue.put((start_url, 1))
        visited_urls.add(start_url)

        config = CrawlerRunConfig(
            extraction_strategy=extraction_strategy,
            **kwargs,
        )
        async with self.crawler() as c:
            while not queue.empty():
                url, depth = await queue.get()
                try:
                    result: CrawlResult = await c.arun(url, config=config)
                    all_results.append(
                        {
                            "url": url,
                            "raw_result": result,
                            "markdown": result.markdown,
                            "cleaned_html": result.cleaned_html,
                        }
                    )

                    if depth < max_depth and result.links:
                        for _, links in result.links.items():
                            for link in links:
                                if link['href'] not in visited_urls:
                                    visited_urls.add(link['href'])
                                    await queue.put((link['href'], depth + 1))

                except Exception as e:
                    print(f"Error crawling {url}: {e}")

                queue.task_done()

            await queue.join()

        return all_results

    async def scrape(
        self,
        url: str,
        extraction_strategy: Optional[LLMExtractionStrategy] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        r"""Scrape a single URL, supporting CSS or LLM-based extraction.

        Args:
            url (str): The URL to scrape.
            extraction_strategy (Optional[LLMExtractionStrategy]]):
                Extraction strategy.
            **kwargs: Additional keyword arguments for CrawlerRunConfig.

        Returns:
            Dict[str, Any]:  The scraped data.

        Raises:
            RuntimeError: If the scraping process fails.
        """
        config = CrawlerRunConfig(
            extraction_strategy=extraction_strategy, **kwargs
        )
        result = await self._run_crawler(url, config)
        return {
            "url": url,
            "raw_result": result,
            "markdown": result.markdown,
            "cleaned_html": result.cleaned_html,
        }

    async def structured_scrape(
        self,
        url: str,
        response_format: BaseModel,
        llm_provider: str = 'openai/gpt-4o-mini',
        **kwargs: Any,
    ) -> Dict[str, Any]:
        r"""Use LLM to extract structured data from a given URL.

        Args:
            url (str): The URL to scrape.
            response_format (BaseModel): A model for the expected output.
            **kwargs: Additional keyword arguments for CrawlerRunConfig

        Returns:
            Dict[str, Any]: The extracted data.

        Raises:
            RuntimeError: If the scraping or data conversion fails.
            ValidationError: If the extracted data
                            doesn't conform to the schema.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "Please set the OPENAI_API_KEY environment variable."
            )

        extraction_strategy = LLMExtractionStrategy(
            llm_config=LLMConfig(provider=llm_provider, api_token=api_key),
            schema=response_format.model_json_schema(),
            extraction_type="schema",
            instruction="Extract the data according to the schema.",
        )

        config = CrawlerRunConfig(
            extraction_strategy=extraction_strategy, **kwargs
        )
        try:
            return await self._run_crawler(url, config)
        except ValidationError as e:
            raise ValidationError(
                f"Extracted data does not match schema: {e}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Structured scrape failed: {e}") from e

    async def map_site(self, url: str, **kwargs) -> List[str]:
        r"""
        Map a website to retrieve all accessible URLs (basic implementation).
        This is similar to crawling but only returns the URLs, not the content.

        Args:
            url (str): starting url.
            **kwargs: config kwargs
        Returns:
            List[str]: A list of URLs found on the site.

        Raises:
            RuntimeError: If an error occurs during the process.
        """
        try:
            result = await self.crawl(url, **kwargs)
            return [page["url"] for page in result]
        except Exception as e:
            raise RuntimeError(f"Failed to map url: {e}") from e


# --- Example Usage (Update the main function to use the corrected crawl)---
async def main():
    r"""
    Example usage of the Crawl4AI crawler.

    Performs a breadth-first crawl of the given URL, up to a maximum depth.
    Prints out the results, including any extracted data.
    """
    crawler = Crawl4AI()

    # --- Crawling (BFS) ---
    try:
        crawl_results = await crawler.crawl(
            "https://github.com/camel-ai/camel/issues/1685", max_depth=1
        )
        print("\n--- Crawl Results (BFS): ---")
        for page_data in crawl_results:
            print(f"URL: {page_data['url']}")
            if page_data["markdown"]:
                print(f"Markdown Data: {page_data['markdown']}")
            print("-" * 20)

        # --- Scraping ---
        scrape_result = await crawler.scrape(
            "https://github.com/camel-ai/camel/issues/1685"
        )
        print("\n--- Scrape Result: ---")
        print(f"URL: {scrape_result['url']}")
        print(f"Markdown Data: {scrape_result['markdown']}")
        print("-" * 20)

        # --- Structured Scraping ---
        from pydantic import BaseModel, Field

        class MovieResponse(BaseModel):
            title: str = Field(..., description="The title of the movie.")
            year: int = Field(
                ..., description="The release year of the movie."
            )
            rating: float = Field(..., description="The rating of the movie.")

        structured_scrape_result = await crawler.structured_scrape(
            "https://www.imdb.com/title/tt0111161/",
            response_format=MovieResponse,
        )
        print("\n--- Structured Scrape Result: ---")
        print(f"URL: {structured_scrape_result[0].url}")
        print(f"Markdown Data: {structured_scrape_result[0].markdown}")
        print("-" * 20)
    except RuntimeError as e:
        print(e)


if __name__ == "__main__":
    asyncio.run(main())
