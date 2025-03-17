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
from unittest.mock import MagicMock, Mock, patch

import pytest

from camel.embeddings import OpenAIEmbedding
from camel.loaders import Chunk
from camel.retrievers import VectorRetriever

# Mock classes for dependencies
MockBaseEmbedding = Mock()
MockBaseVectorStorage = Mock()
MockUnstructuredIO = Mock()


@pytest.fixture
def mock_embedding_model():
    mock_instance = MockBaseEmbedding()
    mock_instance.embed.return_value = [0.0, 0.0]
    mock_instance.embed_list.return_value = [[0.0, 0.0]]
    return mock_instance


@pytest.fixture
def mock_vector_storage():
    return MockBaseVectorStorage()


@pytest.fixture
def vector_retriever(mock_embedding_model, mock_vector_storage):
    return VectorRetriever(
        embedding_model=mock_embedding_model, storage=mock_vector_storage
    )


@pytest.fixture
def mock_unstructured_modules():
    with patch('camel.retrievers.vector_retriever.UnstructuredIO') as mock:
        yield mock


# Test initialization with a custom embedding model
def test_initialization_with_custom_embedding(
    vector_retriever, mock_embedding_model
):
    assert vector_retriever.embedding_model == mock_embedding_model


# Test initialization with default embedding model
def test_initialization_with_default_embedding():
    retriever = VectorRetriever()
    assert isinstance(retriever.embedding_model, OpenAIEmbedding)


def test_load_chunks(vector_retriever):
    mock_chunk1 = Chunk(
        text="mock text 1", metadata={"mock_key": "mock_value"}
    )
    mock_chunk2 = Chunk(
        text="mock text 2", metadata={"mock_key": "mock_value"}
    )

    vector_retriever.load_chunks([mock_chunk1, mock_chunk2], 'dummy_path')

    # Assert that the embedding model is called as expected
    vector_retriever.embedding_model.embed_list.assert_called_once_with(
        objs=["mock text 1", "mock text 2"]
    )


# Test process method
@patch('camel.loaders.UnstructuredIO')
def test_process(mock_unstructured_io):
    mock_instance = mock_unstructured_io.return_value

    # Create a mock chunk with metadata
    mock_chunk = MagicMock()
    mock_chunk.metadata.to_dict.return_value = {'mock_key': 'mock_value'}

    # Setup mock behavior
    mock_instance.parse_file_or_url.return_value = ["mock_element"]
    mock_instance.chunk_elements.return_value = [mock_chunk]

    vector_retriever = VectorRetriever()

    vector_retriever.process(content="https://www.camel-ai.org/")

    # Assert that methods are called as expected
    mock_instance.parse_file_or_url.assert_called_once_with(
        input_path="https://www.camel-ai.org/", metadata_filename=None
    )
    mock_instance.chunk_elements.assert_called_once()


# Test query
def test_query(vector_retriever):
    query = "test query"
    top_k = 1
    # Setup mock behavior for vector storage query
    vector_retriever.storage.load = Mock()
    vector_retriever.storage.query.return_value = [
        Mock(similarity=0.8, record=Mock(payload={"text1": "mock_result1"}))
    ]

    results = vector_retriever.query(query, top_k=top_k)
    assert len(results) == 1
    assert results[0]['similarity score'] == '0.8'


# Test query with no results found
def test_query_no_results(vector_retriever):
    query = "test query"
    top_k = 1
    # Setup mock behavior for vector storage query
    vector_retriever.storage.load = Mock()
    vector_retriever.storage.query.return_value = []

    with pytest.raises(
        ValueError,
        match="Query result is empty, please check if the "
        "vector storage is empty.",
    ):
        vector_retriever.query(query, top_k=top_k)


# Test query with payload None
def test_query_payload_none(vector_retriever):
    query = "test query"
    top_k = 1
    # Setup mock behavior for vector storage query
    vector_retriever.storage.load = Mock()
    vector_retriever.storage.query.return_value = [
        Mock(similarity=0.8, record=Mock(payload=None))
    ]

    with pytest.raises(
        ValueError,
        match=(
            "Payload of vector storage is None, "
            "please check the collection."
        ),
    ):
        vector_retriever.query(query, top_k=top_k)
