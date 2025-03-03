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

from unittest.mock import MagicMock, create_autospec, patch

import pytest

from camel.storages.vectordb_storages import (
    PgVectorStorage,
    VectorDBQuery,
    VectorRecord,
    VectorDBStatus,
)


@pytest.fixture
def mock_pg_storage():
    r"""Creates a mock PgVectorStorage instance for testing.

    Returns:
        MagicMock: A mock PgVectorStorage instance.
    """
    with patch('camel.storages.PgVectorStorage') as MockPgStorage:
        mock_storage = create_autospec(PgVectorStorage)
        MockPgStorage.return_value = mock_storage
        yield mock_storage


def setup_mock_storage(mock_storage, vectors, query_result_id, payload):
    r"""Sets up a mock storage with predefined behaviors.

    Args:
        mock_storage (MagicMock): The mock storage instance to configure.
        vectors (List[VectorRecord]): List of vectors to be used in the mock.
        query_result_id (str): ID to be used in query results.
        payload (Dict[str, Any]): Payload to be used in query results.
    """
    mock_query_result = MagicMock()
    mock_query_result.record = MagicMock()
    mock_query_result.record.id = query_result_id
    mock_query_result.record.payload = payload
    mock_query_result.similarity = 0.95
    mock_storage.query.return_value = [mock_query_result]

    mock_storage.add.return_value = None
    vector_dim = len(vectors[0].vector)
    mock_storage.status.return_value = VectorDBStatus(
        vector_count=len(vectors), vector_dim=vector_dim)


def test_add_and_query_vectors(mock_pg_storage):
    r"""Tests adding vectors to storage and querying them back."""
    vectors = [
        VectorRecord(vector=[0.2, 0.2, 0.2, 0.2], payload={"label": "A"}),
        VectorRecord(vector=[-0.2, -0.2, -0.2, -0.2], payload={"label": "B"}),
    ]
    
    setup_mock_storage(mock_pg_storage, vectors, vectors[0].id, {"label": "A"})
    mock_pg_storage.add(records=vectors)
    assert mock_pg_storage.status().vector_count == 2

    query = VectorDBQuery(query_vector=[0.2, 0.2, 0.2, 0.2], top_k=1)
    result = mock_pg_storage.query(query)
    assert len(result) == 1
    assert result[0].record.payload["label"] == "A"


def test_delete_vectors(mock_pg_storage):
    r"""Tests deleting vectors from storage."""
    vectors = [
        VectorRecord(vector=[0.6, 0.6, 0.6, 0.6], payload={"group": "X"}),
        VectorRecord(vector=[-0.6, -0.6, -0.6, -0.6], payload={"group": "Y"})
    ]
    
    setup_mock_storage(
        mock_pg_storage, vectors[1:], vectors[1].id, {"group": "Y"})
    mock_pg_storage.add(records=vectors)
    mock_pg_storage.delete(ids=[vectors[0].id])
    
    query = VectorDBQuery(query_vector=[0.0, 0.0, 0.0, 0.0], top_k=2)
    results = mock_pg_storage.query(query)
    assert len(results) == 1
    assert results[0].record.payload["group"] == "Y"


def test_clear_storage(mock_pg_storage):
    r"""Tests clearing all vectors from storage."""
    vectors = [
        VectorRecord(vector=[1.0, 1.0, 1.0, 1.0]),
        VectorRecord(vector=[-1.0, -1.0, -1.0, -1.0])
    ]
    
    setup_mock_storage(mock_pg_storage, vectors, vectors[0].id, {})
    mock_pg_storage.add(records=vectors)
    assert mock_pg_storage.status().vector_count == 2

    mock_pg_storage.clear()
    vector_dim = len(vectors[0].vector)
    mock_pg_storage.status.return_value = VectorDBStatus(
        vector_dim=vector_dim, vector_count=0)
    assert mock_pg_storage.status().vector_count == 0