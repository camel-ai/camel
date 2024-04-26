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
from unittest.mock import MagicMock, Mock, patch

import pytest

from camel.embeddings import OpenAIEmbedding
from camel.retrievers import VectorRetriever

# Mock classes for dependencies
MockBaseEmbedding = Mock()
MockBaseVectorStorage = Mock()
MockUnstructuredIO = Mock()


@pytest.fixture
def mock_embedding_model():
    return MockBaseEmbedding()


@pytest.fixture
def mock_vector_storage():
    return MockBaseVectorStorage()


@pytest.fixture
def vector_retriever(mock_embedding_model):
    return VectorRetriever(embedding_model=mock_embedding_model)


# Test initialization with a custom embedding model
def test_initialization_with_custom_embedding(vector_retriever, mock_embedding_model):
    assert vector_retriever.embedding_model == mock_embedding_model


# Test initialization with default embedding model
def test_initialization_with_default_embedding():
    retriever = VectorRetriever()
    assert isinstance(retriever.embedding_model, OpenAIEmbedding)


# Test process method
@patch('camel.retrievers.vector_retriever.UnstructuredIO')
def test_process(mock_unstructured_modules, vector_retriever, mock_vector_storage):
    # Create a mock chunk with metadata
    mock_chunk = MagicMock()
    mock_chunk.metadata.to_dict.return_value = {'mock_key': 'mock_value'}

    # Setup mock behavior
    mock_unstructured_instance = mock_unstructured_modules.return_value
    mock_unstructured_instance.parse_file_or_url.return_value = ["mock_element"]
    mock_unstructured_instance.chunk_elements.return_value = [mock_chunk]

    vector_retriever.embedding_model.embed_list.return_value = [[0.1, 0.2, 0.3]]

    vector_retriever.process("mock_path", mock_vector_storage)

    # Assert that methods are called as expected
    mock_unstructured_instance.parse_file_or_url.assert_called_once_with("mock_path")
    mock_unstructured_instance.chunk_elements.assert_called_once()
    mock_vector_storage.add.assert_called_once()


# Test query
def test_query(vector_retriever, mock_vector_storage):
    # Setup mock behavior for vector storage query
    mock_vector_storage.query.return_value = [
        Mock(similarity=0.8, record=Mock(payload={"text": "mock_result"}))
    ]

    result = vector_retriever.query("mock_query", mock_vector_storage)

    # Assert that the result is as expected
    assert any(d.get('text') == 'mock_result' for d in result)
