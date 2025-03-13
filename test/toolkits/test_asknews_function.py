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
import sys
import unittest
from unittest.mock import MagicMock, patch

# Create mock for the asknews_sdk module
mock_asknews_sdk = MagicMock()
mock_asknews_sdk.AskNewsSDK = MagicMock()
mock_asknews_sdk.AsyncAskNewsSDK = MagicMock()

sys.modules['asknews_sdk'] = mock_asknews_sdk

# Import the modules that depend on asknews_sdk
# ruff: noqa: E402
from camel.toolkits.ask_news_toolkit import (
    AskNewsToolkit,
    _process_response,
)


class TestAskNewsToolkit(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "ASKNEWS_CLIENT_ID": "fake_client_id",
            "ASKNEWS_CLIENT_SECRET": "fake_client_secret",
        },
    )
    def setUp(self):
        # Setup for tests
        self.mock_sdk = MagicMock()
        self.toolkit = AskNewsToolkit()
        self.toolkit.asknews_client = self.mock_sdk

    def test_get_news_success(self):
        # Mock the API response for a successful get_news call
        mock_response = MagicMock()
        mock_response.as_string = "News in string format"
        self.mock_sdk.news.search_news.return_value = mock_response

        result = self.toolkit.get_news(
            query="test query", return_type="string"
        )

        self.assertEqual(result, "News in string format")
        self.mock_sdk.news.search_news.assert_called_once_with(
            query="test query",
            n_articles=10,
            return_type="string",
            method="kw",
        )

    def test_get_news_failure(self):
        # Test handling of an exception in get_news
        self.mock_sdk.news.search_news.side_effect = Exception("API Error")
        result = self.toolkit.get_news(query="test query")
        self.assertEqual(result, "Got error: API Error")

    def test_search_reddit_success(self):
        # Mock the API response for search_reddit
        mock_response = MagicMock()
        mock_response.as_string = "Reddit threads in string format"
        self.mock_sdk.news.search_reddit.return_value = mock_response

        result = self.toolkit.search_reddit(
            keywords=["test"], n_threads=5, return_type="string"
        )

        self.assertEqual(result, "Reddit threads in string format")
        self.mock_sdk.news.search_reddit.assert_called_once_with(
            keywords=["test"], n_threads=5, method="kw"
        )

    def test_get_stories_success(self):
        # Mock the API response for get_stories
        mock_story = MagicMock()
        mock_story.updates = [
            MagicMock(headline="Update 1 headline", story="Update 1 story"),
            MagicMock(headline="Update 2 headline", story="Update 2 story"),
        ]
        mock_response = MagicMock()
        mock_response.stories = [mock_story]
        self.mock_sdk.stories.search_stories.return_value = mock_response

        result = self.toolkit.get_stories(
            query="test query", categories=["Sports"]
        )

        expected_result = {
            "stories": [
                {
                    "headline": "Update 1 headline",
                    "updates": [
                        {
                            "headline": "Update 1 headline",
                            "story": "Update 1 story",
                        },
                        {
                            "headline": "Update 2 headline",
                            "story": "Update 2 story",
                        },
                    ],
                }
            ]
        }
        self.assertEqual(result, expected_result)
        self.mock_sdk.stories.search_stories.assert_called_once_with(
            query="test query",
            categories=["Sports"],
            reddit=3,
            expand_updates=True,
            max_updates=2,
            max_articles=10,
        )

    def test_get_stories_failure(self):
        # Test handling of an exception in get_stories
        self.mock_sdk.stories.search_stories.side_effect = Exception(
            "API Error"
        )
        result = self.toolkit.get_stories(
            query="test query", categories=["Sports"]
        )
        self.assertEqual(result, "Got error: API Error")

    def test_process_response(self):
        # Test _process_response utility function
        mock_response = MagicMock()
        mock_response.as_string = "response in string"
        mock_response.as_dicts = {"response": "in dict"}

        # Test for string return type
        result = _process_response(mock_response, "string")
        self.assertEqual(result, "response in string")

        # Test for dicts return type
        result = _process_response(mock_response, "dicts")
        self.assertEqual(result, {"response": "in dict"})

        # Test for both return type
        result = _process_response(mock_response, "both")
        self.assertEqual(
            result, ("response in string", {"response": "in dict"})
        )

        # Test for invalid return type
        with self.assertRaises(ValueError):
            _process_response(mock_response, "invalid_type")
