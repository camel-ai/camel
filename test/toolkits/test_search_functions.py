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
from unittest.mock import MagicMock, patch

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


@patch('requests.get')
def test_search_google_web_success(mock_get, search_toolkit):
    """Test successful Google web search."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "title": "Test Title 1",
                "snippet": "Test snippet 1",
                "link": "https://example1.com",
                "pagemap": {
                    "metatags": [{"og:description": "Test long description 1"}]
                },
            },
            {
                "title": "Test Title 2",
                "snippet": "Test snippet 2",
                "link": "https://example2.com",
                "pagemap": {
                    "metatags": [{"og:description": "Test long description 2"}]
                },
            },
        ]
    }
    mock_get.return_value = mock_response

    with patch.dict(
        os.environ,
        {
            'GOOGLE_API_KEY': 'fake_api_key',
            'SEARCH_ENGINE_ID': 'fake_search_engine_id',
        },
    ):
        result = search_toolkit.search_google(query="test query")

    assert len(result) == 2
    assert result[0] == {
        "result_id": 1,
        "title": "Test Title 1",
        "description": "Test snippet 1",
        "long_description": "Test long description 1",
        "url": "https://example1.com",
    }
    assert result[1] == {
        "result_id": 2,
        "title": "Test Title 2",
        "description": "Test snippet 2",
        "long_description": "Test long description 2",
        "url": "https://example2.com",
    }

    # Verify the request was made with correct parameters
    mock_get.assert_called_once()
    call_args = mock_get.call_args[0][0]
    assert "q=test+query" in call_args or "q=test%20query" in call_args
    assert "num=10" in call_args


@patch('requests.get')
def test_search_google_image_success(mock_get, search_toolkit):
    """Test successful Google image search."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "title": "Image Title 1",
                "link": "https://example.com/image1.jpg",
                "displayLink": "example.com",
                "image": {
                    "contextLink": "https://example.com/page1.html",
                    "width": 800,
                    "height": 600,
                },
            }
        ]
    }
    mock_get.return_value = mock_response

    with patch.dict(
        os.environ,
        {
            'GOOGLE_API_KEY': 'fake_api_key',
            'SEARCH_ENGINE_ID': 'fake_search_engine_id',
        },
    ):
        result = search_toolkit.search_google(
            query="test image", search_type="image"
        )

    assert len(result) == 1
    assert result[0] == {
        "result_id": 1,
        "title": "Image Title 1",
        "image_url": "https://example.com/image1.jpg",
        "display_link": "example.com",
        "context_url": "https://example.com/page1.html",
        "width": 800,
        "height": 600,
    }

    # Verify searchType parameter was included
    call_args = mock_get.call_args[0][0]
    assert "searchType=image" in call_args


@patch('requests.get')
def test_search_google_no_results(mock_get, search_toolkit):
    """Test Google search with no results."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "searchInformation": {"totalResults": "0"}
    }
    mock_get.return_value = mock_response

    with patch.dict(
        os.environ,
        {
            'GOOGLE_API_KEY': 'fake_api_key',
            'SEARCH_ENGINE_ID': 'fake_search_engine_id',
        },
    ):
        result = search_toolkit.search_google(query="very specific query")

    # When no results are found, the method now returns an empty list
    assert len(result) == 0


def test_search_google_parameter_validation(search_toolkit):
    """Test parameter validation for Google search."""
    # The new API doesn't perform parameter validation
    # Skip this test as it's no longer applicable
    pytest.skip("Parameter validation is not implemented in the new API")


@patch('requests.get')
def test_search_google_error_handling(mock_get, search_toolkit):
    """Test error handling in Google search."""
    with patch.dict(
        os.environ,
        {
            'GOOGLE_API_KEY': 'fake_api_key',
            'SEARCH_ENGINE_ID': 'fake_search_engine_id',
        },
    ):
        # Test timeout error
        mock_get.side_effect = requests.exceptions.Timeout()
        result = search_toolkit.search_google(query="test")
        assert len(result) == 1
        assert "error" in result[0]
        assert "google search failed" in result[0]["error"]

        # Test general exception
        mock_get.side_effect = Exception("Some error")
        result = search_toolkit.search_google(query="test")
        assert len(result) == 1
        assert "error" in result[0]
        assert "google search failed" in result[0]["error"]

        # Test API error response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": {
                "code": 400,
                "message": "API key not valid. Please pass a valid API key.",
            }
        }
        mock_get.side_effect = None
        mock_get.return_value = mock_response
        result = search_toolkit.search_google(query="test")
        assert len(result) == 1
        assert "error" in result[0]
        assert "Google search failed" in result[0]["error"]
        assert "API key not valid" in result[0]["error"]


@patch('requests.get')
def test_search_google_with_exclude_domains(mock_get):
    """Test Google search with excluded domains."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": []}
    mock_get.return_value = mock_response

    # Create toolkit with exclude_domains
    toolkit_with_exclusions = SearchToolkit(
        exclude_domains=["example.com", "test.com"]
    )

    with patch.dict(
        os.environ,
        {
            'GOOGLE_API_KEY': 'fake_api_key',
            'SEARCH_ENGINE_ID': 'fake_search_engine_id',
        },
    ):
        toolkit_with_exclusions.search_google(query="test query")

    # Verify the query includes exclusion terms
    call_args = mock_get.call_args[0][0]
    # Check that the exclusion terms are properly encoded
    assert "-site%3Aexample.com" in call_args
    assert "-site%3Atest.com" in call_args


