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

from typing import List
from unittest.mock import patch

from pydantic import BaseModel, Field

from camel.loaders import Firecrawl


def test_init():
    with patch('firecrawl.FirecrawlApp') as MockFirecrawlApp:
        mock_app = MockFirecrawlApp.return_value
        api_key = 'test_api_key'
        api_url = 'https://api.test.com'
        firecrawl = Firecrawl(api_key=api_key, api_url=api_url)

        assert firecrawl._api_key == api_key
        assert firecrawl._api_url == api_url
        assert firecrawl.app == mock_app


def test_crawl_success():
    with patch('firecrawl.FirecrawlApp') as MockFirecrawlApp:
        mock_app = MockFirecrawlApp.return_value
        firecrawl = Firecrawl(
            api_key='test_api_key', api_url='https://api.test.com'
        )
        url = 'https://example.com'
        response = 'Crawl content'
        mock_app.crawl_url.return_value = response

        result = firecrawl.crawl(url)
        assert result == response


def test_crawl_failure():
    with patch('firecrawl.FirecrawlApp') as MockFirecrawlApp:
        mock_app = MockFirecrawlApp.return_value
        firecrawl = Firecrawl(
            api_key='test_api_key', api_url='https://api.test.com'
        )
        url = 'https://example.com'
        mock_app.crawl_url.side_effect = Exception('Error')

        try:
            firecrawl.crawl(url)
        except RuntimeError as e:
            assert 'Failed to crawl the URL' in str(e)


def test_check_crawl_job_success():
    with patch('firecrawl.FirecrawlApp') as MockFirecrawlApp:
        mock_app = MockFirecrawlApp.return_value
        firecrawl = Firecrawl(
            api_key='test_api_key', api_url='https://api.test.com'
        )
        job_id = 'job_123'
        response = 'Job status'
        mock_app.check_crawl_status.return_value = response

        result = firecrawl.check_crawl_job(job_id)
        assert result == response


def test_check_crawl_job_failure():
    with patch('firecrawl.FirecrawlApp') as MockFirecrawlApp:
        mock_app = MockFirecrawlApp.return_value
        firecrawl = Firecrawl(
            api_key='test_api_key', api_url='https://api.test.com'
        )
        job_id = 'job_123'
        mock_app.check_crawl_status.side_effect = Exception('Error')

        try:
            firecrawl.check_crawl_job(job_id)
        except RuntimeError as e:
            assert 'Failed to check the crawl job status' in str(e)


def test_scrape_success():
    with patch('firecrawl.FirecrawlApp') as MockFirecrawlApp:
        mock_app = MockFirecrawlApp.return_value
        firecrawl = Firecrawl(
            api_key='test_api_key', api_url='https://api.test.com'
        )
        url = 'https://example.com'
        response = 'Scraped content'
        mock_app.scrape_url.return_value = response

        result = firecrawl.scrape(url)
        assert result == response


def test_scrape_failure():
    with patch('firecrawl.FirecrawlApp') as MockFirecrawlApp:
        mock_app = MockFirecrawlApp.return_value
        firecrawl = Firecrawl(
            api_key='test_api_key', api_url='https://api.test.com'
        )
        url = 'https://example.com'
        mock_app.scrape_url.side_effect = Exception('Error')

        try:
            firecrawl.scrape(url)
        except RuntimeError as e:
            assert 'Failed to scrape the URL' in str(e)


class ArticleSchema(BaseModel):
    title: str
    points: int
    by: str
    commentsURL: str


class TopArticlesSchema(BaseModel):
    top: List[ArticleSchema] = Field(
        ..., max_length=5, description="Top 5 stories"
    )


def test_structured_scrape_failure():
    with patch('firecrawl.FirecrawlApp') as MockFirecrawlApp:
        mock_app = MockFirecrawlApp.return_value
        firecrawl = Firecrawl(
            api_key='test_api_key', api_url='https://api.test.com'
        )
        url = 'https://example.com'
        response_format = TopArticlesSchema
        mock_app.scrape_url.side_effect = Exception('Error')

        try:
            firecrawl.structured_scrape(url, response_format)
        except RuntimeError as e:
            assert 'Failed to perform structured scrape' in str(e)


def test_map_site_success():
    with patch('firecrawl.FirecrawlApp') as MockFirecrawlApp:
        mock_app = MockFirecrawlApp.return_value
        firecrawl = Firecrawl(
            api_key='test_api_key', api_url='https://api.test.com'
        )
        url = 'https://example.com'
        map_result = ['https://example.com']
        mock_app.map_url.return_value = map_result

        result = firecrawl.map_site(url)
        assert result == map_result


def test_map_site_failure():
    with patch('firecrawl.FirecrawlApp') as MockFirecrawlApp:
        mock_app = MockFirecrawlApp.return_value
        firecrawl = Firecrawl(
            api_key='test_api_key', api_url='https://api.test.com'
        )
        url = 'https://example.com'
        mock_app.map_url.side_effect = Exception('Error')

        try:
            firecrawl.map_site(url)
        except RuntimeError as e:
            assert 'Failed to map the site' in str(e)
