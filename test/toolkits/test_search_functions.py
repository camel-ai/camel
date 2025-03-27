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
from unittest import mock
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests
import wikipedia

from camel.toolkits import SearchToolkit


@pytest.fixture
def search_toolkit():
    return SearchToolkit()


def test_search_wiki_normal(search_toolkit):
    expected_output = (
        "Erygia sigillata is a species of moth in the family Erebidae found "
        "in Himachal Pradesh, Northern India. The moth was officially "
        "recognized and classified in 1892."
    )

    assert search_toolkit.search_wiki("Erygia sigillata") == expected_output


def test_search_wiki_not_found(search_toolkit):
    search_output = search_toolkit.search_wiki(
        "South Africa Women Football Team"
    )
    assert search_output.startswith(
        "There is no page in Wikipedia corresponding to entity South Africa "
        "Women Football Team, please specify another word to describe the "
        "entity to be searched."
    )


def test_search_wiki_with_ambiguity(search_toolkit):
    expected_output = wikipedia.summary(
        "Google", sentences=5, auto_suggest=False
    )
    assert search_toolkit.search_wiki("Google LLC") == expected_output


def test_google_api():
    # Mock the Google search api

    # Mock environment variables
    with patch.dict(
        os.environ,
        {
            'GOOGLE_API_KEY': 'fake_api_key',
            'SEARCH_ENGINE_ID': 'fake_search_engine_id',
        },
    ):
        # Create a MagicMock object for the response
        mock_response = MagicMock()
        mock_response.status_code = 200

        # Mock the requests.get method
        with patch('requests.get', return_value=mock_response) as mock_get:
            # Define the expected URL
            GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
            SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")
            url = (
                f"https://www.googleapis.com/customsearch/v1?"
                f"key={GOOGLE_API_KEY}&cx={SEARCH_ENGINE_ID}&q=any"
            )

            # Call the function under test
            result = requests.get(url)

            # Assert that requests.get was called with the correct URL
            mock_get.assert_called_with(url)

            # Assert that the status_code is as expected
            assert result.status_code == 200


search_duckduckgo = SearchToolkit().search_duckduckgo


def test_search_duckduckgo_text():
    # Mock the DDGS class and its text method
    with mock.patch("duckduckgo_search.DDGS") as MockDDGS:
        # Create a mock instance of DDGS
        mock_ddgs_instance = MockDDGS.return_value
        mock_ddgs_instance.text.return_value = [
            {
                "title": "Test Title 1",
                "body": "Test Body 1",
                "href": "https://example1.com",
            },
            {
                "title": "Test Title 2",
                "body": "Test Body 2",
                "href": "https://example2.com",
            },
        ]

        # Call the function with the mocked DDGS
        result = search_duckduckgo(
            query="test query", source="text", max_results=2
        )

        # Check if the result is as expected
        assert result == [
            {
                "result_id": 1,
                "title": "Test Title 1",
                "description": "Test Body 1",
                "url": "https://example1.com",
            },
            {
                "result_id": 2,
                "title": "Test Title 2",
                "description": "Test Body 2",
                "url": "https://example2.com",
            },
        ]

        mock_ddgs_instance.text.assert_called_once_with(
            keywords="test query", max_results=2
        )


def test_search_duckduckgo_images():
    # Mock the DDGS class and its images method
    with mock.patch("duckduckgo_search.DDGS") as MockDDGS:
        mock_ddgs_instance = MockDDGS.return_value
        mock_ddgs_instance.images.return_value = [
            {
                "title": "Image Title 1",
                "image": "https://image1.com",
                "url": "https://example1.com",
                "source": "Example Source 1",
            },
            {
                "title": "Image Title 2",
                "image": "https://image2.com",
                "url": "https://example2.com",
                "source": "Example Source 2",
            },
        ]

        # Call the function with the mocked DDGS for images
        result = search_duckduckgo(
            query="test query", source="images", max_results=2
        )

        # Check if the result matches the expected output
        assert result == [
            {
                "result_id": 1,
                "title": "Image Title 1",
                "image": "https://image1.com",
                "url": "https://example1.com",
                "source": "Example Source 1",
            },
            {
                "result_id": 2,
                "title": "Image Title 2",
                "image": "https://image2.com",
                "url": "https://example2.com",
                "source": "Example Source 2",
            },
        ]

        mock_ddgs_instance.images.assert_called_once_with(
            keywords="test query", max_results=2
        )