@patch('requests.get')
def test_search_google_special_characters(mock_get, search_toolkit):
    """Test Google search with special characters in query."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": []}
    mock_get.return_value = mock_response

    with patch.dict(
        os.environ,
        {
            'GOOGLE_API_KEY': 'fake_api_key',
            'SEARCH_ENGINE_ID': 'fake_search_engine_id',
        },
    ):
        search_toolkit.search_google(query="C++ & Python programming")

    # Verify special characters are properly encoded
    call_args = mock_get.call_args[0][0]
    # Check for proper URL encoding of special characters
    assert "C%2B%2B" in call_args  # C++
    assert "%26" in call_args  # &
    assert "Python" in call_args
    assert "programming" in call_args


@patch('requests.get')
def test_search_google_without_metatags(mock_get, search_toolkit):
    """Test Google search handling results without metatags."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "title": "Test Title Without Metatags",
                "snippet": "Test snippet without metatags",
                "link": "https://example.com/no-metatags",
                # No pagemap/metatags
            },
            {
                "title": "Test Title With Twitter Description",
                "snippet": "Test snippet with twitter description",
                "link": "https://example.com/twitter",
                "pagemap": {
                    "metatags": [
                        {"twitter:description": "Twitter description only"}
                    ]
                },
            },
        ]
    }
    mock_get.return_value = mock_response

    with patch.dict(
        os.environ,
        {
            'GOOGLE_API_KEY': 'fake_api_key',
            'SEARCH_ENGINE_ID': 'fake_search_engine_id',
        },
    ):
        result = search_toolkit.search_google(query="test query")

    # The new implementation skips results without pagemap/metatags
    assert len(result) == 1
    # Only the second result (with metatags) is returned
    # Since it doesn't have og:description, it gets "N/A"
    assert result[0]["title"] == "Test Title With Twitter Description"
    assert result[0]["long_description"] == "N/A"


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
        result = search_duckduckgo(query="test query", source="text")

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
            keywords="test query", max_results=10
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
        result = search_duckduckgo(query="test query", source="images")

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
            keywords="test query", max_results=10
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
    result = search_toolkit.search_baidu(query="test query")

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
        params={"wd": "test query", "rn": "10"},
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
    result = search_toolkit.search_bing(query="test query")

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


@patch('requests.get')
def test_search_alibaba_tongxiao(mock_get, search_toolkit):
    # Mock the response from Alibaba Tongxiao search
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "requestId": "test-request-id",
        "pageItems": [
            {
                "title": "Test Title 1",
                "snippet": "Test Snippet 1",
                "link": "https://example1.com",
                "hostname": "example1.com",
                "markdownText": "# Test Markdown 1",
            }
        ],
    }
    mock_get.return_value = mock_response

    # Mock environment variables and call the function
    with patch.dict(os.environ, {'TONGXIAO_API_KEY': 'fake_api_key'}):
        result = search_toolkit.search_alibaba_tongxiao(
            query="test query", return_markdown_text=True
        )

        # Verify the request was made correctly
        mock_get.assert_called_once_with(
            "https://cloud-iqs.aliyuncs.com/search/genericSearch",
            headers={"X-API-Key": "fake_api_key"},
            params={
                "query": "test query",
                "timeRange": "NoLimit",
                "page": 10,
                "returnMainText": "false",
                "returnMarkdownText": "true",
                "enableRerank": "true",
            },
            timeout=10,
        )

        # Check if the result is as expected
        assert result == {
            "request_id": "test-request-id",
            "results": [
                {
                    "result_id": 1,
                    "title": "Test Title 1",
                    "snippet": "Test Snippet 1",
                    "url": "https://example1.com",
                    "hostname": "example1.com",
                    "markdown_text": "# Test Markdown 1",
                }
            ],
        }


