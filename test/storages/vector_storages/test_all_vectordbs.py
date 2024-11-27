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

from camel.storages import (
    BaseVectorStorage,
    QdrantStorage,
    VectorDBQuery,
    VectorRecord,
)

parametrize = pytest.mark.parametrize(
    "storage",
    ["qdrant:built-in", "qdrant:local"],
    indirect=True,
)


@pytest.fixture()
def storage(request):
    params = request.param.split(":")
    if params[0] == "qdrant":
        if params[1] == "built-in":
            yield QdrantStorage(vector_dim=4)
        elif params[1] == "local":
            tmpdir = tempfile.mkdtemp()
            yield QdrantStorage(
                vector_dim=4,
                path=tmpdir,
            )
            shutil.rmtree(tmpdir)


@parametrize
def test_vector_storage(storage: BaseVectorStorage) -> None:
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
                "number": 1,
            },
        ),
    ]
    storage.add(records=vectors)

    status = storage.status()
    assert status.vector_count == 4
    assert status.vector_dim == 4

    query = VectorDBQuery(query_vector=[1.0, 1.0, 1.0, 1.0], top_k=2)
    result = storage.query(query)
    assert result[0].record.id == vectors[0].id
    assert result[1].record.id == vectors[3].id
    assert result[1].record.payload == {"message": "text", "number": 1}
    assert result[0].similarity > result[1].similarity

    storage.delete(ids=[vectors[1].id, vectors[3].id])
    result = storage.query(query)
    assert result[0].record.id == vectors[0].id
    assert result[1].record.id == vectors[2].id
    assert result[1].record.payload == {"message": "text"}
    assert result[0].similarity > result[1].similarity

    status = storage.status()
    assert status.vector_count == 2
    assert status.vector_dim == 4


@parametrize
def test_get_payload_by_vector(storage: BaseVectorStorage):
    vectors = [
        VectorRecord(
            vector=[-0.1, 0.1, -0.1, 0.1],
            payload={"order": 1},
        ),
        VectorRecord(
            vector=[-0.1, 0.1, 0.1, 0.1],
            payload={"order": 2},
        ),
        VectorRecord(
            vector=[0.1, 0.1, 0.1, 0.1],
            payload={"order": 3},
        ),
    ]
    storage.add(vectors)
    payloads = storage.get_payloads_by_vector([1.0, 1.0, 1.0, 1.0], top_k=2)
    assert payloads[0] == {"order": 3}
    assert payloads[1] == {"order": 2}
