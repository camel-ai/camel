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

from camel.storages import QdrantStorage, VectorDBQuery, VectorRecord


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
