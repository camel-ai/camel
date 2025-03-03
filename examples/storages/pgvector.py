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

from camel.storages.vectordb_storages import (
    PgVectorStorage,
    PgVectorDistance,
    VectorDBQuery,
    VectorRecord,
)

connection_params = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'postgres',
    'user': 'postgres',   
    'password': 'postgres'   
}

vector_storage = PgVectorStorage(
    vector_dim=3,
    connection_params=connection_params,
    collection_name='example_vectors',
    distance=PgVectorDistance.COSINE,
)

vectors = [
    VectorRecord(
        vector=[1.0, 0.0, 0.0],
        payload={"label": "X", "description": "X axis direction"}
    ),
    VectorRecord(
        vector=[0.0, 1.0, 0.0],
        payload={"label": "Y", "description": "Y axis direction"}
    ),
    VectorRecord(
        vector=[0.0, 0.0, 1.0],
        payload={"label": "Z", "description": "Z axis direction"}
    ),
]

print("Adding vectors...")
vector_storage.add(records=vectors)

status = vector_storage.status()
print(f"Current status: {status.vector_count} vectors stored")
print(f"Vector dimension: {status.vector_dim}")

query = VectorDBQuery(
    query_vector=[1.0, 0.0, 0.0],
    top_k=3
)
results = vector_storage.query(query)

print("\nQuery results:")
for result in results:
    print(f"Label: {result.record.payload['label']}")
    print(f"Similarity: {result.similarity:.3f}")
    print(f"Description: {result.record.payload['description']}")
    print()

print("Clearing collection...")
vector_storage.clear()