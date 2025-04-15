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

from typing import Optional
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel

from camel.loaders import Crawl4AI


# Dummy CrawlResult to simulate the results from AsyncWebCrawler.arun
class DummyCrawlResult:
    def __init__(
        self, markdown: str, cleaned_html: str, links: Optional[dict] = None
    ):
        self.markdown = markdown
        self.cleaned_html = cleaned_html
        self.links = links or {}


URL = "https://example.com"


# ------------------------
# Test Cases for Crawl4AI
# ------------------------


def test_init():
    crawler = Crawl4AI()
    # Verify that the crawler attribute is set to AsyncWebCrawler
    assert crawler.crawl is not None


@pytest.mark.asyncio
async def test_crawl_success():
    dummy_result = DummyCrawlResult(
        markdown="Test markdown", cleaned_html="<html></html>", links={}
    )

    with patch.object(
        Crawl4AI, "_run_crawler", new_callable=AsyncMock
    ) as mock_run_crawler:
        mock_run_crawler.return_value = dummy_result
        crawler = Crawl4AI()
        results = await crawler.crawl(URL, max_depth=1)
        assert isinstance(results, list)
        page = results[0]
        assert page["url"] == URL
        assert page["markdown"] == "Test markdown"
        assert page["cleaned_html"] == "<html></html>"
        assert page["links"] == {}


@pytest.mark.asyncio
async def test_crawl_failure_in_run():
    with patch.object(
        Crawl4AI, "_run_crawler", new_callable=AsyncMock
    ) as mock_run_crawler:
        mock_run_crawler.side_effect = Exception(
            f"Error crawling {URL}: Crawl error"
        )
        crawler = Crawl4AI()
        with pytest.raises(
            RuntimeError, match=f"Error crawling {URL}: Crawl error"
        ):
            await crawler.crawl(URL)


@pytest.mark.asyncio
async def test_scrape_success():
    dummy_result = DummyCrawlResult(
        markdown="Scraped markdown",
        cleaned_html="<html>scraped</html>",
        links={},
    )

    with patch.object(
        Crawl4AI, "_run_crawler", new_callable=AsyncMock
    ) as mock_run_crawler:
        mock_run_crawler.return_value = dummy_result
        crawler = Crawl4AI()
        result = await crawler.scrape(URL)
        assert result["url"] == URL
        assert result["markdown"] == "Scraped markdown"
        assert result["cleaned_html"] == "<html>scraped</html>"
        assert result["links"] == {}


@pytest.mark.asyncio
async def test_structured_scrape_success():
    dummy_result = DummyCrawlResult(
        markdown="Scraped markdown",
        cleaned_html="<html>scraped</html>",
        links={},
    )

    class DummySchema(BaseModel):
        field: str

    with patch.object(
        Crawl4AI, "_run_crawler", new_callable=AsyncMock
    ) as mock_run_crawler:
        mock_run_crawler.return_value = dummy_result
        crawler = Crawl4AI()
        result = await crawler.structured_scrape(
            URL, DummySchema, llm_provider="openai"
        )
        assert result.markdown == "Scraped markdown"
        assert result.cleaned_html == "<html>scraped</html>"
        assert result.links == {}


@pytest.mark.asyncio
async def test_structured_scrape_failure():
    # Simulate a failure in the structured scrape method.
    with patch.object(
        Crawl4AI, "_run_crawler", new_callable=AsyncMock
    ) as mock_run_crawler:
        mock_run_crawler.side_effect = RuntimeError("Structured scrape failed")
        crawler = Crawl4AI()

        class DummySchema(BaseModel):
            field: str

        with pytest.raises(RuntimeError, match="Structured scrape failed"):
            await crawler.structured_scrape(URL, DummySchema)


@pytest.mark.asyncio
async def test_map_site_success():
    # Simulate the crawl method to return a list with a dummy page
    dummy_page = {
        "url": "https://example.com/page1",
        "markdown": "md",
        "cleaned_html": "html",
    }

    # Instead of patching AsyncWebCrawler here, patch the crawl method itself
    async def dummy_crawl(url: str, **kwargs):
        return [dummy_page]

    crawler = Crawl4AI()
    crawler.crawl = dummy_crawl  # Override crawl method for testing

    urls = await crawler.map_site(URL)
    assert urls == ["https://example.com/page1"]


@pytest.mark.asyncio
async def test_map_site_failure():
    # Simulate crawl raising an exception in map_site
    async def dummy_crawl_fail(url: str, **kwargs):
        raise Exception("Mapping error")

    crawler = Crawl4AI()
    crawler.crawl = (
        dummy_crawl_fail  # Override crawl method to simulate failure
    )

    with pytest.raises(RuntimeError, match="Failed to map url"):
        await crawler.map_site(URL)
