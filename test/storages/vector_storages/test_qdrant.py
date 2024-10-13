# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

import shutil
import tempfile
import uuid

from camel.storages import (
    QdrantManager,
    QdrantStorage,
    VectorDBQuery,
    VectorRecord,
)


def test_multiple_local_clients() -> None:
    tmpdir = tempfile.mkdtemp()
    storage1 = QdrantStorage(
        vector_dim=4,
        path=tmpdir,
        collection_name="collection1",
        delete_collection_on_del=True,
    )
    storage2 = QdrantStorage(
        vector_dim=4,
        path=tmpdir,
        collection_name="collection2",
        delete_collection_on_del=True,
    )

    # Add vectors to storage1
    vectors1 = [
        VectorRecord(vector=[0.1, 0.1, 0.1, 0.1]),
        VectorRecord(vector=[0.1, -0.1, -0.1, 0.1]),
    ]
    storage1.add(records=vectors1)

    # Add vectors to storage2
    vectors2 = [
        VectorRecord(
            vector=[-0.1, 0.1, -0.1, 0.1],
            payload={"message": "text"},
        ),
        VectorRecord(
            vector=[-0.1, 0.1, 0.1, 0.1],
            payload={"message": "text", "number": 1},
        ),
    ]
    storage2.add(records=vectors2)

    # Query and check results from storage1
    query1 = VectorDBQuery(query_vector=[1.0, 1.0, 1.0, 1.0], top_k=1)
    result1 = storage1.query(query1)
    assert result1[0].record.id == vectors1[0].id

    # Query and check results from storage2
    query2 = VectorDBQuery(query_vector=[-1.0, 1.0, -1.0, 1.0], top_k=1)
    result2 = storage2.query(query2)
    assert result2[0].record.id == vectors2[0].id
    assert result2[0].record.payload == {"message": "text"}

    # Clear and check status for each storage
    storage1.clear()
    status1 = storage1.status()
    assert status1.vector_count == 0

    storage2.clear()
    status2 = storage2.status()
    assert status2.vector_count == 0

    storage1.close_client()
    storage2.close_client()

    shutil.rmtree(tmpdir)


def test_existing_collection():
    tmpdir = tempfile.mkdtemp()
    storage = QdrantStorage(
        vector_dim=4,
        path=tmpdir,
        collection_name="test_collection",
    )
    vectors = [
        VectorRecord(vector=[0.1, 0.1, 0.1, 0.1]),
        VectorRecord(vector=[0.1, -0.1, -0.1, 0.1]),
    ]
    storage.add(records=vectors)
    assert storage.status().vector_count == 2

    storage2 = QdrantStorage(
        vector_dim=4,
        path=tmpdir,
        collection_name="test_collection",
    )
    assert storage2.status().vector_count == 2


def test_points_crud():
    tmpdir = tempfile.mkdtemp()
    collection_name = "test_collection"
    manager = QdrantManager(path=tmpdir)

    if manager.collection_exists(collection_name):
        manager.delete_collection(collection_name)

    storage = QdrantStorage(
        vector_dim=4,
        path=tmpdir,
        collection_name=collection_name,
    )

    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    id3 = str(uuid.uuid4())

    vector1 = [0.1, 0.1, 0.1, 0.1]
    vector2 = [0.1, -0.1, -0.1, 0.1]
    vector3 = [-0.1, -0.1, 0.1, 0.1]

    normalized_v1 = [0.5, 0.5, 0.5, 0.5]
    normalized_v2 = [0.5, -0.5, -0.5, 0.5]
    normalized_v3 = [-0.5, -0.5, 0.5, 0.5]

    payload1 = {"test": "value"}
    payload2 = {"test1": "value1"}
    payload3 = {"test2": "value2", "test3": "value3"}

    # Add vectors
    records = [
        VectorRecord(id=id1, vector=vector1, payload=payload1),
    ]

    storage.add(records=records)
    assert storage.status().vector_count == 1

    records1 = [
        VectorRecord(id=id2, vector=vector2, payload=payload2),
        VectorRecord(id=id3, vector=vector3, payload=payload3),
    ]
    storage.add(records=records1)
    assert storage.status().vector_count == 3

    # Query and check results
    query1 = VectorDBQuery(query_vector=vector1, top_k=1)
    result1 = storage.query(query1)
    assert result1[0].record.id == id1
    assert result1[0].record.vector == normalized_v1

    query2 = VectorDBQuery(query_vector=vector2, top_k=1)
    result2 = storage.query(query2)
    assert result2[0].record.id == id2
    assert result2[0].record.vector == normalized_v2

    query3 = VectorDBQuery(query_vector=vector3, top_k=1)
    result3 = storage.query(query3)
    assert result3[0].record.id == id3
    assert result3[0].record.vector == normalized_v3

    # Query by payload
    query4 = VectorDBQuery(
        query_vector=vector1,
        top_k=1,
        filter={"must": [{"key": "test", "match": {"value": "value"}}]},
    )
    result4 = storage.query(query4)
    assert len(result4) == 1
    assert result4[0].record.id == id1
    assert result4[0].record.vector == normalized_v1

    query5 = VectorDBQuery(
        query_vector=vector3,
        top_k=1,
        filter={"must": [{"key": "test", "match": {"value": "value"}}]},
    )
    result5 = storage.query(query5)
    assert len(result5) == 1
    assert result5[0].record.id == id1
    assert result5[0].record.vector == normalized_v1

    # Update vector
    i = id1
    v = [0.1, 0.5, 0.1, 0.1]
    nv = [
        0.18898224830627441,
        0.9449112415313721,
        0.18898224830627441,
        0.18898224830627441,
    ]
    p = {"test": "value2"}
    update_vector = VectorRecord(id=i, vector=v, payload=p)
    storage.update(records=[update_vector])

    query6 = VectorDBQuery(query_vector=v, top_k=1)
    result6 = storage.query(query6)
    assert len(result6) == 1
    assert result6[0].record.id == id1
    assert result6[0].record.vector == nv
    assert result6[0].record.payload == p

    i1 = id2
    v1 = [0.1, -0.5, -0.1, 0.1]
    p1 = {"test1": "value2"}
    update_vector = VectorRecord(id=i1, vector=v1, payload=p1)
    storage.update(records=[update_vector], only_payload=True)

    query7 = VectorDBQuery(query_vector=v1, top_k=1)
    result7 = storage.query(query7)
    assert len(result7) == 1
    assert result7[0].record.id == id2
    assert result7[0].record.vector == normalized_v2
    assert result7[0].record.payload == p1

    query8 = VectorDBQuery(query_vector=vector2, top_k=1)
    result8 = storage.query(query8)
    assert len(result8) == 1
    assert result8[0].record.id == id2
    assert result8[0].record.vector == normalized_v2
    assert result8[0].record.payload == p1

    # Delete vector
    storage.delete(ids=[id1])
    assert storage.status().vector_count == 2

    storage.delete(ids=[id2, id3])
    assert storage.status().vector_count == 0

    manager.delete_collection(collection_name=storage.collection_name)
