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
from unittest.mock import MagicMock, patch

import pytest

from camel.embeddings import AzureEmbedding
from camel.types import EmbeddingModelType


class MockEmbeddingData:
    def __init__(self, embedding: List[float]):
        self.embedding = embedding


class MockResponse:
    def __init__(self, data: List[MockEmbeddingData]):
        self.data = data


@pytest.fixture
def mock_env_vars(monkeypatch):
    r"""Set up environment variables to prevent API calls during testing."""
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test_api_key")
    monkeypatch.setenv(
        "AZURE_OPENAI_BASE_URL", "https://test.openai.azure.com"
    )
    monkeypatch.setenv("AZURE_API_VERSION", "2023-05-15")


@patch('camel.embeddings.azure_embedding.AzureOpenAI')
def test_azure_embedding(mock_azure_openai, mock_env_vars):
    # Create mock client and mock embeddings object
    mock_client = MagicMock()
    mock_embeddings = MagicMock()
    mock_client.embeddings = mock_embeddings
    mock_azure_openai.return_value = mock_client

    # Default model test with mocked response (1536 dimensions)
    default_dim = EmbeddingModelType.TEXT_EMBEDDING_3_SMALL.output_dim
    mock_embedding = [0.1] * default_dim
    mock_response = MockResponse([MockEmbeddingData(mock_embedding)])
    mock_embeddings.create.return_value = mock_response

    # Test with default dimensions
    embedding_model = AzureEmbedding()
    text = "test 1."
    vector = embedding_model.embed(text)

    # Verify mock was called correctly
    mock_embeddings.create.assert_called_once()
    assert len(vector) == embedding_model.get_output_dim()

    # Reset mock for second test
    mock_embeddings.create.reset_mock()

    # Test with custom dimensions
    custom_dim = 256
    mock_embedding_custom = [0.1] * custom_dim
    mock_response_custom = MockResponse(
        [MockEmbeddingData(mock_embedding_custom)]
    )
    mock_embeddings.create.return_value = mock_response_custom

    embedding_model = AzureEmbedding(dimensions=custom_dim)
    text = "test 2"
    vector = embedding_model.embed(text)

    # Verify dimensions were passed correctly
    mock_embeddings.create.assert_called_once()
    assert len(vector) == embedding_model.get_output_dim() == custom_dim
