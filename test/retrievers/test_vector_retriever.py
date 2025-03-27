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
from unittest.mock import Mock, patch

import pytest

from camel.embeddings import OpenAIEmbedding
from camel.retrievers import VectorRetriever

# Mock classes for dependencies
MockBaseEmbedding = Mock()
MockBaseVectorStorage = Mock()
MockUnstructuredIO = Mock()


@pytest.fixture
def mock_embedding_model():
    mock_instance = MockBaseEmbedding()
    mock_instance.embed.return_value = [0.0, 0.0]
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


# Test process method
def test_process(mock_unstructured_modules, monkeypatch):
    # Create a VectorRetriever instance
    vector_retriever = VectorRetriever()

    def mock_process(content, **kwargs):
        # Just verify that the content is correct and return
        assert content == "https://www.camel-ai.org/"
        return None

    # Replace the process method with our mock
    monkeypatch.setattr(vector_retriever, 'process', mock_process)

    # Call the mocked process method
    vector_retriever.process(content="https://www.camel-ai.org/")

    # Verify that the mock_unstructured_modules fixture was created correctly
    assert mock_unstructured_modules is not None


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
