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
import requests
from PIL import Image

from camel.embeddings import JinaEmbedding
from camel.types import EmbeddingModelType


@patch.dict(os.environ, {"JINA_API_KEY": "fake_api_key"})
@patch('requests.post')
def test_text_embed_list(mock_post):
    # Mock the API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [{"embedding": [0.1, 0.2, 0.3]}]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    # Initialize embedding instance
    embedding = JinaEmbedding()

    # Test text embedding
    result = embedding.embed_list(["test text"])

    # Verify the API was called correctly
    mock_post.assert_called_once()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == [0.1, 0.2, 0.3]


@patch.dict(os.environ, {"JINA_API_KEY": "fake_api_key"})
@patch('requests.post')
def test_image_embed_list(mock_post):
    # Mock the API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [{"embedding": [0.1, 0.2, 0.3]}]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    # Create a dummy image
    img = Image.new('RGB', (60, 30), color='red')

    # Initialize embedding instance with CLIP model
    embedding = JinaEmbedding(model_type=EmbeddingModelType.JINA_CLIP_V2)

    # Test image embedding
    result = embedding.embed_list([img])

    # Verify the API was called correctly
    mock_post.assert_called_once()
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0] == [0.1, 0.2, 0.3]


@patch.dict(os.environ, {"JINA_API_KEY": "fake_api_key"})
def test_invalid_model_type():
    # Test initialization with invalid model type
    with pytest.raises(ValueError, match="is not a Jina model"):
        JinaEmbedding(model_type=EmbeddingModelType.TEXT_EMBEDDING_3_SMALL)


@patch.dict(os.environ, {"JINA_API_KEY": "fake_api_key"})
@patch('requests.post')
def test_embed_list_with_options(mock_post):
    # Mock the API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [{"embedding": [0.1, 0.2, 0.3]}]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    # Initialize embedding instance with options
    embedding = JinaEmbedding(
        dimensions=3,
        task="text-matching",
        late_chunking=True,
        normalized=True,
    )

    # Test embedding with options
    result = embedding.embed_list(["test text"])

    # Verify the API was called with correct parameters
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args[1]
    assert len(result[0]) == 3
    assert "json" in call_kwargs
    request_data = call_kwargs["json"]
    assert request_data["task"] == "text-matching"
    assert request_data["late_chunking"] is True
    assert request_data["normalized"] is True


@patch.dict(os.environ, {"JINA_API_KEY": "fake_api_key"})
def test_get_output_dim():
    # Test with default model
    embedding = JinaEmbedding()
    assert embedding.get_output_dim() == embedding.output_dim

    # Test with custom dimensions
    custom_dim = 512
    embedding_custom = JinaEmbedding(dimensions=custom_dim)
    assert embedding_custom.get_output_dim() == custom_dim


@patch.dict(os.environ, {"JINA_API_KEY": "fake_api_key"})
@patch('requests.post')
def test_api_error_handling(mock_post):
    # Mock a failed API response
    mock_post.side_effect = requests.exceptions.RequestException("API Error")

    # Initialize embedding instance
    embedding = JinaEmbedding()

    # Test error handling
    with pytest.raises(
        RuntimeError, match="Failed to get embeddings from Jina AI"
    ):
        embedding.embed_list(["test text"])
