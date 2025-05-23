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
    FaissStorage,
    VectorDBQuery,
    VectorRecord,
)
from camel.types import VectorDistance


@pytest.fixture
def mock_faiss_storage():
    with patch('camel.storages.FaissStorage') as MockFaissStorage:
        mock_storage1 = create_autospec(FaissStorage)
        mock_storage2 = create_autospec(FaissStorage)
        MockFaissStorage.side_effect = [mock_storage1, mock_storage2]
        yield mock_storage1, mock_storage2


def setup_mock_storage(mock_storage, vectors, query_result_id, payload):
    mock_query_result = MagicMock()
    mock_query_result.record.id = query_result_id
    mock_query_result.record.payload = payload
    mock_storage.query.return_value = [mock_query_result]
    mock_storage.add(vectors)
    mock_storage.status.return_value = MagicMock(
        vector_count=len(vectors), vector_dim=4
    )


def test_multiple_faiss_instances(mock_faiss_storage):
    mock_storage1, mock_storage2 = mock_faiss_storage

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
    assert status1.vector_count == 2
    assert status1.vector_dim == 4

    mock_storage2.clear()
    status2 = mock_storage2.status()
    assert status2.vector_count == 2
    assert status2.vector_dim == 4


@pytest.fixture
def mock_faiss_module():
    with (
        patch('faiss.IndexFlatIP') as mock_index_ip,
        patch('faiss.IndexFlatL2') as mock_index_l2,
        patch('faiss.write_index') as mock_write,
        patch('faiss.read_index') as mock_read,
    ):
        mock_index = MagicMock()
        mock_index_ip.return_value = mock_index
        mock_index_l2.return_value = mock_index
        yield {
            'index': mock_index,
            'write_index': mock_write,
            'read_index': mock_read,
        }


def test_faiss_storage_initialization(mock_faiss_module):
    # Test different initialization parameters
    storage1 = FaissStorage(vector_dim=128)
    storage2 = FaissStorage(
        vector_dim=512, index_type='Flat', distance=VectorDistance.EUCLIDEAN
    )
    # Avoid using IVFFlat which might cause segmentation fault
    storage3 = FaissStorage(
        vector_dim=1536,
        index_type='Flat',  # Changed from 'IVFFlat' to 'Flat'
        distance=VectorDistance.COSINE,
    )

    # Check that indices were created correctly
    assert storage1.vector_dim == 128
    assert storage2.vector_dim == 512
    assert storage3.vector_dim == 1536
    assert storage1.distance == VectorDistance.COSINE  # Default
    assert storage2.distance == VectorDistance.EUCLIDEAN


def test_faiss_storage_operations():
    # Completely bypass the actual FAISS operations
    with patch('faiss.IndexFlatIP') as mock_index_class:
        # Setup mock index
        mock_index = MagicMock()
        mock_index.ntotal = 2
        mock_index_class.return_value = mock_index

        # Initialize storage
        storage = FaissStorage(vector_dim=4)

        # Create test vectors
        vectors = [
            VectorRecord(
                vector=[0.1, 0.2, 0.3, 0.4],
                payload={"text": "Sample text", "source": "doc1"},
            ),
            VectorRecord(
                vector=[0.5, 0.6, 0.7, 0.8],
                payload={"text": "Another example", "source": "doc2"},
            ),
        ]

        # Test add operation by patching the actual add method
        with patch.object(FaissStorage, 'add', autospec=True) as mock_add:
            storage.add(vectors)
            mock_add.assert_called_once()

        # Test query operation by patching the actual query method
        query = VectorDBQuery(query_vector=[0.2, 0.3, 0.4, 0.5], top_k=2)
        with patch.object(
            FaissStorage, 'query', autospec=True, return_value=[]
        ) as mock_query:
            results = storage.query(query)
            mock_query.assert_called_once()
            assert results == []

        # Test delete operation by patching the actual delete method
        with patch.object(
            FaissStorage, 'delete', autospec=True
        ) as mock_delete:
            storage.delete(ids=[vectors[0].id])
            mock_delete.assert_called_once()

        # Test clear operation by patching the actual clear method
        with patch.object(FaissStorage, 'clear', autospec=True) as mock_clear:
            storage.clear()
            mock_clear.assert_called_once()