@patch('requests.get')
def test_search_baidu(mock_get, search_toolkit):
    # Mock the response from Baidu search
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "utf-8"
    mock_response.text = """
    <html>
        <head><title>Baidu Search</title></head>
        <body>
            <div class="result c-container">
                <h3 class="t">
                    <a href="https://example1.com">Test Title 1</a>
                </h3>
                <div class="c-abstract">Test Abstract 1</div>
            </div>
            <div class="result c-container">
                <h3 class="t">
                    <a href="https://example2.com">Test Title 2</a>
                </h3>
                <div class="c-abstract">Test Abstract 2</div>
            </div>
        </body>
    </html>
    """
    mock_get.return_value = mock_response

    # Call the function under test
    result = search_toolkit.search_baidu(query="test query", max_results=5)

    # Expected output
    expected_output = {
        "results": [
            {
                "result_id": 1,
                "title": "Test Title 1",
                "description": "Test Abstract 1",
                "url": "https://example1.com",
            },
            {
                "result_id": 2,
                "title": "Test Title 2",
                "description": "Test Abstract 2",
                "url": "https://example2.com",
            },
        ]
    }

    # Assertions
    assert result == expected_output
    mock_get.assert_called_once_with(
        "https://www.baidu.com/s",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.baidu.com",
        },
        params={"wd": "test query", "rn": "5"},
    )


@patch('requests.get')
def test_search_bing(mock_get, search_toolkit):
    # Mock the response from Bing search
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.encoding = "utf-8"
    mock_response.text = """
    <html>
        <head><title>Bing Search</title></head>
        <body>
            <ol id="b_results">
                <li>
                    <h2><a href="https://example1.com">Test Title 1</a></h2>
                    <p class="b_algoSlug">Test Snippet 1</p>
                </li>
                <li>
                    <h2><a href="https://example2.com">Test Title 2</a></h2>
                    <p class="b_algoSlug">Test Snippet 2</p>
                </li>
            </ol>
        </body>
    </html>
    """
    mock_get.return_value = mock_response

    # Call the function under test
    result = search_toolkit.search_bing(query="test query", max_results=5)

    # Expected output
    expected_output = {
        "results": [
            {
                "result_id": 1,
                "title": "Test Title 1",
                "snippet": "Test Snippet 1",
                "link": "https://example1.com",
            },
            {
                "result_id": 2,
                "title": "Test Title 2",
                "snippet": "Test Snippet 2",
                "link": "https://example2.com",
            },
        ]
    }

    # Assertions
    assert result == expected_output
    mock_get.assert_called_once_with(
        "https://cn.bing.com/search?q=test+query",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        },
        timeout=10,
    )


@patch('requests.get')
@patch('wolframalpha.Client')
@patch('os.environ.get')
def test_query_wolfram_alpha(mock_get_env, mock_client, mock_requests_get):
    mock_get_env.return_value = 'FAKE_APP_ID'

    mock_res = MagicMock()
    mock_res.get.side_effect = lambda key, default: {
        '@inputstring': 'calculate limit of sinx^2/x',
        'pod': [
            {
                '@title': 'Limit',
                'subpod': {'plaintext': 'lim_(x->0) (sin^2(x))/x = 0'},
            },
            {
                '@title': 'Plot',
                'subpod': {'plaintext': None},
            },
        ],
    }[key]

    mock_instance = MagicMock()
    mock_instance.query.return_value = mock_res
    mock_client.return_value = mock_instance

    mock_requests_get.return_value = MagicMock(status_code=200)
    mock_requests_get.return_value.text = """
    <queryresult success="true" error="false">
        <pod title="Limit">
            <subpod>
                <plaintext>lim_(x->0) (sin^2(x))/x = 0</plaintext>
            </subpod>
        </pod>
        <pod title="Plot">
            <subpod>
                <plaintext></plaintext>
            </subpod>
        </pod>
    </queryresult>
    """

    result = SearchToolkit().query_wolfram_alpha(
        "calculate limit of sinx^2/x", True
    )

    expected_output = {
        "query": "calculate limit of sinx^2/x",
        "pod_info": [
            {
                "title": "Limit",
                "description": "lim_(x->0) (sin^2(x))/x = 0",
                "image_url": '',
            },
            {
                "title": "Plot",
                "description": None,
                "image_url": '',
            },
        ],
        "final_answer": None,
        "steps": {},
    }

    assert result == expected_output


def test_parse_wolfram_result():
    sample_wolfram_result = {
        "@inputstring": "What is 2+2?",
        "pod": [
            {
                "@title": "Input",
                "subpod": {
                    "plaintext": "2 + 2",
                    "img": {"@src": "http://example.com/image1.png"},
                },
            },
            {
                "@title": "Result",
                "subpod": {
                    "plaintext": "4",
                    "img": {"@src": "http://example.com/image2.png"},
                },
                "@primary": "true",
            },
        ],
    }
    expected_output = {
        "query": "What is 2+2?",
        "pod_info": [
            {
                "title": "Input",
                "description": "2 + 2",
                "image_url": "http://example.com/image1.png",
            },
            {
                "title": "Result",
                "description": "4",
                "image_url": "http://example.com/image2.png",
            },
        ],
        "final_answer": "4",
    }

    result = SearchToolkit()._parse_wolfram_result(sample_wolfram_result)

    assert (
        result == expected_output
    ), f"Expected {expected_output}, but got {result}"


