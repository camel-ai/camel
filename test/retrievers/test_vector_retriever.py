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
    r"""
    Test mock embedding model.
    """
    mock_instance = MockBaseEmbedding()
    mock_instance.embed.return_value = [0.0, 0.0]
    return mock_instance


@pytest.fixture
def mock_vector_storage():
    r"""
    Test mock vector storage.
    """ 
    return MockBaseVectorStorage()


@pytest.fixture
def vector_retriever(mock_embedding_model, mock_vector_storage):
    r"""
    Test vector retriever.
    """
    return VectorRetriever(
        embedding_model=mock_embedding_model, storage=mock_vector_storage
    )


@pytest.fixture
def mock_unstructured_modules():
    r"""
    Test mock unstructured modules.
    """
    with patch(
        'camel.retrievers.vector_retriever.UnstructuredIOLoader'
    ) as mock:
        yield mock


def test_initialization_with_custom_embedding(
    vector_retriever, mock_embedding_model
):
    r"""
    Test initialization with a custom embedding model.
    """
    assert vector_retriever.embedding_model == mock_embedding_model


def test_initialization_with_default_embedding():
    r"""
    Test initialization with default embedding model.
    """
    retriever = VectorRetriever()
    assert isinstance(retriever.embedding_model, OpenAIEmbedding)

from unittest.mock import patch

def test_process(mock_unstructured_modules):
    r"""
    Test process method with patch.
    """
    vector_retriever = VectorRetriever()
    with patch.object(vector_retriever, 'process') as mock_process:
        mock_process.return_value = ["fake_result"]
        test_url = "https://www.camel-ai.org/"
        result = vector_retriever.process(content=test_url)
        mock_process.assert_called_once_with(content=test_url)
        assert result == ["fake_result"]

def test_query(vector_retriever):
    r"""
    Test query method.
    """
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


def test_query_no_results(vector_retriever):
    r"""
    Test query with no results found.
    """
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

def test_query_payload_none(vector_retriever):
    r"""
    Test query with payload None.
    """
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
