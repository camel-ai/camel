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
from camel.storages import MilvusStorage, VectorDBQuery, VectorRecord

URL_AND_KEY = (
    "https://in03-971134166a4c2ec.api.gcp-us-west1.zillizcloud.com",
    "56d29e389a93a4137dfcdfd276d2e9656ee2f91774484c9ae8b1b47cbe724c4bcaa16d0ae"
    "35e079fc5081f80c59b462e35011a52")


def test_multiple_remote_clients() -> None:
    # Storage without collection name
    storage1 = MilvusStorage(
        vector_dim=4,
        url_and_api_key=URL_AND_KEY,
    )

    storage2 = MilvusStorage(
        vector_dim=4,
        url_and_api_key=URL_AND_KEY,
        collection_name="collection2",
    )

    # Add vectors to storage1
    vectors1 = [
        VectorRecord(vector=[0.1, 0.1, 0.1, 0.1], payload={"message": "text"}),
        VectorRecord(vector=[0.1, -0.1, -0.1, 0.1],
                     payload={"message": "text"}),
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
            payload={
                "message": "text",
                "number": 1
            },
        ),
    ]
    storage2.add(records=vectors2)

    # Query and check results from storage1
    query1 = VectorDBQuery(query_vector=[0.1, 0.2, 0.1, 0.1], top_k=1)
    result1 = storage1.query(query1)
    assert result1[0].record.id == vectors1[0].id

    # Query and check results from storage2
    query2 = VectorDBQuery(query_vector=[-0.1, 0.2, -0.1, 0.1], top_k=1)
    result2 = storage2.query(query2)
    assert result2[0].record.id == vectors2[0].id
    assert result2[0].record.payload == {"message": "text"}

    # Delect vector in storage2
    storage2.delete([vectors2[0].id])
    result3 = storage2.query(query2)
    assert result3[0].record.id == vectors2[1].id

    # Clear and check status for each storage
    storage1.clear()
    status1 = storage1.status()
    assert status1.vector_count == 0
    storage1.clear()

    storage2.clear()
    status2 = storage2.status()
    assert status2.vector_count == 0
    storage2.clear()
