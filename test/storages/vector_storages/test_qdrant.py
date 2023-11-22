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

import pytest

from camel.storages import QdrantStorage, VectorDBQuery, VectorRecord

parametrize = pytest.mark.parametrize(
    "server",
    ["built-in", "local"],
    indirect=True,
)


@pytest.fixture()
def server(request):
    if request.param == "built-in":
        yield QdrantStorage(vector_dim=4)
    elif request.param == "local":
        tmpdir = tempfile.mkdtemp()
        yield QdrantStorage(vector_dim=4, path=tmpdir)
        shutil.rmtree(tmpdir)


@parametrize
def test_qdrant_storage(server: QdrantStorage) -> None:
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
    server.add(records=vectors)

    query = VectorDBQuery(query_vector=[1, 1, 1, 1], top_k=2)
    result = server.query(query)
    assert result[0].record.id == vectors[0].id
    assert result[1].record.id == vectors[3].id
    assert result[1].record.payload == {"message": "text", "number": 1}
    assert result[0].similarity > result[1].similarity

    server.delete(ids=[vectors[1].id, vectors[3].id])
    result = server.query(query)
    assert result[0].record.id == vectors[0].id
    assert result[1].record.id == vectors[2].id
    assert result[1].record.payload == {"message": "text"}
    assert result[0].similarity > result[1].similarity
