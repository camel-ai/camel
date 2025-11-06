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
from unittest.mock import MagicMock, patch

import pytest

from camel.loaders.scrapegraph_reader import ScrapeGraphAI


@pytest.fixture
def scrapegraph_ai():
    with patch("scrapegraph_py.Client") as mock_client:
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        yield ScrapeGraphAI(api_key="test_api_key")


def test_init_with_api_key():
    with patch("scrapegraph_py.Client") as mock_client:
        ScrapeGraphAI(api_key="test_api_key")
        mock_client.assert_called_once_with(api_key="test_api_key")


def test_init_with_env_var():
    with (
        patch("scrapegraph_py.Client") as mock_client,
        patch.dict(os.environ, {"SCRAPEGRAPH_API_KEY": "env_api_key"}),
    ):
        ScrapeGraphAI()
        mock_client.assert_called_once_with(api_key="env_api_key")


def test_search_success(scrapegraph_ai):
    mock_response = {"answer": "test answer", "references": ["url1", "url2"]}
    scrapegraph_ai.client.searchscraper.return_value = mock_response

    result = scrapegraph_ai.search("test query")
    assert result == mock_response
    scrapegraph_ai.client.searchscraper.assert_called_once_with(
        user_prompt="test query"
    )


def test_search_failure(scrapegraph_ai):
    scrapegraph_ai.client.searchscraper.side_effect = Exception(
        "Search failed"
    )

    with pytest.raises(
        RuntimeError, match="Failed to perform search: Search failed"
    ):
        scrapegraph_ai.search("test query")


def test_scrape_success(scrapegraph_ai):
    mock_response = {"request_id": "123", "result": {"data": "test data"}}
    scrapegraph_ai.client.smartscraper.return_value = mock_response

    result = scrapegraph_ai.scrape(
        website_url="https://example.com",
        user_prompt="Extract title and description",
    )
    assert result == mock_response
    scrapegraph_ai.client.smartscraper.assert_called_once_with(
        website_url="https://example.com",
        user_prompt="Extract title and description",
        website_html=None,
    )


def test_scrape_with_html(scrapegraph_ai):
    mock_response = {"request_id": "123", "result": {"data": "test data"}}
    scrapegraph_ai.client.smartscraper.return_value = mock_response

    result = scrapegraph_ai.scrape(
        website_url="https://example.com",
        user_prompt="Extract title and description",
        website_html="<html>test</html>",
    )
    assert result == mock_response
    scrapegraph_ai.client.smartscraper.assert_called_once_with(
        website_url="https://example.com",
        user_prompt="Extract title and description",
        website_html="<html>test</html>",
    )


def test_scrape_failure(scrapegraph_ai):
    scrapegraph_ai.client.smartscraper.side_effect = Exception("Scrape failed")

    with pytest.raises(
        RuntimeError, match="Failed to perform scrape: Scrape failed"
    ):
        scrapegraph_ai.scrape(
            website_url="https://example.com",
            user_prompt="Extract title and description",
        )


def test_close(scrapegraph_ai):
    scrapegraph_ai.close()
    scrapegraph_ai.client.close.assert_called_once()
