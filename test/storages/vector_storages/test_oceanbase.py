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

from camel.storages import OceanBaseStorage, VectorDBQuery, VectorRecord


@pytest.fixture
def mock_oceanbase_storage():
    with patch('camel.storages.OceanBaseStorage') as MockOceanBaseStorage:
        mock_storage1 = create_autospec(OceanBaseStorage)
        mock_storage2 = create_autospec(OceanBaseStorage)
        MockOceanBaseStorage.side_effect = [mock_storage1, mock_storage2]
        yield mock_storage1, mock_storage2


def setup_mock_storage(mock_storage, vectors, query_result_id, payload):
    mock_query_result = MagicMock()
    mock_query_result.record.id = query_result_id
    mock_query_result.record.payload = payload
    mock_storage.query.return_value = [mock_query_result]
    mock_storage.add(vectors)
    mock_storage.status.return_value = MagicMock(vector_count=0)


def test_multiple_clients(mock_oceanbase_storage):
    mock_storage1, mock_storage2 = mock_oceanbase_storage

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


@pytest.fixture
def mock_ob_client():
    with patch('pyobvector.client.ObVecClient') as MockObVecClient:
        client = MagicMock()

        # Setup mock methods
        client.check_table_exists.return_value = False
        client.create_table.return_value = None
        client.create_vidx_with_vec_index_param.return_value = None
        client.add.return_value = None
        client.delete.return_value = None
        client.perform_raw_text_sql.return_value.fetchone.return_value = [10]

        MockObVecClient.return_value = client
        yield client


def test_oceanbase_storage_initialization(mock_ob_client):
    # Create a mock factory that returns a new mock IndexParams with iterator
    # each time
    def create_mock_index_params():
        mock_index_param = MagicMock()
        mock_index_params = MagicMock()
        mock_index_params.__iter__.return_value = iter([mock_index_param])
        return mock_index_params

    with patch('pyobvector.schema.VECTOR'):
        with patch(
            'pyobvector.client.index_param.IndexParams',
            side_effect=create_mock_index_params,
        ):
            with patch('pyobvector.client.index_param.IndexParam'):
                # Test initialization with default parameters
                storage = OceanBaseStorage(
                    vector_dim=64,
                    table_name="test_table",
                    uri="127.0.0.1:2881",
                    user="root@test",
                    password="",
                    db_name="test",
                )

                # Verify that check_table_exists was called
                mock_ob_client.check_table_exists.assert_called_once_with(
                    "test_table"
                )

                mock_ob_client.create_table.assert_called_once()

                # Verify that create_vidx_with_vec_index_param was called
                mock_ob_client.create_vidx_with_vec_index_param.assert_called_once()

                # Test different distance metrics
                assert storage.distance == "l2"

                # Create storage with cosine distance
                cosine_storage = OceanBaseStorage(
                    vector_dim=64, table_name="test_table", distance="cosine"
                )
                assert cosine_storage.distance == "cosine"


def test_oceanbase_storage_operations(mock_ob_client):
    # Create a mock factory that returns a new mock IndexParams with iterator
    # each time
    def create_mock_index_params():
        mock_index_param = MagicMock()
        mock_index_params = MagicMock()
        mock_index_params.__iter__.return_value = iter([mock_index_param])
        return mock_index_params

    with patch('pyobvector.schema.VECTOR'):
        with patch(
            'pyobvector.client.index_param.IndexParams',
            side_effect=create_mock_index_params,
        ):
            with patch('pyobvector.client.index_param.IndexParam'):
                with patch('sqlalchemy.func'):
                    # Setup mock for query results
                    mock_result = MagicMock()
                    mock_result._mapping = {
                        "id": 1,
                        "embedding": [0.1, 0.2, 0.3, 0.4],
                        "metadata": {"text": "test_data"},
                        "l2_distance": 0.5,
                    }
                    mock_ob_client.ann_search.return_value = [mock_result]

                    # Initialize storage
                    storage = OceanBaseStorage(
                        vector_dim=4,
                        table_name="test_table",
                        uri="127.0.0.1:2881",
                    )

                    # Test add method
                    vectors = [
                        VectorRecord(
                            vector=[0.1, 0.2, 0.3, 0.4],
                            payload={"text": "test_data"},
                        )
                    ]
                    storage.add(vectors)
                    mock_ob_client.insert.assert_called_once()

                    # Test query method
                    query = VectorDBQuery(
                        query_vector=[0.1, 0.2, 0.3, 0.4], top_k=1
                    )
                    results = storage.query(query)
                    assert len(results) == 1
                    assert results[0].record.payload == {"text": "test_data"}
                    mock_ob_client.ann_search.assert_called_once()

                    # Test clear method
                    storage.clear()
                    mock_ob_client.delete.assert_called_once()


def test_distance_to_similarity_conversion():
    # Create a mock factory that returns a new mock IndexParams with iterator
    # each time
    def create_mock_index_params():
        mock_index_param = MagicMock()
        mock_index_params = MagicMock()
        mock_index_params.__iter__.return_value = iter([mock_index_param])
        return mock_index_params

    with patch('pyobvector.client.ObVecClient'):
        with patch('pyobvector.schema.VECTOR'):
            with patch(
                'pyobvector.client.index_param.IndexParams',
                side_effect=create_mock_index_params,
            ):
                with patch('pyobvector.client.index_param.IndexParam'):
                    # Test cosine distance conversion
                    cosine_storage = OceanBaseStorage(
                        vector_dim=4,
                        table_name="test_table",
                        distance="cosine",
                    )
                    cosine_sim = (
                        cosine_storage._convert_distance_to_similarity(0.2)
                    )
                    assert cosine_sim == 0.8  # 1.0 - 0.2

                    # Test L2 distance conversion (uses exponential decay)
                    import math

                    l2_storage = OceanBaseStorage(
                        vector_dim=4,
                        table_name="test_table",
                        distance="l2",
                    )
                    l2_sim = l2_storage._convert_distance_to_similarity(0.2)
                    assert l2_sim == pytest.approx(math.exp(-0.2))
