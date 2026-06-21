# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

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


def test_context_manager():
    """QdrantStorage can be used as a context manager.  Data added inside the
    ``with`` block is accessible via a second instance that shares the same
    underlying client (Issue #1658 — same-process scenario)."""
    tmpdir = tempfile.mkdtemp()
    try:
        collection_name = "test_ctx_manager"
        vector = VectorRecord(vector=[1.0, 0.0, 0.0, 0.0], payload={"k": "v"})

        with QdrantStorage(
            vector_dim=4,
            path=tmpdir,
            collection_name=collection_name,
        ) as storage:
            storage.add(records=[vector])
            assert storage.status().vector_count == 1

            # A second instance opened inside the same context shares the
            # underlying client via _qdrant_local_client_map and must see
            # the data immediately (Issue #1658).
            storage2 = QdrantStorage(
                vector_dim=4,
                path=tmpdir,
                collection_name=collection_name,
            )
            try:
                assert storage2.status().vector_count == 1
                result = storage2.query(
                    VectorDBQuery(query_vector=[1.0, 0.0, 0.0, 0.0], top_k=1)
                )
                assert len(result) == 1
                assert result[0].record.payload["k"] == "v"
            finally:
                storage2.delete_collection()
                # close_client() removes from map; the outer ``with`` block's
                # storage is also invalidated so we exit immediately.
                storage2.close_client()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_save_is_noop_and_data_shared_within_process():
    """save() is a no-op for Qdrant (WAL guarantees durability).  Within the
    same process, two QdrantStorage instances pointing to the same local path
    share one underlying client and see each other's writes immediately
    (Issue #1658 — same-process scenario)."""
    tmpdir = tempfile.mkdtemp()
    try:
        collection_name = "test_save_flush"
        records = [
            VectorRecord(vector=[0.5, 0.5, 0.5, 0.5], payload={"n": 1}),
            VectorRecord(vector=[-0.5, -0.5, -0.5, -0.5], payload={"n": 2}),
        ]

        storage1 = QdrantStorage(
            vector_dim=4,
            path=tmpdir,
            collection_name=collection_name,
        )
        storage1.add(records=records)
        storage1.save()  # no-op for Qdrant, must not raise

        # Within the same process a second instance shares the client via
        # _qdrant_local_client_map and must see the data immediately.
        storage2 = QdrantStorage(
            vector_dim=4,
            path=tmpdir,
            collection_name=collection_name,
        )
        try:
            assert storage2.status().vector_count == 2
            result = storage2.query(
                VectorDBQuery(query_vector=[0.5, 0.5, 0.5, 0.5], top_k=2)
            )
            assert len(result) == 2
        finally:
            storage2.delete_collection()
            storage2.close_client()
        storage1.close_client()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_points_count_none_treated_as_zero():
    """vector_count must never be None — it should fall back to 0 so that
    the AutoRetriever ``== 0`` check behaves correctly (Issue #1658)."""
    tmpdir = tempfile.mkdtemp()
    try:
        storage = QdrantStorage(
            vector_dim=4,
            path=tmpdir,
            collection_name="test_count_none",
        )
        # A freshly created, empty collection must report 0, not None.
        assert storage.status().vector_count == 0
        storage.delete_collection()
        storage.close_client()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
