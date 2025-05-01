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

from camel.storages import MilvusStorage, VectorDBQuery, VectorRecord


@pytest.fixture
def mock_milvus_storage():
    with patch('camel.storages.MilvusStorage') as MockMilvusStorage:
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


@pytest.fixture
def milvus_test_setup():
    """Setup fixture for Milvus tests with mock search results.

    This fixture provides common setup for testing Milvus query functionality,
    including mock client, search results and storage instance.
    """
    # Mock search results structure: [[result1, result2, result3]]
    mock_search_results = [
        [
            {
                'id': '1',
                'distance': 0.9,
                'entity': {
                    'vector': [0.1, 0.1, 0.1, 0.1],
                    'payload': {'message': 'text1'},
                },
            },
            {
                'id': '2',
                'distance': 0.8,
                'entity': {
                    'vector': [0.2, 0.2, 0.2, 0.2],
                    'payload': {'message': 'text2'},
                },
            },
            {
                'id': '3',
                'distance': 0.7,
                'entity': {
                    'vector': [0.3, 0.3, 0.3, 0.3],
                    'payload': {'message': 'text3'},
                },
            },
        ]
    ]

    # Mock Milvus client
    with patch('pymilvus.MilvusClient') as MockMilvusClient:
        mock_client = MockMilvusClient.return_value
        mock_client.search.return_value = mock_search_results

        # Set up storage instance
        with (
            patch(
                'camel.storages.vectordb_storages.milvus.MilvusStorage._create_collection'
            ),
            patch(
                'camel.storages.vectordb_storages.milvus.MilvusStorage._check_and_create_collection'
            ),
            patch(
                'camel.storages.vectordb_storages.milvus.MilvusStorage._collection_exists',
                return_value=True,
            ),
        ):
            storage = MilvusStorage(
                vector_dim=4,
                url_and_api_key=("http://localhost:19530", "fake_api_key"),
                collection_name="test_collection",
            )
            storage._client = mock_client

            yield storage, mock_client, mock_search_results


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


def test_milvus_return_multiple_results(milvus_test_setup):
    r"""Test that Milvus returns multiple results (top_k > 1)

    This test verifies the fix for a previous bug:
    In the previous implementation, the loop would only execute once because
    the outer list only had one element, and it only took the first result of
    each element (point[0]), which meant it could return at most one result.
    The fixed code should be able to return the complete top_k results.
    """
    storage, mock_client, _ = milvus_test_setup

    # Execute query
    query = VectorDBQuery(query_vector=[0.1, 0.1, 0.1, 0.1], top_k=3)
    results = storage.query(query)

    # Verify results
    assert len(results) == 3, "Should return all 3 results (top_k=3)"

    # Verify the order and content of returned results
    assert results[0].record.id == '1'
    assert results[0].similarity == 0.9
    assert results[0].record.payload == {'message': 'text1'}

    assert results[1].record.id == '2'
    assert results[1].similarity == 0.8
    assert results[1].record.payload == {'message': 'text2'}

    assert results[2].record.id == '3'
    assert results[2].similarity == 0.7
    assert results[2].record.payload == {'message': 'text3'}

    # Verify search method was called correctly
    mock_client.search.assert_called_once()
    call_args = mock_client.search.call_args[1]
    assert call_args['collection_name'] == "test_collection"
    assert call_args['limit'] == 3


def test_milvus_bug_single_result(milvus_test_setup):
    r"""Test the bug behavior of Milvus before fix, returning only one result

    This test simulates the code behavior before the fix, where even if
    top_k=3 was specified, it would only return one result.
    """
    storage, mock_client, _ = milvus_test_setup

    # Mock old implementation - the way it was processed before the fix
    def mock_buggy_query(query, **kwargs):
        from camel.storages import VectorDBQueryResult

        search_result = mock_client.search(
            collection_name=storage.collection_name,
            data=[query.query_vector],
            limit=query.top_k,
            output_fields=['vector', 'payload'],
            **kwargs,
        )
        query_results = []
        for point in search_result:
            query_results.append(
                VectorDBQueryResult.create(
                    similarity=(point[0]['distance']),
                    id=str(point[0]['id']),
                    payload=(point[0]['entity'].get('payload')),
                    vector=point[0]['entity'].get('vector'),
                )
            )
        return query_results

    # Replace query method with the buggy version
    storage.query = mock_buggy_query

    # Execute query
    query = VectorDBQuery(query_vector=[0.1, 0.1, 0.1, 0.1], top_k=3)
    results = storage.query(query=query)

    # Verify results - before fix would only return 1 result
    assert (
        len(results) == 1
    ), "Before the fix, should return only 1 result, even if top_k=3"

    # Verify that it's the first result
    assert results[0].record.id == '1'
    assert results[0].similarity == 0.9
    assert results[0].record.payload == {'message': 'text1'}

    # Verify search method was called correctly
    mock_client.search.assert_called_once()
    call_args = mock_client.search.call_args[1]
    assert call_args['collection_name'] == "test_collection"
    assert (
        call_args['limit'] == 3
    )  # Even though limit=3, the buggy version only returns the first result
