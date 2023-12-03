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
from unittest.mock import MagicMock

import pytest

from camel.storages import QdrantStorage, VectorDBQuery, VectorRecord

parametrize = pytest.mark.parametrize(
    "storage",
    ["built-in", "local"],
    indirect=True,
)


@pytest.fixture()
def storage(request):
    if request.param == "built-in":
        yield QdrantStorage(vector_dim=4, create_collection=True)
    elif request.param == "local":
        tmpdir = tempfile.mkdtemp()
        yield QdrantStorage(vector_dim=4, path=tmpdir, create_collection=True)
        shutil.rmtree(tmpdir)


@parametrize
def test_qdrant_storage(storage: QdrantStorage) -> None:
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

    query = VectorDBQuery(query_vector=[1, 1, 1, 1], top_k=2)
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


@pytest.fixture
def qdrant_storage():
    storage = QdrantStorage(vector_dim=4)
    storage._client = MagicMock()  # Mock the client
    return storage


def test_validate_vector_dimensions(qdrant_storage):
    # Test with valid dimensions
    vectors = [VectorRecord(vector=[0.1, 0.1, 0.1, 0.1])]
    qdrant_storage.validate_vector_dimensions(vectors)  # Should not raise

    # Test with invalid dimensions
    with pytest.raises(ValueError):
        invalid_vectors = [VectorRecord(vector=[0.1, 0.1])]
        qdrant_storage.validate_vector_dimensions(invalid_vectors)
