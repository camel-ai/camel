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

"""
Example demonstrating how to use the ScrapeGraphAI reader for web scraping and
searching.

This example shows:
1. How to initialize the ScrapeGraphAI reader
2. How to perform AI-powered web searches
3. How to scrape websites with specific instructions
4. How to handle errors and close the connection
"""

import os
from typing import Any, Dict

from camel.loaders.scrapegraph_reader import ScrapeGraphAI


def search_example(api_key: str) -> Dict[str, Any]:
    r"""Example of performing an AI-powered web search."""
    # Initialize the ScrapeGraphAI reader
    scraper = ScrapeGraphAI(api_key=api_key)

    try:
        # Perform a search
        search_query = "What are the latest developments in AI?"
        result = scraper.search(user_prompt=search_query)

        print("\nSearch Results:")
        print(f"Answer: {result.get('answer', 'No answer found')}")
        print("References:")
        for url in result.get('references', []):
            print(f"- {url}")

        return result
    finally:
        # Always close the connection
        scraper.close()


def scrape_example(api_key: str) -> Dict[str, Any]:
    r"""Example of scraping a website with specific instructions."""
    # Initialize the ScrapeGraphAI reader
    scraper = ScrapeGraphAI(api_key=api_key)

    try:
        # Scrape a website with specific instructions
        website_url = "https://example.com"
        instructions = """
        Extract the following information:
        1. Main title of the page
        2. All paragraph texts
        3. Any links to other pages
        """

        result = scraper.scrape(
            website_url=website_url, user_prompt=instructions
        )

        print("\nScraping Results:")
        print(f"Request ID: {result.get('request_id', 'No ID')}")
        print("Extracted Data:")
        print(result.get('result', {}))

        return result
    finally:
        # Always close the connection
        scraper.close()


def main():
    # Get API key from environment variable or use a placeholder
    api_key = os.environ.get("SCRAPEGRAPH_API_KEY", "your_api_key_here")

    if api_key == "your_api_key_here":
        print("Please set your SCRAPEGRAPH_API_KEY environment variable")
        return

    print("Running search example...")
    search_example(api_key)

    print("\nRunning scrape example...")
    scrape_example(api_key)


if __name__ == "__main__":
    main()
