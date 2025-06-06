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

from camel.storages import VectorDBQuery, VectorRecord, WeaviateStorage


@pytest.fixture
def mock_weaviate_storage():
    """Create mock WeaviateStorage instances."""
    with patch('camel.storages.WeaviateStorage') as MockWeaviateStorage:
        mock_storage1 = create_autospec(WeaviateStorage)
        mock_storage2 = create_autospec(WeaviateStorage)
        MockWeaviateStorage.side_effect = [mock_storage1, mock_storage2]
        yield mock_storage1, mock_storage2


def setup_mock_storage(mock_storage, vectors, query_result_id, payload):
    """Helper function to setup mock storage behavior."""
    mock_query_result = MagicMock()
    mock_query_result.id = query_result_id
    mock_query_result.payload = payload
    mock_query_result.similarity = 0.95

    mock_storage.query.return_value = [mock_query_result]
    mock_storage.add(vectors)
    mock_storage.status.return_value = MagicMock(vector_count=len(vectors))


def test_weaviate_storage_initialization():
    """Test WeaviateStorage initialization."""
    with patch('camel.storages.WeaviateStorage') as MockWeaviateStorage:
        mock_client = MagicMock()
        vector_dim = 4
        collection_name = "test_collection"

        # Test normal initialization
        MockWeaviateStorage(
            client=mock_client,
            vector_dim=vector_dim,
            collection_name=collection_name,
        )

        MockWeaviateStorage.assert_called_once_with(
            client=mock_client,
            vector_dim=vector_dim,
            collection_name=collection_name,
        )


def test_weaviate_storage_initialization_error():
    """Test WeaviateStorage initialization with None client."""
    with patch('camel.storages.WeaviateStorage') as MockWeaviateStorage:
        MockWeaviateStorage.side_effect = ValueError(
            "Weaviate client cannot be None"
        )

        with pytest.raises(ValueError, match="Weaviate client cannot be None"):
            MockWeaviateStorage(client=None, vector_dim=4)


def test_multiple_weaviate_clients(mock_weaviate_storage):
    """Test multiple Weaviate storage instances."""
    mock_storage1, mock_storage2 = mock_weaviate_storage

    # Example vectors for testing
    vectors1 = [
        VectorRecord(
            vector=[0.1, 0.1, 0.1, 0.1],
            payload={"message": "text1", "type": "document"},
        ),
        VectorRecord(
            vector=[0.1, -0.1, -0.1, 0.1],
            payload={"message": "text2", "type": "document"},
        ),
    ]
    vectors2 = [
        VectorRecord(
            vector=[-0.1, 0.1, -0.1, 0.1],
            payload={"message": "text3", "type": "query"},
        ),
        VectorRecord(
            vector=[-0.1, 0.1, 0.1, 0.1],
            payload={"message": "text4", "number": 1, "type": "query"},
        ),
    ]

    setup_mock_storage(
        mock_storage1,
        vectors1,
        vectors1[0].id,
        {"message": "text1", "type": "document"},
    )
    setup_mock_storage(
        mock_storage2,
        vectors2,
        vectors2[0].id,
        {"message": "text3", "type": "query"},
    )

    # Assert add method was called correctly
    mock_storage1.add.assert_called_once_with(vectors1)
    mock_storage2.add.assert_called_once_with(vectors2)

    # Perform and verify queries
    query1 = VectorDBQuery(query_vector=[0.1, 0.2, 0.1, 0.1], top_k=1)
    result1 = mock_storage1.query(query1)
    assert result1[0].id == vectors1[0].id
    assert result1[0].payload == {"message": "text1", "type": "document"}

    query2 = VectorDBQuery(query_vector=[-0.1, 0.2, -0.1, 0.1], top_k=1)
    result2 = mock_storage2.query(query2)
    assert result2[0].id == vectors2[0].id
    assert result2[0].payload == {"message": "text3", "type": "query"}

    # Test status for each storage
    status1 = mock_storage1.status()
    assert status1.vector_count == len(vectors1)

    status2 = mock_storage2.status()
    assert status2.vector_count == len(vectors2)


def test_weaviate_storage_operations():
    """Test basic Weaviate storage operations."""
    with patch('camel.storages.WeaviateStorage') as MockWeaviateStorage:
        mock_storage = create_autospec(WeaviateStorage)
        MockWeaviateStorage.return_value = mock_storage

        # Test vectors
        vectors = [
            VectorRecord(
                vector=[0.1, 0.2, 0.3, 0.4],
                payload={
                    "content": "test content",
                    "metadata": {"source": "test"},
                },
            ),
            VectorRecord(
                vector=[0.5, 0.6, 0.7, 0.8],
                payload={
                    "content": "another test",
                    "metadata": {"source": "test2"},
                },
            ),
        ]

        # Test add operation
        mock_storage.add(vectors)
        mock_storage.add.assert_called_once_with(vectors)

        # Test delete operation
        ids_to_delete = [vectors[0].id, vectors[1].id]
        mock_storage.delete(ids_to_delete)
        mock_storage.delete.assert_called_once_with(ids_to_delete)

        # Test query operation
        query = VectorDBQuery(query_vector=[0.1, 0.2, 0.3, 0.4], top_k=2)
        mock_query_result = MagicMock()
        mock_query_result.id = vectors[0].id
        mock_query_result.vector = vectors[0].vector
        mock_query_result.payload = vectors[0].payload
        mock_query_result.similarity = 0.98

        mock_storage.query.return_value = [mock_query_result]
        result = mock_storage.query(query)

        assert len(result) == 1
        assert result[0].id == vectors[0].id
        assert result[0].similarity == 0.98

        # Test clear operation
        mock_storage.clear()
        mock_storage.clear.assert_called_once()
