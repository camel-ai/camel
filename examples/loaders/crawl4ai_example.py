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

from pydantic import BaseModel, Field

from camel.loaders import Crawl4AI


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
        class MovieResponse(BaseModel):
            title: str = Field(..., description="The title of the movie.")
            year: int = Field(
                ..., description="The release year of the movie."
            )
            rating: float = Field(..., description="The rating of the movie.")

        # api_key = "OPENAI_API_KEY"
        structured_scrape_result = await crawler.structured_scrape(
            "https://www.imdb.com/title/tt0111161/",
            response_format=MovieResponse,
            # api_key=api_key
        )
        print("\n--- Structured Scrape Result: ---")
        print(structured_scrape_result)
        print("-" * 20)
    except RuntimeError as e:
        print(e)


if __name__ == "__main__":
    asyncio.run(main())
