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
import json
from unittest.mock import MagicMock, patch

import pytest

from camel.storages import VectorDBQuery, VectorRecord, WeaviateStorage


@pytest.fixture
def mock_weaviate_client():
    r"""Create a mock Weaviate client with collections interface."""
    with patch('weaviate.connect_to_local') as mock_connect:
        mock_client = MagicMock()
        mock_connect.return_value = mock_client

        # Mock collections interface
        mock_collection = MagicMock()
        mock_client.collections.get.return_value = mock_collection
        mock_client.collections.create = MagicMock()
        mock_client.collections.delete = MagicMock()

        # Mock collection config
        mock_collection.config.get.return_value = {}

        # Mock batch interface
        mock_batch = MagicMock()
        mock_collection.batch.dynamic.return_value.__enter__.return_value = (
            mock_batch
        )

        # Mock aggregate interface for status queries
        mock_aggregate = MagicMock()
        mock_aggregate.total_count = 2
        mock_collection.aggregate.over_all.return_value = mock_aggregate

        yield mock_client, mock_collection


def test_weaviate_storage_initialization(mock_weaviate_client):
    r"""Test WeaviateStorage initialization functionality."""
    mock_client, _ = mock_weaviate_client

    with (
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._get_connection_client',
            return_value=mock_client,
        ),
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._check_and_create_collection'
        ),
    ):
        storage = WeaviateStorage(
            vector_dim=4,
            collection_name="test_collection",
            connection_type="local",
        )

        assert storage.vector_dim == 4
        assert storage.collection_name == "test_collection"
        assert storage.connection_type == "local"
        assert storage.distance_metric == "cosine"
        assert storage.vector_index_type == "hnsw"


def test_add_vectors(mock_weaviate_client):
    r"""Test adding vectors to storage."""
    mock_client, mock_collection = mock_weaviate_client

    with (
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._get_connection_client',
            return_value=mock_client,
        ),
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._check_and_create_collection'
        ),
    ):
        storage = WeaviateStorage(
            vector_dim=4, collection_name="test_collection"
        )

        # Prepare test vectors
        vectors = [
            VectorRecord(
                id="1",
                vector=[0.1, 0.2, 0.3, 0.4],
                payload={"label": "A", "type": "test"},
            ),
            VectorRecord(
                id="2",
                vector=[0.5, 0.6, 0.7, 0.8],
                payload={"label": "B", "type": "test"},
            ),
        ]

        # Execute add operation
        storage.add(vectors)

        # Verify batch interface was called
        mock_collection.batch.dynamic.assert_called_once()


def test_query_vectors(mock_weaviate_client):
    r"""Test querying vectors functionality."""
    mock_client, mock_collection = mock_weaviate_client

    # Mock query response
    mock_object = MagicMock()
    mock_object.uuid = "1111"
    mock_object.properties = {
        "payload": json.dumps({"label": "A", "type": "test"})
    }
    mock_object.vector = {"default": [0.1, 0.2, 0.3, 0.4]}
    mock_object.metadata.distance = 0.1

    mock_response = MagicMock()
    mock_response.objects = [mock_object]
    mock_collection.query.near_vector.return_value = mock_response

    with (
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._get_connection_client',
            return_value=mock_client,
        ),
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._check_and_create_collection'
        ),
    ):
        storage = WeaviateStorage(
            vector_dim=4,
            collection_name="test_collection",
            distance_metric="cosine",
        )

        # Execute query
        query = VectorDBQuery(query_vector=[0.1, 0.2, 0.3, 0.4], top_k=1)
        results = storage.query(query)

        # Verify results
        assert len(results) == 1
        assert results[0].record.id == "1111"
        assert results[0].record.payload == {"label": "A", "type": "test"}
        assert results[0].record.vector == [0.1, 0.2, 0.3, 0.4]
        assert results[0].similarity > 0  # Similarity should be greater than 0

        # Verify query method was called correctly
        mock_collection.query.near_vector.assert_called_once()


