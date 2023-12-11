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

import os
import shutil
from unittest.mock import Mock, patch

import pytest

from camel.embeddings import OpenAIEmbedding
from camel.functions.retrieval_function import RetrievalFunction
from camel.storages.vectordb_storages import QdrantStorage


@pytest.fixture
def temp_storage_path():
    # Define the path to the temporary storage
    path = 'test/functions/tempory_storage'

    # Setup phase: yield the path for use in tests
    yield path

    # Teardown phase: remove the files created in the temporary storage
    if os.path.exists(path):
        shutil.rmtree(path)


# Fixtures for common mock objects
@pytest.fixture
def mock_openai_embedding():
    return Mock(spec=OpenAIEmbedding)


@pytest.fixture
def mock_qdrant_storage():
    return Mock(spec=QdrantStorage)


@pytest.fixture
def retrieval_function_instance():
    return RetrievalFunction()


def test_retrieval_function_initialization():
    # Test with default parameters
    retrieval_func = RetrievalFunction()
    assert isinstance(retrieval_func.embedding_model, OpenAIEmbedding)
    assert isinstance(retrieval_func.vector_storage, QdrantStorage)
    assert retrieval_func.top_k == 1

    # Test with custom top_k
    retrieval_func = RetrievalFunction(top_k=5)
    assert retrieval_func.top_k == 5

    # Test with invalid top_k
    with pytest.raises(ValueError):
        RetrievalFunction(top_k=0)


def test_set_vector_storage_local_without_vector_path(
        retrieval_function_instance):
    # Test setting local storage without providing 'vector_path'
    with pytest.raises(ValueError):
        retrieval_function_instance._set_vector_storage(storage_type='local')


def test_set_vector_storage_local_with_url_and_api_key(
        retrieval_function_instance):
    # Test setting local storage with 'url_and_api_key' which should not be
    # provided
    with pytest.raises(ValueError):
        retrieval_function_instance._set_vector_storage(
            vector_storage_local_path='examples/rag/',
            url_and_api_key=('http://example.com', 'api_key'),
            storage_type='local')


def test_set_vector_storage_local_with_valid_path(retrieval_function_instance,
                                                  temp_storage_path):
    storage = retrieval_function_instance._set_vector_storage(
        storage_type='local', collection_name='test_collection',
        vector_storage_local_path=temp_storage_path)
    assert isinstance(storage, QdrantStorage)


def test_set_vector_storage_local_without_path(retrieval_function_instance):
    with pytest.raises(ValueError):
        retrieval_function_instance._set_vector_storage(
            storage_type='local', vector_storage_local_path=None)


def test_set_vector_storage_remote_without_api_key(
        retrieval_function_instance):
    with pytest.raises(ValueError):
        retrieval_function_instance._set_vector_storage(
            storage_type='remote', url_and_api_key=None)


def test_set_vector_storage_invalid_type(retrieval_function_instance):
    with pytest.raises(ValueError):
        retrieval_function_instance._set_vector_storage(
            storage_type='invalid_type')


def test_check_collection_status_local_valid(retrieval_function_instance,
                                             temp_storage_path):

    retrieval_function_instance._set_vector_storage(
        storage_type='local', collection_name='test_collection',
        vector_storage_local_path=temp_storage_path)
    assert retrieval_function_instance._check_collection_status(
        storage_type='local', collection_name='test_collection',
        vector_storage_local_path=temp_storage_path) is True


def test_check_collection_status_local_invalid(retrieval_function_instance):

    assert retrieval_function_instance._check_collection_status(
        storage_type='local', collection_name='test_collection',
        url_and_api_key=('http://example.com', 'api_key')) is False


def test_check_collection_status_remote_valid(retrieval_function_instance):

    assert retrieval_function_instance._check_collection_status(
        storage_type='remote', collection_name='latest', url_and_api_key=(
            "https://c7ac871b-0dca-4586-8b03-9ffb4e40363e.us-east4-0.gcp."
            "cloud.qdrant.io:6333",
            "axny37nzYHwg8jxbW-TnC90p8MibC1Tl4ypSwM87boZhSqvedvW_7w")) is True


def test_check_collection_status_remote_invalid(retrieval_function_instance):

    assert retrieval_function_instance._check_collection_status(
        storage_type='remote', collection_name='not_existing_collection_name',
        url_and_api_key=(
            "https://c7ac871b-0dca-4586-8b03-9ffb4e40363e.us-east4-0.gcp."
            "cloud.qdrant.io:6333",
            "axny37nzYHwg8jxbW-TnC90p8MibC1Tl4ypSwM87boZhSqvedvW_7w")) is False


def test_embed_and_store_chunks(mock_openai_embedding, mock_qdrant_storage):
    rf = RetrievalFunction(embedding_model=mock_openai_embedding,
                           vector_storage=mock_qdrant_storage)
    with patch('camel.functions.unstructured_io_fuctions.UnstructuredModules'
               ) as mock_unstructured:
        # Mock the return value of parse_file_or_url and chunk_elements
        mock_unstructured.return_value.parse_file_or_url.return_value = [
            "mocked content"
        ]
        mock_unstructured.return_value.chunk_elements.return_value = [
            "chunk1", "chunk2"
        ]
        rf._embed_and_store_chunks(
            "examples/rag/example_database/camel paper.pdf",
            mock_qdrant_storage)
        mock_openai_embedding.embed.assert_called()
        mock_qdrant_storage.add.assert_called()


def test_query_and_compile_results(mock_openai_embedding, mock_qdrant_storage):
    rf = RetrievalFunction(embedding_model=mock_openai_embedding,
                           vector_storage=mock_qdrant_storage)
    mock_qdrant_storage.query.return_value = [
        Mock(record=Mock(payload="result1")),
        Mock(record=Mock(payload="result2"))
    ]
    result = rf._query_and_compile_results("query", mock_qdrant_storage)
    assert "result1" in result and "result2" in result
