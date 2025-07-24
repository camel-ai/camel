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
import sys
from unittest.mock import MagicMock, patch

import pytest
from surrealdb import RecordID

from camel.storages.vectordb_storages.surreal import (
    SurrealStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)

# Mock the module if surrealdb is not installed
sys.modules['surrealdb'] = MagicMock()
sys.modules['surrealdb.data'] = MagicMock()
sys.modules['surrealdb.data.types'] = MagicMock()
sys.modules['surrealdb.data.types.record_id'] = MagicMock()


@pytest.fixture
def storage():
    with patch("surrealdb.Surreal") as mock_surreal:
        mock_db = MagicMock()
        mock_surreal.return_value = mock_db

        # Mock the methods that would be called during initialization
        mock_db.signin = MagicMock()
        mock_db.use = MagicMock()
        mock_db.query_raw = MagicMock(
            return_value={"result": [{"result": {"tables": {}}}]}
        )

        storage = SurrealStorage(vector_dim=3)
        yield storage, mock_db


def test_add(storage):
    storage_instance, mock_db = storage
    vec1 = VectorRecord(vector=[0.1, 0.2, 0.3], payload={"name": "test_1"})
    vec2 = VectorRecord(vector=[0.4, 0.5, 0.6], payload={"name": "test_2"})

    storage_instance.add([vec1, vec2])
    assert mock_db.create.call_count == 2

    mock_db.create.assert_any_call(
        storage_instance.table,
        {"payload": {"name": "test_1"}, "embedding": [0.1, 0.2, 0.3]},
    )
    mock_db.create.assert_any_call(
        storage_instance.table,
        {"payload": {"name": "test_2"}, "embedding": [0.4, 0.5, 0.6]},
    )


def test_query(storage):
    storage_instance, mock_db = storage
    mock_db.query.return_value = [
        {
            "id": RecordID(table_name="documents", identifier="1"),
            "payload": {"id": "1"},
            "embedding": [0.1, 0.2, 0.3],
            "dist": 0.9,
        },
        {
            "id": RecordID(table_name="documents", identifier="2"),
            "payload": {"id": "2"},
            "embedding": [0.4, 0.5, 0.6],
            "dist": 0.8,
        },
    ]

    query = VectorDBQuery(query_vector=[0.2, 0.3, 0.4], top_k=2)
    results = storage_instance.query(query)

    assert isinstance(results, list)
    assert all(isinstance(r, VectorDBQueryResult) for r in results)
    assert len(results) == 2


def test_status(storage):
    storage_instance, mock_db = storage

    mock_db.query.side_effect = [
        {"tables": {storage_instance.table: {}}},
        {
            'events': {},
            'fields': {
                'embedding': 'DEFINE FIELD embedding ON documents TYPE array<float> PERMISSIONS FULL',  # noqa: E501
                'embedding[*]': 'DEFINE FIELD embedding[*] ON documents TYPE float PERMISSIONS FULL',  # noqa: E501
                'payload': 'DEFINE FIELD payload ON documents FLEXIBLE TYPE object PERMISSIONS FULL',  # noqa: E501
            },
            'indexes': {
                'hnsw_idx': 'DEFINE INDEX hnsw_idx ON documents FIELDS embedding HNSW DIMENSION 4 DIST COSINE TYPE F64 EFC 150 M 12 M0 24 LM 0.40242960438184466f'  # noqa: E501
            },
            'lives': {},
            'tables': {},
        },
        {"count": 5},
    ]

    status = storage_instance.status()

    assert isinstance(status, VectorDBStatus)
    assert status.vector_dim == 4
    assert status.vector_count == 5


def test_delete_all(storage):
    storage_instance, mock_db = storage

    storage_instance.delete(if_all=True)

    mock_db.delete.assert_called_once_with(storage_instance.table)


def test_delete_ids(storage):
    storage_instance, mock_db = storage

    # Mock RecordID class
    mock_record_id = MagicMock()
    mock_record_instance = MagicMock()
    mock_record_id.return_value = mock_record_instance

    # Set up the mock in sys.modules
    sys.modules['surrealdb.data.types.record_id'].RecordID = mock_record_id

    storage_instance.delete(ids=["id1", "id2"])

    assert mock_record_id.call_count == 2
    assert mock_db.delete.call_count == 2

    # Verify RecordID was called with correct parameters
    mock_record_id.assert_any_call(storage_instance.table, "id1")
    mock_record_id.assert_any_call(storage_instance.table, "id2")
