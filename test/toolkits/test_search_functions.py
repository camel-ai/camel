# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
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


search_duckduckgo = SearchToolkit().search_duckduckgo


@mock.patch(
    "duckduckgo_search.DDGS.text",
    return_value=[
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
    ],
)
def test_search_duckduckgo_text(mock_text):
    result = search_duckduckgo(
        query="test query", source="text", max_results=2
    )
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
    mock_text.assert_called_once_with(keywords="test query", max_results=2)


@mock.patch(
    "duckduckgo_search.DDGS.images",
    return_value=[
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
    ],
)
def test_search_duckduckgo_images(mock_images):
    result = search_duckduckgo(
        query="test query", source="images", max_results=2
    )

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

    mock_images.assert_called_once_with(keywords="test query", max_results=2)


def test_web_search(search_toolkit):
    query = "What big things are happening in 2023?"
    answer = search_toolkit.search_google(query)
    assert answer is not None
    answer = search_toolkit.search_duckduckgo(query)
    assert answer is not None


@patch('wolframalpha.Client')
@patch('os.environ.get')
def test_query_wolfram_alpha(mock_get, mock_client, search_toolkit):
    mock_get.return_value = 'FAKE_APP_ID'

    # Create mock subpods objects
    mock_subpods1 = [
        MagicMock(plaintext="lim_(x->0) (sin^2(x))/x = 0"),
        MagicMock(plaintext="lim_(x->-∞) (sin^2(x))/x = 0"),
        MagicMock(plaintext="lim_(x->∞) (sin^2(x))/x = 0"),
    ]
    mock_subpods2 = [MagicMock(plaintext=None)]

    # Create mock pods objects
    mock_pod1 = MagicMock()
    mock_pod1.subpods = mock_subpods1
    mock_pod1.__getitem__.side_effect = lambda key: {'@title': 'Limit'}[key]

    mock_pod2 = MagicMock()
    mock_pod2.subpods = mock_subpods2
    mock_pod2.__getitem__.side_effect = lambda key: {'@title': 'Plot'}[key]

    # Create mock results object
    mock_results = MagicMock(text="lim_(x->0) (sin^2(x))/x = 0")

    # Create mock res object
    mock_res = MagicMock()
    mock_res.pods.__iter__.return_value = iter([mock_pod1, mock_pod2])
    mock_res.results.__iter__.return_value = iter([mock_results])

    # Configure the text attribute of the object returned by the next method
    mock_res.pods.__next__.return_value.text = "lim_(x->0) (sin^2(x))/x = 0"
    mock_res.results.__next__.return_value.text = "lim_(x->0) (sin^2(x))/x = 0"

    # Configure the mock client instance to return the mock response
    mock_instance = MagicMock()
    mock_instance.query.return_value = mock_res
    mock_client.return_value = mock_instance

    result = search_toolkit.query_wolfram_alpha(
        "calculate limit of sinx^2/x", True
    )
    expected_output = (
        "Assumption:\n"
        "lim_(x->0) (sin^2(x))/x = 0\n\n"
        "Answer:\n"
        "lim_(x->0) (sin^2(x))/x = 0\n\n"
        "Limit:\n"
        "lim_(x->0) (sin^2(x))/x = 0\n"
        "lim_(x->-∞) (sin^2(x))/x = 0\n"
        "lim_(x->∞) (sin^2(x))/x = 0\n\n"
        "Plot:\nNone"
    )
    assert result == expected_output
