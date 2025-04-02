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

from camel.storages import (
    MilvusStorage,
    VectorDBQuery,
    VectorDBSearch,
    VectorRecord,
)


@pytest.fixture
def mock_milvus_storage():
    with patch("camel.storages.MilvusStorage") as MockMilvusStorage:
        mock_storage1 = create_autospec(MilvusStorage)
        mock_storage2 = create_autospec(MilvusStorage)
        MockMilvusStorage.side_effect = [mock_storage1, mock_storage2]
        yield mock_storage1, mock_storage2


def setup_mock_storage(mock_storage, vectors, query_result_id, payload):
    mock_query_result = MagicMock()
    mock_query_result.record.id = query_result_id
    mock_query_result.record.payload = payload
    mock_storage.query.return_value = [mock_query_result]
    mock_storage.add(vectors)
    mock_storage.status.return_value = MagicMock(vector_count=0)


def test_multiple_remote_clients(mock_milvus_storage):
    mock_storage1, mock_storage2 = mock_milvus_storage

    # Example vectors for testing
    vectors1 = [
        VectorRecord(
            vector=[0.1, 0.1, 0.1, 0.1], payload={"message": "text1"}
        ),
        VectorRecord(
            vector=[0.1, -0.1, -0.1, 0.1], payload={"message": "text2"}
        ),
    ]
    vectors2 = [
        VectorRecord(
            vector=[-0.1, 0.1, -0.1, 0.1], payload={"message": "text3"}
        ),
        VectorRecord(
            vector=[-0.1, 0.1, 0.1, 0.1],
            payload={"message": "text4", "number": 1},
        ),
    ]
    setup_mock_storage(
        mock_storage1, vectors1, vectors1[0].id, {"message": "text1"}
    )
    setup_mock_storage(
        mock_storage2, vectors2, vectors2[0].id, {"message": "text3"}
    )

    # Assert add method was called correctly
    mock_storage1.add.assert_called_once_with(vectors1)
    mock_storage2.add.assert_called_once_with(vectors2)

    # Perform and verify queries
    query1 = VectorDBQuery(query_vector=[0.1, 0.2, 0.1, 0.1], top_k=1)
    result1 = mock_storage1.query(query1)
    assert result1[0].record.id == vectors1[0].id
    assert result1[0].record.payload == {"message": "text1"}

    query2 = VectorDBQuery(query_vector=[-0.1, 0.2, -0.1, 0.1], top_k=1)
    result2 = mock_storage2.query(query2)
    assert result2[0].record.id == vectors2[0].id
    assert result2[0].record.payload == {"message": "text3"}

    # Clear and check status for each storage
    mock_storage1.clear()
    status1 = mock_storage1.status()
    assert status1.vector_count == 0

    mock_storage2.clear()
    status2 = mock_storage2.status()
    assert status2.vector_count == 0


def setup_mock_storage_for_search(
    mock_storage, vectors, query_result_id, payload
):
    mock_query_result = MagicMock()
    mock_query_result.record.id = query_result_id
    mock_query_result.record.payload = payload
    mock_storage.search.return_value = [mock_query_result]
    mock_storage.add(vectors)
    mock_storage.status.return_value = MagicMock(vector_count=0)


def test_search_method(mock_milvus_storage):
    # Use both mocked storages for testing search with more data
    mock_storage1, mock_storage2 = mock_milvus_storage

    # Setup multiple vector records for database 1
    vectors1 = [
        VectorRecord(
            vector=[0.5, 0.5, 0.5, 0.5],
            payload={"category": "fruit", "color": "red", "message": "apple"},
        ),
        VectorRecord(
            vector=[0.6, 0.6, 0.6, 0.6],
            payload={"category": "fruit", "color": "red", "message": "cherry"},
        ),
        VectorRecord(
            vector=[0.7, 0.7, 0.7, 0.7],
            payload={"category": "fruit", "color": "green", "message": "pear"},
        ),
    ]
    setup_mock_storage_for_search(
        mock_storage1, vectors1, vectors1[0].id, vectors1[0].payload
    )

    # Setup multiple vector records for database 2
    vectors2 = [
        VectorRecord(
            vector=[-0.5, -0.5, -0.5, -0.5],
            payload={
                "category": "fruit",
                "color": "red",
                "message": "strawberry",
            },
        ),
        VectorRecord(
            vector=[-0.6, -0.6, -0.6, -0.6],
            payload={
                "category": "fruit",
                "color": "red",
                "message": "raspberry",
            },
        ),
        VectorRecord(
            vector=[-0.7, -0.7, -0.7, -0.7],
            payload={
                "category": "fruit",
                "color": "yellow",
                "message": "banana",
            },
        ),
    ]
    setup_mock_storage_for_search(
        mock_storage2, vectors2, vectors2[0].id, vectors2[0].payload
    )

    # Assert add method was called correctly
    mock_storage1.add.assert_called_once_with(vectors1)
    mock_storage2.add.assert_called_once_with(vectors2)

    search_query1 = VectorDBSearch(
        payload_filter={"category": "fruit", "color": "red"}, top_k=1
    )
    search_query2 = VectorDBSearch(
        payload_filter={"color": "yellow", "message": "banana"}, top_k=1
    )
    # Call the search method on both storages
    search_results1 = mock_storage1.search(search_query1)
    search_results2 = mock_storage2.search(search_query2)

    assert len(search_results1) == 1
    assert search_results1[0].record.id == vectors1[0].id
    assert search_results1[0].record.payload == {
        "category": "fruit",
        "color": "red",
        "message": "apple",
    }

    assert len(search_results2) == 1
    assert search_results2[0].record.id == vectors2[0].id
    assert search_results2[0].record.payload == {
        "category": "fruit",
        "color": "red",
        "message": "strawberry",
    }
