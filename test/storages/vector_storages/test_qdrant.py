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

import shutil
import tempfile

import pytest

from camel.storages import QdrantStorage, VectorDBQuery, VectorRecord
from camel.types import VectorDistance


@pytest.fixture(scope="function")
def temp_storage():
    tmpdir = tempfile.mkdtemp()
    storage = QdrantStorage(
        vector_dim=4,
        path=tmpdir,
        collection_name="test_collection",
    )
    yield storage
    storage.delete_collection()
    storage.close_client()
    shutil.rmtree(tmpdir)


def test_add_and_query_vectors(temp_storage):
    vectors = [
        VectorRecord(vector=[0.2, 0.2, 0.2, 0.2], payload={"label": "A"}),
        VectorRecord(vector=[-0.2, -0.2, -0.2, -0.2], payload={"label": "B"}),
    ]
    temp_storage.add(records=vectors)

    assert temp_storage.status().vector_count == 2

    query = VectorDBQuery(query_vector=[0.2, 0.2, 0.2, 0.2], top_k=1)
    result = temp_storage.query(query)
    assert len(result) == 1
    assert result[0].record.payload["label"] == "A"


def test_query_with_filter(temp_storage):
    vector1 = VectorRecord(vector=[0.3, 0.3, 0.3, 0.3], payload={"label": "A"})
    vector2 = VectorRecord(
        vector=[-0.3, -0.3, -0.3, -0.3], payload={"label": "B"}
    )
    temp_storage.add(records=[vector1, vector2])

    query = VectorDBQuery(query_vector=[0.3, 0.3, 0.3, 0.3], top_k=2)
    result = temp_storage.query(query, filter_conditions={"label": "A"})
    assert len(result) == 1
    assert result[0].record.payload["label"] == "A"

    result2 = temp_storage.query(query, filter_conditions={"label": "B"})
    assert len(result2) == 1
    assert result2[0].record.payload["label"] == "B"


def test_update_payload(temp_storage):
    vector = VectorRecord(vector=[0.5, 0.5, 0.5, 0.5], payload={"label": "C"})
    temp_storage.add(records=[vector])

    temp_storage.update_payload(ids=[vector.id], payload={"label": "Updated"})
    query = VectorDBQuery(query_vector=[0.5, 0.5, 0.5, 0.5], top_k=1)
    result = temp_storage.query(query)
    assert result[0].record.payload["label"] == "Updated"

    # Verify original label is no longer present
    result2 = temp_storage.query(query, filter_conditions={"label": "C"})
    assert len(result2) == 0


def test_delete_vectors(temp_storage):
    vector1 = VectorRecord(vector=[0.6, 0.6, 0.6, 0.6], payload={"group": "X"})
    vector2 = VectorRecord(
        vector=[-0.6, -0.6, -0.6, -0.6], payload={"group": "Y"}
    )
    temp_storage.add(records=[vector1, vector2])

    temp_storage.delete(ids=[vector1.id])

    all_vectors = temp_storage.query(
        VectorDBQuery(query_vector=[0.0, 0.0, 0.0, 0.0], top_k=10)
    )
    assert all(v.record.id != vector1.id for v in all_vectors)

    temp_storage.delete(payload_filter={"group": "Y"})
    assert temp_storage.status().vector_count == 0


def test_clear_collection(temp_storage):
    vector1 = VectorRecord(vector=[1.0, 1.0, 1.0, 1.0])
    vector2 = VectorRecord(vector=[-1.0, -1.0, -1.0, -1.0])
    temp_storage.add(records=[vector1, vector2])

    temp_storage.clear()
    assert temp_storage.status().vector_count == 0


def test_different_distance_metrics():
    tmpdir = tempfile.mkdtemp()
    storage = QdrantStorage(
        vector_dim=4,
        path=tmpdir,
        collection_name="test_collection_distance_metric",
        distance=VectorDistance.EUCLIDEAN,
        delete_collection_on_del=True,
    )

    vector1 = VectorRecord(vector=[0.0, 0.0, 0.0, 0.0])
    vector2 = VectorRecord(vector=[1.0, 1.0, 1.0, 1.0])
    storage.add(records=[vector1, vector2])

    query = VectorDBQuery(query_vector=[0.1, 0.1, 0.1, 0.1], top_k=2)
    result = storage.query(query)
    assert result[0].record.id == vector1.id

    storage.close_client()
    shutil.rmtree(tmpdir)


def test_delete_collection(temp_storage):
    vectors = [
        VectorRecord(vector=[0.2, 0.2, 0.2, 0.2], payload={"label": "A"}),
        VectorRecord(vector=[-0.2, -0.2, -0.2, -0.2], payload={"label": "B"}),
    ]
    temp_storage.add(records=vectors)

    assert temp_storage.status().vector_count == 2

    temp_storage.delete_collection()

    assert not temp_storage.client.collection_exists(
        temp_storage.collection_name
    )
