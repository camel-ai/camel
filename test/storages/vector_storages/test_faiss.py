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

import pytest

from camel.storages.vectordb_storages import (
    FaissStorage,
    VectorDBQuery,
    VectorRecord,
)


@pytest.fixture
def faiss_storage():
    """Fixture to create a temporary FaissStorage instance."""
    storage = FaissStorage(vector_dim=4, index_type="IndexFlatL2")
    yield storage
    storage.clear()


def test_add_and_query_vectors(faiss_storage):
    """Test adding and querying vectors in FAISS storage."""
    vectors = [
        VectorRecord(vector=[0.2, 0.2, 0.2, 0.2], payload={"label": "A"}),
        VectorRecord(vector=[-0.2, -0.2, -0.2, -0.2], payload={"label": "B"}),
    ]
    faiss_storage.add(records=vectors)

    assert faiss_storage.status().vector_count == 2

    query = VectorDBQuery(query_vector=[0.2, 0.2, 0.2, 0.2], top_k=1)
    result = faiss_storage.query(query)

    assert len(result) == 1
    assert result[0].record.payload["label"] == "A"


def test_query_multiple_neighbors(faiss_storage):
    """Test querying for multiple nearest neighbors."""
    vectors = [
        VectorRecord(vector=[1.0, 1.0, 1.0, 1.0], payload={"label": "X"}),
        VectorRecord(vector=[-1.0, -1.0, -1.0, -1.0], payload={"label": "Y"}),
        VectorRecord(vector=[0.5, 0.5, 0.5, 0.5], payload={"label": "Z"}),
    ]
    faiss_storage.add(records=vectors)

    query = VectorDBQuery(query_vector=[0.6, 0.6, 0.6, 0.6], top_k=2)
    result = faiss_storage.query(query)

    assert len(result) == 2
    assert result[0].record.payload["label"] in ["X", "Z"]
    assert result[1].record.payload["label"] in ["X", "Z"]


def test_delete_vectors(faiss_storage):
    """Test deleting vectors from FAISS storage."""
    vector1 = VectorRecord(vector=[0.3, 0.3, 0.3, 0.3], payload={"label": "A"})
    vector2 = VectorRecord(
        vector=[-0.3, -0.3, -0.3, -0.3], payload={"label": "B"}
    )

    faiss_storage.add(records=[vector1, vector2])

    faiss_storage.delete(ids=[vector1.id])

    assert faiss_storage.status().vector_count == 1

    query = VectorDBQuery(query_vector=[0.3, 0.3, 0.3, 0.3], top_k=1)
    result = faiss_storage.query(query)

    assert len(result) == 1
    assert result[0].record.payload["label"] == "B"


def test_clear_storage(faiss_storage):
    """Test clearing all vectors from FAISS storage."""
    vector1 = VectorRecord(vector=[0.7, 0.7, 0.7, 0.7])
    vector2 = VectorRecord(vector=[-0.7, -0.7, -0.7, -0.7])

    faiss_storage.add(records=[vector1, vector2])

    faiss_storage.clear()

    assert faiss_storage.status().vector_count == 0


def test_invalid_query(faiss_storage):
    """Test querying when no vectors are present."""
    query = VectorDBQuery(query_vector=[0.1, 0.1, 0.1, 0.1], top_k=1)
    result = faiss_storage.query(query)

    assert len(result) == 0


def test_invalid_index_type():
    """Test error handling for unsupported FAISS index types."""
    with pytest.raises(ValueError, match="Unsupported FAISS index type"):
        FaissStorage(vector_dim=4, index_type="InvalidIndex")


def test_gpu_throws_exception():
    """Test that using GPU raises an exception."""
    with pytest.raises(ValueError):
        FaissStorage(vector_dim=4, use_gpu=True)
