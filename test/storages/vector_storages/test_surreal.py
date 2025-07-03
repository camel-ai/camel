import pytest
from unittest.mock import patch, MagicMock

from surrealdb import Surreal

from camel.storages.vectordb_storages.surreal import SurrealStorage
from camel.storages.vectordb_storages import VectorRecord, VectorDBQuery, VectorDBQueryResult, VectorDBStatus
from surrealdb.data.types.record_id import RecordID

@pytest.fixture
def storage():
    with patch("camel.storages.vectordb_storages.surreal.Surreal") as mock_surreal:
        mock_db = MagicMock()
        mock_surreal.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_surreal.return_value.__exit__ = MagicMock(return_value=None)
        storage = SurrealStorage(vector_dim=3)

        yield storage, mock_db

def test_add(storage):
    storage_instance, mock_db = storage
    vec1 = VectorRecord(vector=[0.1, 0.2, 0.3], payload={"name": "test_1"})
    vec2 = VectorRecord(vector=[0.4, 0.5, 0.6], payload={"name": "test_2"})

    storage_instance.add([vec1, vec2])
    assert mock_db.create.call_count == 2

    mock_db.create.assert_any_call(storage_instance.table, {
        "payload": {"name": "test_1"},
        "embedding": [0.1, 0.2, 0.3]
    })
    mock_db.create.assert_any_call(storage_instance.table, {
        "payload": {"name": "test_2"},
        "embedding": [0.4, 0.5, 0.6]
    })

def test_query(storage):
    storage_instance, mock_db = storage
    mock_db.query_raw.return_value = {
        "result": [{
            "result": [
                {"payload": {"id": "1"}, "score": 0.1},
                {"payload": {"id": "2"}, "score": 0.2},
            ]
        }]
    }
    
    query = VectorDBQuery(query_vector=[0.2, 0.3, 0.4], top_k=2)
    results = storage_instance.query(query)

    assert isinstance(results, list)
    assert all(isinstance(r, VectorDBQueryResult) for r in results)
    assert len(results) == 2

def test_status(storage):
    storage_instance, mock_db = storage

    mock_db.query_raw.side_effect = [
        {"result": [{"result": {"tables": {storage_instance.table: {}}}}]},
        {"result": [{"result": {"indexes": {"hnsw_idx": "DIMENSION 3"}}}]},
        {"result": [{"result": [{"count": 1} for _ in range(5)]}]},  
    ]
    
    status = storage_instance.status()

    assert isinstance(status, VectorDBStatus)
    assert status.vector_dim == 3
    assert status.vector_count == 5


def test_delete_all(storage):
    storage_instance, mock_db = storage

    storage_instance.delete(if_all=True)

    mock_db.delete.assert_called_once_with(storage_instance.table)


def test_delete_ids(storage):
    storage_instance, mock_db = storage

    storage_instance.delete(ids=["id1", "id2"])

    assert mock_db.delete.call_count == 2
    calls_args = [call_args[0][0] for call_args in mock_db.delete.call_args_list]
    assert all(isinstance(arg, RecordID) for arg in calls_args)

"""
(.camel) [lyz@dev4 surrealDB]$ pytest test_surreal.py 
======================================================================= test session starts ========================================================================
platform linux -- Python 3.12.11, pytest-7.4.4, pluggy-1.6.0
rootdir: /home/lyz/rag/surrealDB
plugins: cov-4.1.0, anyio-4.9.0, Faker-19.13.0, asyncio-0.23.8
asyncio: mode=Mode.STRICT
collected 5 items                                                                                                                                                  

test_surreal.py .....                                                                                                                                        [100%]

======================================================================== 5 passed in 0.67s =========================================================================


"""