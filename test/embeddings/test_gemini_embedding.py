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

from camel.embeddings import GeminiEmbedding
from camel.types import GeminiEmbeddingTaskType


@patch.dict(os.environ, {"GEMINI_API_KEY": "fake_api_key"})
@patch('google.genai.Client.models', autospec=True)
def test_embed_list(mock_models):
    # Set up the mock models and its return values
    mock_embed_content = MagicMock()
    mock_models.embed_content = mock_embed_content

    # Create two different responses for the two texts
    mock_response = MagicMock()
    mock_embedding1 = MagicMock()
    mock_embedding1.values = [0.1, 0.2, 0.3]
    mock_embedding2 = MagicMock()
    mock_embedding2.values = [0.4, 0.5, 0.6]
    mock_response.embeddings = [mock_embedding1, mock_embedding2]

    # Set up the mock to return different responses for each call
    mock_embed_content.side_effect = [mock_response]

    # Create the embedding instance and test embed_list
    embedding = GeminiEmbedding()
    result = embedding.embed_list(["text1", "text2"])

    # Verify the calls to the mock
    assert mock_embed_content.call_count == 1

    # Check the first call
    args1, kwargs1 = mock_embed_content.call_args_list[0]
    assert kwargs1['model'] == "gemini-embedding-exp-03-07"
    assert kwargs1['contents'] == ["text1", "text2"]
    assert kwargs1['config'] is None

    # Verify the result
    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]


@patch.dict(os.environ, {"GEMINI_API_KEY": "fake_api_key"})
@patch('google.genai.Client.models', autospec=True)
def test_embed_list_with_task_type(mock_models):
    # Set up the mock models and its return values
    mock_embed_content = MagicMock()
    mock_models.embed_content = mock_embed_content

    # Create response for the text
    mock_response = MagicMock()
    mock_embedding = MagicMock()
    mock_embedding.values = [0.1, 0.2, 0.3]
    mock_response.embeddings = [mock_embedding]

    # Set up the mock to return the response
    mock_embed_content.return_value = mock_response

    # Create the embedding instance with task type and test embed_list
    embedding = GeminiEmbedding(
        task_type=GeminiEmbeddingTaskType.SEMANTIC_SIMILARITY
    )
    result = embedding.embed_list(["text1"])

    # Verify the call to the mock includes task_type in config
    mock_embed_content.assert_called_once()
    args, kwargs = mock_embed_content.call_args
    assert kwargs['model'] == "gemini-embedding-exp-03-07"
    assert kwargs['contents'] == ["text1"]
    assert kwargs['config'] is not None

    # Verify the result
    assert result == [[0.1, 0.2, 0.3]]


@patch.dict(os.environ, {"GEMINI_API_KEY": "fake_api_key"})
def test_get_output_dim():
    # Instantiate the GeminiEmbedding with specified dimensions
    embedding = GeminiEmbedding(dimensions=3072)

    # Validate that get_output_dim returns the correct value
    assert embedding.get_output_dim() == 3072

    # Instantiate the GeminiEmbedding without specified dimensions
    embedding = GeminiEmbedding()

    # Validate that get_output_dim returns the correct value
    assert embedding.get_output_dim() == 3072
