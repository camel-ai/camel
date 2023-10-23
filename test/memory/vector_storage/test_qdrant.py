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

import pytest

from camel.memory.vector_storage import Qdrant, VectorRecord
from camel.typing import VectorDistance


@pytest.fixture()
def server(request):
    if request.param == "built-in":
        return Qdrant()


@pytest.mark.parametrize("server", ["built-in"], indirect=True)
def test_create_delete_collection(server: Qdrant):
    collection_name = "test_collection"
    server.create_collection(collection=collection_name, size=4)
    server.delete_collection(collection=collection_name)


@pytest.mark.parametrize("server", ["built-in"], indirect=True)
def test_add_delete_vector(server: Qdrant):
    vectors = [
        VectorRecord(id=1, vector=[0.1, 0.1, 0.1, 0.1]),
        VectorRecord(id=2, vector=[0.1, -0.1, -0.1, 0.1]),
        VectorRecord(
            id=3,
            vector=[-0.1, 0.1, -0.1, 0.1],
            payload={"message": "text"},
        ),
        VectorRecord(
            id=4,
            vector=[-0.1, 0.1, 0.1, 0.1],
            payload={
                "message": "text",
                "number": 1,
            },
        ),
    ]
    collection_name = "test_collection"
    server.create_collection(
        collection=collection_name,
        size=4,
        distance=VectorDistance.DOT,
    )
    server.add_vectors(collection=collection_name, vectors=vectors)

    query_vector = VectorRecord(vector=[1, 1, 1, 1])
    result = server.search(
        collection=collection_name,
        query_vector=query_vector,
        limit=2,
    )
    assert result[0].id == 1
    assert result[1].id == 4
    assert result[1].payload == {"message": "text", "number": 1}

    server.delete_vectors(
        collection=collection_name,
        vectors=[vectors[1], vectors[3]],
    )
    result = server.search(
        collection=collection_name,
        query_vector=query_vector,
        limit=2,
    )
    assert result[0].id == 1
    assert result[1].id == 3
    assert result[1].payload == {"message": "text"}

    server.delete_collection(collection=collection_name)


@pytest.mark.parametrize("server", ["built-in"], indirect=True)
def test_add_delete_vector_without_id(server: Qdrant):
    vectors = [
        VectorRecord(vector=[0.1, 0.1, 0.1, 0.1]),
        VectorRecord(vector=[0.1, -0.1, -0.1, 0.1]),
        VectorRecord(
            vector=[-0.1, 0.1, -0.1, 0.1],
            payload={"message": "text"},
        ),
        VectorRecord(
            vector=[-0.1, 0.1, 0.1, 0.1],
            payload={
                "message": "text",
                "number": 1
            },
        ),
    ]
    collection_name = "test_collection"
    server.create_collection(
        collection=collection_name,
        size=4,
        distance=VectorDistance.DOT,
    )
    add_vectors_rnt = server.add_vectors(
        collection=collection_name,
        vectors=vectors,
    )
    assert len(add_vectors_rnt) == 4
    for v in add_vectors_rnt:
        assert v.id is not None

    query_vector = VectorRecord(vector=[1, 1, 1, 1])
    result = server.search(collection=collection_name,
                           query_vector=query_vector, limit=2)
    assert result[0].id == add_vectors_rnt[0].id
    assert result[1].id == add_vectors_rnt[3].id
    assert result[1].payload == {"message": "text", "number": 1}

    delete_vectors_rnt = server.delete_vectors(
        collection=collection_name,
        vectors=[vectors[1], vectors[3]],
    )
    assert len(delete_vectors_rnt) == 2
    for v in delete_vectors_rnt:
        assert v.id is not None

    result = server.search(collection=collection_name,
                           query_vector=query_vector, limit=2)
    assert result[0].id == add_vectors_rnt[0].id
    assert result[1].id == add_vectors_rnt[2].id
    assert result[1].payload == {"message": "text"}

    server.delete_collection(collection=collection_name)