@patch('http.client.HTTPSConnection')
def test_search_metaso_success(mock_https_connection, search_toolkit):
    # Mock the connection and response
    mock_conn = MagicMock()
    mock_https_connection.return_value = mock_conn

    mock_response = MagicMock()
    mock_response.read.return_value = (
        b'{"results": [{"title": "Test Title", '
        b'"url": "https://example.com", "snippet": "Test snippet"}], '
        b'"total": 1}'
    )
    mock_conn.getresponse.return_value = mock_response

    # Mock environment variable
    with patch.dict(os.environ, {'METASO_API_KEY': 'test_api_key'}):
        result = search_toolkit.search_metaso(query="test query")

    # Verify the result
    expected_result = {
        "results": [
            {
                "title": "Test Title",
                "url": "https://example.com",
                "snippet": "Test snippet",
            }
        ],
        "total": 1,
    }
    assert result == expected_result

    # Verify the API call
    mock_https_connection.assert_called_once_with("metaso.cn")
    mock_conn.request.assert_called_once()

    # Verify request parameters
    call_args = mock_conn.request.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == "/api/v1/search"

    # Verify headers
    headers = call_args[0][3]
    assert headers['Authorization'] == 'Bearer test_api_key'
    assert headers['Accept'] == 'application/json'
    assert headers['Content-Type'] == 'application/json'


@patch('http.client.HTTPSConnection')
def test_search_metaso_with_parameters(mock_https_connection, search_toolkit):
    # Mock the connection and response
    mock_conn = MagicMock()
    mock_https_connection.return_value = mock_conn

    mock_response = MagicMock()
    mock_response.read.return_value = b'{"results": [], "total": 0}'
    mock_conn.getresponse.return_value = mock_response

    with patch.dict(os.environ, {'METASO_API_KEY': 'test_api_key'}):
        search_toolkit.search_metaso(
            query="test query",
            page=2,
            include_summary=True,
            include_raw_content=True,
            concise_snippet=True,
            scope="document",
        )

    # Verify the payload contains correct parameters
    call_args = mock_conn.request.call_args
    payload = call_args[0][2]
    import json

    payload_data = json.loads(payload)

    assert payload_data["q"] == "test query"
    assert payload_data["page"] == "2"
    assert payload_data["includeSummary"] is True
    assert payload_data["includeRawContent"] is True
    assert payload_data["conciseSnippet"] is True
    assert payload_data["scope"] == "document"


@patch('http.client.HTTPSConnection')
def test_search_metaso_connection_error(mock_https_connection, search_toolkit):
    # Mock connection error
    mock_conn = MagicMock()
    mock_https_connection.return_value = mock_conn
    mock_conn.request.side_effect = Exception("Connection failed")

    with patch.dict(os.environ, {'METASO_API_KEY': 'test_api_key'}):
        result = search_toolkit.search_metaso(query="test query")

    assert "error" in result
    assert "Metaso search failed: Connection failed" in result["error"]

    # Verify connection was attempted
    mock_https_connection.assert_called_once_with("metaso.cn")
    mock_conn.request.assert_called_once()


@patch('http.client.HTTPSConnection')
def test_search_metaso_invalid_json(mock_https_connection, search_toolkit):
    # Mock invalid JSON response
    mock_conn = MagicMock()
    mock_https_connection.return_value = mock_conn

    mock_response = MagicMock()
    mock_response.read.return_value = b'invalid json response'
    mock_conn.getresponse.return_value = mock_response

    with patch.dict(os.environ, {'METASO_API_KEY': 'test_api_key'}):
        result = search_toolkit.search_metaso(query="test query")

    assert "error" in result
    assert "Metaso returned content could not be parsed" in result["error"]

    # Verify connection was attempted
    mock_https_connection.assert_called_once_with("metaso.cn")
    mock_conn.request.assert_called_once()