def test_delete_vectors(mock_weaviate_client):
    r"""Test deleting vectors functionality.

    Verifies that vectors can be deleted by ID and that the
    delete_many interface is called correctly.
    """
    mock_client, mock_collection = mock_weaviate_client

    with (
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._get_connection_client',
            return_value=mock_client,
        ),
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._check_and_create_collection'
        ),
        patch('weaviate.classes.query.Filter') as mock_filter,
    ):
        # Mock filter chain
        mock_filter.by_id.return_value.contains_any.return_value = MagicMock()

        storage = WeaviateStorage(
            vector_dim=4, collection_name="test_collection"
        )

        # Execute delete operation
        ids_to_delete = ["1111", "222"]
        storage.delete(ids_to_delete)

        # Verify delete method was called
        mock_collection.data.delete_many.assert_called_once()


def test_status(mock_weaviate_client):
    r"""Test getting storage status functionality.

    Verifies that storage status information including vector dimension
    and vector count can be retrieved correctly.
    """
    mock_client, mock_collection = mock_weaviate_client

    # Mock aggregate results
    mock_aggregate = MagicMock()
    mock_aggregate.total_count = 5
    mock_collection.aggregate.over_all.return_value = mock_aggregate

    with (
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._get_connection_client',
            return_value=mock_client,
        ),
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._check_and_create_collection'
        ),
    ):
        storage = WeaviateStorage(
            vector_dim=4, collection_name="test_collection"
        )

        # Get status
        status = storage.status()

        # Verify status information
        assert status.vector_dim == 4
        assert status.vector_count == 5

        # Verify aggregate method was called
        mock_collection.aggregate.over_all.assert_called_once()


def test_clear_collection(mock_weaviate_client):
    r"""Test clearing collection functionality.

    Verifies that the collection can be cleared by deleting and
    recreating it properly.
    """
    mock_client, mock_collection = mock_weaviate_client

    with (
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._get_connection_client',
            return_value=mock_client,
        ),
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._check_and_create_collection'
        ),
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._create_collection'
        ) as mock_create,
    ):
        storage = WeaviateStorage(
            vector_dim=4, collection_name="test_collection"
        )

        # Execute clear operation
        storage.clear()

        # Verify collection was deleted and recreated
        mock_client.collections.delete.assert_called_once_with(
            "test_collection"
        )
        mock_create.assert_called_once()


def test_empty_operations(mock_weaviate_client):
    r"""Test handling of empty operations.

    Verifies that empty add and delete operations are handled gracefully
    without calling the underlying APIs.
    """
    mock_client, mock_collection = mock_weaviate_client

    with (
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._get_connection_client',
            return_value=mock_client,
        ),
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._check_and_create_collection'
        ),
    ):
        storage = WeaviateStorage(
            vector_dim=4, collection_name="test_collection"
        )

        # Test empty add
        storage.add([])
        mock_collection.batch.dynamic.assert_not_called()

        # Test empty delete
        storage.delete([])
        mock_collection.data.delete_many.assert_not_called()


def test_similarity_calculations():
    r"""Test similarity calculation functionality.

    Verifies that different distance metrics (cosine, L2, hamming) are
    correctly converted to similarity scores.
    """
    with (
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._get_connection_client'
        ),
        patch(
            'camel.storages.vectordb_storages.weaviate.WeaviateStorage._check_and_create_collection'
        ),
    ):
        # Test cosine distance
        storage_cosine = WeaviateStorage(
            vector_dim=4, distance_metric="cosine"
        )
        similarity = storage_cosine._calculate_similarity_from_distance(0.2)
        assert similarity == 0.9  # 1 - (0.2 / 2)

        # Test L2 distance
        storage_l2 = WeaviateStorage(
            vector_dim=4, distance_metric="l2-squared"
        )
        similarity = storage_l2._calculate_similarity_from_distance(1.0)
        assert similarity == 0.5  # 1 / (1 + 1)

        # Test Hamming distance
        storage_hamming = WeaviateStorage(
            vector_dim=4, distance_metric="hamming"
        )
        similarity = storage_hamming._calculate_similarity_from_distance(2.0)
        assert similarity == 0.5  # 1 - (2 / 4)