@patch('requests.get')
def test_get_wolframalpha_step_by_step_solution(mock_get):
    sample_response = """
    <queryresult>
        <pod title="Results">
            <subpod>
                <stepbystepcontenttype>SBSHintStep</stepbystepcontenttype>
                <plaintext>Hint: | Step 1</plaintext>
            </subpod>
            <subpod>
                <stepbystepcontenttype>SBSHintStep</stepbystepcontenttype>
                <plaintext>Hint: | Step 2</plaintext>
            </subpod>
        </pod>
    </queryresult>
    """

    mock_get.return_value = Mock(text=sample_response)

    expected_steps = {"step1": "Step 1", "step2": "Step 2"}

    result = SearchToolkit()._get_wolframalpha_step_by_step_solution(
        "dummy_app_id", "dummy_query"
    )

    assert (
        result == expected_steps
    ), f"Expected {expected_steps}, but got {result}"


class MockSearchResult:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_search_linkup_search_results(search_toolkit):
    with patch('linkup.LinkupClient') as mock_client:
        mock_instance = mock_client.return_value
        mock_result = MockSearchResult(
            title='Test Title', url='http://test.com'
        )
        mock_response = MockSearchResult(results=[mock_result])
        mock_instance.search.return_value = mock_response

        with patch.dict(os.environ, {'LINKUP_API_KEY': 'test_key'}):
            result = search_toolkit.search_linkup(
                query="test query", output_type="searchResults"
            )

        assert result == {
            'results': [{'title': 'Test Title', 'url': 'http://test.com'}]
        }
        mock_instance.search.assert_called_once_with(
            query="test query",
            depth="standard",
            output_type="searchResults",
            structured_output_schema=None,
        )


def test_search_linkup_sourced_answer(search_toolkit):
    with patch('linkup.LinkupClient') as mock_client:
        mock_instance = mock_client.return_value
        mock_source = MockSearchResult(
            title='Source Title', url='http://source.com'
        )
        mock_response = MockSearchResult(
            answer='Test answer', sources=[mock_source]
        )
        mock_instance.search.return_value = mock_response

        with patch.dict(os.environ, {'LINKUP_API_KEY': 'test_key'}):
            result = search_toolkit.search_linkup(
                query="test query", output_type="sourcedAnswer"
            )

        assert result == {
            'answer': 'Test answer',
            'sources': [{'title': 'Source Title', 'url': 'http://source.com'}],
        }


def test_search_linkup_structured_output(search_toolkit):
    with patch('linkup.LinkupClient') as mock_client:
        mock_instance = mock_client.return_value
        mock_response = MockSearchResult(structured_data={'key': 'value'})
        mock_instance.search.return_value = mock_response

        with patch.dict(os.environ, {'LINKUP_API_KEY': 'test_key'}):
            result = search_toolkit.search_linkup(
                query="test query",
                output_type="structured",
                structured_output_schema="test_schema",
            )

        assert result == {'structured_data': {'key': 'value'}}


def test_search_linkup_error(search_toolkit):
    with patch('linkup.LinkupClient') as mock_client:
        mock_instance = mock_client.return_value
        mock_instance.search.side_effect = Exception("Test error")

        with patch.dict(os.environ, {'LINKUP_API_KEY': 'test_key'}):
            result = search_toolkit.search_linkup(query="test query")

        assert result == {"error": "An unexpected error occurred: Test error"}


def test_search_bocha_success(search_toolkit):
    """Test successful Bocha AI search with basic parameters."""
    import json

    mock_response = {
        "code": 200,
        "data": {
            "_type": "SearchResponse",
            "queryContext": {"originalQuery": "test_query"},
            "webPages": {
                "webSearchUrl": "",
                "value": [],
            },
            "images": {},
            "videos": {},
        },
    }
    with patch('requests.post') as mock_post:
        mock_post.return_value.json.return_value = mock_response
        mock_post.return_value.status_code = 200
        mock_post.return_value.text = "OK"
        mock_post.return_value.raise_for_status = lambda: None

        with patch.dict(os.environ, {'BOCHA_API_KEY': 'test_key'}):
            result = search_toolkit.search_bocha(
                query="test query",
            )

    assert result == mock_response["data"]

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert kwargs['headers'] == {
        "Content-Type": "application/json",
        "Authorization": "Bearer test_key",
    }

    assert kwargs['data'] == json.dumps(
        {
            "query": "test query",
            "freshness": "noLimit",
            "summary": False,
            "count": 10,
            "page": 1,
        }
    )


def test_search_bocha_error(search_toolkit):
    """Test error handling in Bocha AI search."""
    with patch('requests.post') as mock_post:
        mock_post.side_effect = requests.exceptions.RequestException(
            "Connection error"
        )

        with patch.dict(os.environ, {'BOCHA_API_KEY': 'test_key'}):
            result = search_toolkit.search_bocha(query="test query")

    assert "error" in result
    assert "Connection error" in result["error"]
