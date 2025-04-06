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

import unittest
from unittest.mock import MagicMock, patch

from camel.embeddings import OpenAICompatibleEmbedding


class TestOpenAICompatibleEmbedding(unittest.TestCase):
    @patch("openai.OpenAI")
    @patch.dict(
        "os.environ",
        {
            "OPENAI_COMPATIBILITY_API_KEY": "test_api_key",
            "OPENAI_COMPATIBILITY_API_BASE_URL": "http://test-url.com",
        },
    )
    def test_embed_list(self, MockOpenAI):
        # Mock the OpenAI client and its response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_data = MagicMock()
        mock_data.embedding = [0.1, 0.2, 0.3]
        mock_response.data = [mock_data]
        mock_client.embeddings.create.return_value = mock_response

        # Initialize the OpenAICompatibleEmbedding object
        embedding = OpenAICompatibleEmbedding(
            "text-embedding-model", "test_api_key", "http://test-url.com"
        )
        embedding._client = mock_client

        # Call embed_list method
        input_texts = ["Hello world", "Goodbye world"]
        result = embedding.embed_list(input_texts)

        # Check if the OpenAI client was called with the correct parameters
        mock_client.embeddings.create.assert_called_once_with(
            input=input_texts, model="text-embedding-model"
        )

        # Check if the result is as expected
        self.assertEqual(result, [[0.1, 0.2, 0.3]])

    @patch("openai.OpenAI")
    @patch.dict(
        "os.environ",
        {
            "OPENAI_COMPATIBILITY_API_KEY": "test_api_key",
            "OPENAI_COMPATIBILITY_API_BASE_URL": "http://test-url.com",
        },
    )
    def test_get_output_dim(self, MockOpenAI):
        # Mock the OpenAI client and its response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_data = MagicMock()
        mock_data.embedding = [0.1, 0.2, 0.3]
        mock_response.data = [mock_data]
        mock_client.embeddings.create.return_value = mock_response

        # Initialize the OpenAICompatibleEmbedding object
        embedding = OpenAICompatibleEmbedding(
            "text-embedding-model", "test_api_key", "http://test-url.com"
        )
        embedding._client = mock_client

        # Call embed_list to generate output_dim
        embedding.embed_list(["Hello world"])

        # Now test get_output_dim
        self.assertEqual(embedding.get_output_dim(), 3)

    def test_get_output_dim_without_embeddings(self):
        # Test if ValueError is raised when get_output_dim is called before
        # embed_list and embed_list fails to set output_dim
        embedding = OpenAICompatibleEmbedding(
            "text-embedding-model", "test_api_key", "http://test-url.com"
        )

        # Mock the embed_list method to simulate a failed embedding attempt
        with patch.object(embedding, 'embed_list') as mock_embed_list:
            # Configure the mock to not change output_dim (simulating failure)
            mock_embed_list.return_value = []

            with self.assertRaises(ValueError) as context:
                embedding.get_output_dim()

            # Verify that embed_list was called
            mock_embed_list.assert_called_once_with(["test"])

            # Check the error message
            self.assertEqual(
                str(context.exception),
                "Failed to determine embedding dimension",
            )
