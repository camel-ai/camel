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
import unittest
from unittest.mock import MagicMock, patch

from camel.toolkits.dappier_toolkit import DappierToolkit


class TestDappierToolkit(unittest.TestCase):
    @patch.dict(
        os.environ,
        {"DAPPIER_API_KEY": "fake_api_key"},
    )
    @patch("dappier.Dappier")
    def setUp(self, MockDappierSDK):
        # Setup for tests
        self.mock_sdk = MockDappierSDK.return_value
        self.toolkit = DappierToolkit()

    def test_search_real_time_data_success(self):
        # Mock the API response for a successful search_real_time_data call
        mock_response = MagicMock()
        mock_response.message = "latest tech news"
        self.mock_sdk.search_real_time_data.return_value = mock_response

        result = self.toolkit.search_real_time_data(query="test query")

        self.assertEqual(result, "latest tech news")
        self.mock_sdk.search_real_time_data.assert_called_once_with(
            query="test query", ai_model_id="am_01j06ytn18ejftedz6dyhz2b15"
        )

    def test_search_real_time_data_failure(self):
        # Test handling of an exception in search_real_time_data
        self.mock_sdk.search_real_time_data.side_effect = Exception("Error")
        result = self.toolkit.search_real_time_data(query="test query")
        self.assertEqual(result, "An unexpected error occurred: Error")

    def test_get_ai_recommendations_success(self):
        # Mock the API response for a successful get_ai_recommendations call
        mock_result = MagicMock()
        mock_result.return_value = [
            MagicMock(
                author="John Doe",
                image_url="https://example.com/image1.jpg",
                pubdate="Mon, 01 Jan 2025 10:00:00 +0000",
                source_url="https://example1.com/article1",
                summary="Summary of article 1.",
                title="Article Title 1",
            ),
            MagicMock(
                author="Jane Smith",
                image_url="https://example.com/image2.jpg",
                pubdate="Tue, 02 Jan 2025 12:00:00 +0000",
                source_url="https://example2.com/article2",
                summary="Summary of article 2.",
                title="Article Title 2",
            ),
            MagicMock(
                author="Alice Johnson",
                image_url="https://example.com/image3.jpg",
                pubdate="Wed, 03 Jan 2025 14:00:00 +0000",
                source_url="https://example3.com/article3",
                summary="Summary of article 3.",
                title="Article Title 3",
            ),
        ]
        mock_response = MagicMock()
        mock_response.status = "success"
        mock_response.response.query = "test query"
        mock_response.response.results = mock_result()

        self.mock_sdk.get_ai_recommendations.return_value = mock_response

        result = self.toolkit.get_ai_recommendations(
            query="test query", similarity_top_k=3
        )

        expected_result = [
            {
                "author": "John Doe",
                "image_url": "https://example.com/image1.jpg",
                "pubdate": "Mon, 01 Jan 2025 10:00:00 +0000",
                "source_url": "https://example1.com/article1",
                "summary": "Summary of article 1.",
                "title": "Article Title 1",
            },
            {
                "author": "Jane Smith",
                "image_url": "https://example.com/image2.jpg",
                "pubdate": "Tue, 02 Jan 2025 12:00:00 +0000",
                "source_url": "https://example2.com/article2",
                "summary": "Summary of article 2.",
                "title": "Article Title 2",
            },
            {
                "author": "Alice Johnson",
                "image_url": "https://example.com/image3.jpg",
                "pubdate": "Wed, 03 Jan 2025 14:00:00 +0000",
                "source_url": "https://example3.com/article3",
                "summary": "Summary of article 3.",
                "title": "Article Title 3",
            },
        ]

        self.assertEqual(result, expected_result)
        self.mock_sdk.get_ai_recommendations.assert_called_once_with(
            query="test query",
            data_model_id="dm_01j0pb465keqmatq9k83dthx34",
            similarity_top_k=3,
            ref=None,
            num_articles_ref=0,
            search_algorithm="most_recent",
        )

    def test_get_ai_recommendations_failure(self):
        # Test handling of an exception in get_ai_recommendations
        self.mock_sdk.get_ai_recommendations.side_effect = Exception(
            "API Error"
        )
        result = self.toolkit.get_ai_recommendations(query="test query")
        self.assertEqual(
            result, {"error": "An unexpected error occurred: API Error"}
        )

    def test_get_ai_recommendations_failure_when_status_failure(self):
        # Test handling of an exception in get_ai_recommendations
        mock_response = MagicMock()
        mock_response.status = "failure"
        mock_response.response.query = "test query"
        mock_response.response.results = None
        result = self.toolkit.get_ai_recommendations(query="test query")
        self.assertEqual(result, {"error": "An unknown error occurred."})
