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

from typing import List
from unittest.mock import patch

import pytest
from pydantic import BaseModel, Field

from camel.loaders import CrwReader


def test_init():
    with patch('crw.CrwClient') as MockCrwClient:
        mock_app = MockCrwClient.return_value
        api_key = 'test_api_key'
        api_url = 'https://api.test.com'
        crw = CrwReader(api_key=api_key, api_url=api_url)

        assert crw._api_key == api_key
        assert crw._api_url == api_url
        assert crw.app == mock_app


def test_crawl_success():
    with patch('crw.CrwClient') as MockCrwClient:
        mock_app = MockCrwClient.return_value
        crw = CrwReader(api_key='test_api_key', api_url='https://api.test.com')
        url = 'https://example.com'
        response = {'status': 'completed', 'data': []}
        mock_app.crawl.return_value = response

        result = crw.crawl(url)
        assert result == response


def test_crawl_failure():
    with patch('crw.CrwClient') as MockCrwClient:
        mock_app = MockCrwClient.return_value
        crw = CrwReader(api_key='test_api_key', api_url='https://api.test.com')
        url = 'https://example.com'
        mock_app.crawl.side_effect = Exception('Error')

        try:
            crw.crawl(url)
        except RuntimeError as e:
            assert 'Failed to crawl the URL' in str(e)


def test_scrape_success():
    with patch('crw.CrwClient') as MockCrwClient:
        mock_app = MockCrwClient.return_value
        crw = CrwReader(api_key='test_api_key', api_url='https://api.test.com')
        url = 'https://example.com'
        response = {'markdown': 'Scraped content'}
        mock_app.scrape.return_value = response

        result = crw.scrape(url)
        assert result == response


def test_scrape_failure():
    with patch('crw.CrwClient') as MockCrwClient:
        mock_app = MockCrwClient.return_value
        crw = CrwReader(api_key='test_api_key', api_url='https://api.test.com')
        url = 'https://example.com'
        mock_app.scrape.side_effect = Exception('Error')

        try:
            crw.scrape(url)
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


def test_structured_scrape_success():
    with patch('crw.CrwClient') as MockCrwClient:
        mock_app = MockCrwClient.return_value
        crw = CrwReader(api_key='test_api_key', api_url='https://api.test.com')
        url = 'https://example.com'
        response_format = TopArticlesSchema
        extracted = {'top': []}
        mock_app.scrape.return_value = {'json': extracted}

        result = crw.structured_scrape(url, response_format)
        assert result == extracted


def test_structured_scrape_failure():
    with patch('crw.CrwClient') as MockCrwClient:
        mock_app = MockCrwClient.return_value
        crw = CrwReader(api_key='test_api_key', api_url='https://api.test.com')
        url = 'https://example.com'
        response_format = TopArticlesSchema
        mock_app.scrape.side_effect = Exception('Error')

        try:
            crw.structured_scrape(url, response_format)
        except RuntimeError as e:
            assert 'Failed to perform structured scrape' in str(e)


def test_map_site_success():
    with patch('crw.CrwClient') as MockCrwClient:
        mock_app = MockCrwClient.return_value
        crw = CrwReader(api_key='test_api_key', api_url='https://api.test.com')
        url = 'https://example.com'

        class _Link:
            def __init__(self, url):
                self.url = url

        mock_app.map.return_value = type(
            'MapData', (), {'links': [_Link('https://example.com')]}
        )()

        result = crw.map_site(url)
        assert result == ['https://example.com']


def test_map_site_failure():
    with patch('crw.CrwClient') as MockCrwClient:
        mock_app = MockCrwClient.return_value
        crw = CrwReader(api_key='test_api_key', api_url='https://api.test.com')
        url = 'https://example.com'
        mock_app.map.side_effect = Exception('Error')

        try:
            crw.map_site(url)
        except RuntimeError as e:
            assert 'Failed to map the site' in str(e)


def test_search_success():
    with patch('crw.CrwClient') as MockCrwClient:
        mock_app = MockCrwClient.return_value
        crw = CrwReader(api_key='test_api_key', api_url='https://api.test.com')
        query = 'camel ai'
        response = {'web': [{'url': 'https://example.com'}]}
        mock_app.search.return_value = response

        result = crw.search(query, params={'limit': 1})

        assert result == response
        mock_app.search.assert_called_once_with(query, limit=1)


def test_search_failure():
    with patch('crw.CrwClient') as MockCrwClient:
        mock_app = MockCrwClient.return_value
        crw = CrwReader(api_key='test_api_key', api_url='https://api.test.com')
        mock_app.search.side_effect = Exception('Error')

        with pytest.raises(RuntimeError) as exc_info:
            crw.search('camel ai')
        assert 'Failed to search' in str(exc_info.value)
