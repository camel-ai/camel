# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
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
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
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
