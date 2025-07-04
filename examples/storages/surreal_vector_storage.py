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
import os

from camel.storages.vectordb_storages import (
    SurrealStorage,
    VectorDBQuery,
    VectorRecord,
)


def main():
    url = os.getenv("SURREAL_URL", "ws://localhost:8000/rpc")
    table = os.getenv("SURREAL_TABLE", "tb")
    vector_dim = int(os.getenv("SURREAL_VECTOR_DIM", 4))
    namespace = os.getenv("SURREAL_NAMESPACE", "ns")
    database = os.getenv("SURREAL_DATABASE", "db")
    user = os.getenv("SURREAL_USER", "user")
    password = os.getenv("SURREAL_PASSWORD")

    # Raise an error if password is not set
    if not password:
        raise ValueError(
            "Environment variable SURREAL_PASSWORD is not set. "
            "Please set it before running."
        )

    # Initialize the SurrealStorage instance with provided parameters
    storage = SurrealStorage(
        url=url,
        table=table,
        namespace=namespace,
        database=database,
        user=user,
        password=password,
        vector_dim=vector_dim,
    )

    # Clear existing data in storage
    storage.clear()

    # Print the current status after clearing
    print("[Step 1] After clear:", storage.status())

    vec1 = VectorRecord(vector=[1, 2, 3, 4], payload={"name": "test_1"})
    vec2 = VectorRecord(vector=[5, 6, 7, 8], payload={"name": "test_2"})
    vec3 = VectorRecord(vector=[9, 10, 11, 12], payload={"name": "test_3"})
    vec4 = VectorRecord(vector=[13, 14, 15, 16], payload={"name": "test_4"})
    storage.add([vec1, vec2, vec3, vec4])
    print("[Step 2] After add:", storage.status())

    surreal_client = storage.client
    with surreal_client as db:
        db.signin({"username": user, "password": password})
        db.use(namespace, database)
        res = db.query_raw(
            "SELECT * FROM lyz_tb WHERE payload.name = 'test_3';"
        )["result"][0]["result"][0]["id"].id
        print("[Step 3] Query Result ID for 'test_3':", res)

    storage.delete(ids=[res])
    print("[Step 4] After delete 'test_3':", storage.status())

    res = storage.query(
        VectorDBQuery(query_vector=[1.1, 2.1, 3.1, 4.1], top_k=2)
    )
    print("[Step 5] Vector Query Result:", res)


if __name__ == "__main__":
    main()

"""
[Step 1] After clear: vector_dim=4 vector_count=0oceanbasech
[Step 2] After add: vector_dim=4 vector_count=4
[Step 3] Query Result ID for 'test_3': lov5h16x6uog7l2xtsqp
[Step 4] After delete 'test_3': vector_dim=4 vector_count=3
[Step 5] Vector Query Result: 
[VectorDBQueryResult(record=VectorRecord(vector=[], 
id='9803ae3a-18da-4152-a522-48e1939a3604', 
payload={'name': 'test_2'}), similarity=0.027665393972965968), 
VectorDBQueryResult(record=VectorRecord(vector=[], 
id='de3d085c-ed1b-4d23-9d12-d9fc64ae1e00', 
payload={'name': 'test_1'}), similarity=0.00010404203326297434)]

"""
