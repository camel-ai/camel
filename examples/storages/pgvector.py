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
import random

from camel.storages.vectordb_storages import (
    PgVectorStorage,
    VectorDBQuery,
    VectorRecord,
)

connection_params = {
    'host': 'localhost',
    'port': 5432,
    'dbname': 'postgres',
    'user': 'postgres',
    'password': 'postgres',
}

# First, let's demonstrate basic vector storage operations
vector_storage = PgVectorStorage(
    vector_dim=3,
    connection_params=connection_params,
    collection_name='example_vectors',
)

# Basic operations example with simple vectors
print("=== Basic Vector Operations ===")
basic_vectors = [
    VectorRecord(
        vector=[1.0, 0.0, 0.0],
        payload={"label": "X", "description": "X axis direction"},
    ),
    VectorRecord(
        vector=[0.0, 1.0, 0.0],
        payload={"label": "Y", "description": "Y axis direction"},
    ),
    VectorRecord(
        vector=[0.0, 0.0, 1.0],
        payload={"label": "Z", "description": "Z axis direction"},
    ),
]

print("Adding basic vectors...")
vector_storage.add(records=basic_vectors)

status = vector_storage.status()
print(f"Current status: {status.vector_count} vectors stored")
print(f"Vector dimension: {status.vector_dim}")

query = VectorDBQuery(query_vector=[1.0, 0.0, 0.0], top_k=3)
results = vector_storage.query(query)

print("\nBasic query results:")
for result in results:
    print(f"Label: {result.record.payload['label']}")
    print(f"Similarity: {result.similarity:.3f}")
    print(f"Description: {result.record.payload['description']}")
    print()

"""
==============================================================================
Adding vectors...
Current status: 3 vectors stored
Vector dimension: 3

Query results:
Label: X
Similarity: 1.000
Description: X axis direction

Label: Y
Similarity: 0.000
Description: Y axis direction

Label: Z
Similarity: 0.000
Description: Z axis direction

Clearing collection...
==============================================================================
"""

# Now, let's demonstrate index performance
print("\n=== Index Performance Comparison ===")


def run_query_benchmark(storage, query_vector, top_k=3, num_iterations=100):
    """Run a simple benchmark for query performance."""
    import time

    total_time = 0

    for _ in range(num_iterations):
        start = time.time()
        storage.query(VectorDBQuery(query_vector=query_vector, top_k=top_k))
        total_time += (time.time() - start) * 1000  # Convert to ms

    return total_time / num_iterations


# Generate test vectors for performance testing
num_vectors = 10000
test_vectors = []
for i in range(num_vectors):
    vec = [random.uniform(-1, 1) for _ in range(3)]
    magnitude = sum(x * x for x in vec) ** 0.5
    vec = [x / magnitude for x in vec]
    test_vectors.append(
        VectorRecord(
            vector=vec,
            payload={"id": i, "magnitude": magnitude},
        )
    )

# Clear previous data and add test vectors
print(f"\nAdding {num_vectors} test vectors...")
vector_storage.clear()
vector_storage.add(records=test_vectors)

# Test query performance without index
query_vector = [1.0, 0.0, 0.0]
print("\nTesting query performance without index...")
avg_time = run_query_benchmark(vector_storage, query_vector)
print(f"Average query time: {avg_time:.2f}ms")

# Test IVFFlat index
print("\nCreating IVFFlat index...")
vector_storage.create_index(
    vector_type='vector',
    index_type='ivfflat',
    lists=100,  # Number of clusters
)

print("Testing query performance with IVFFlat index...")
avg_time = run_query_benchmark(vector_storage, query_vector)
print(f"Average query time: {avg_time:.2f}ms")

# Test HNSW index
print("\nRecreating collection for HNSW index...")
vector_storage.clear()
vector_storage.add(records=test_vectors)

print("Creating HNSW index...")
vector_storage.create_index(
    vector_type='vector',
    index_type='hnsw',
    m=16,  # Max connections per node
    ef_construction=64,  # Build-time accuracy
)

print("Testing query performance with HNSW index...")
avg_time = run_query_benchmark(vector_storage, query_vector)
print(f"Average query time: {avg_time:.2f}ms")

# Show some example results
results = vector_storage.query(
    VectorDBQuery(query_vector=query_vector, top_k=3)
)
print("\nExample query results with HNSW index:")
for i, result in enumerate(results):
    print(f"Result {i+1}:")
    print(f"  Vector: [{', '.join(f'{x:.6f}' for x in result.record.vector)}]")
    print(f"  Similarity: {result.similarity:.6f}")
    print(f"  Metadata: {result.record.payload}")

# Clean up
print("\nClearing collection...")
vector_storage.clear()

"""
==============================================================================
=== Index Performance Comparison ===

Adding 10000 test vectors...

Testing query performance without index...
Average query time: 0.35ms

Creating IVFFlat index...
Testing query performance with IVFFlat index...
Average query time: 0.35ms

Recreating collection for HNSW index...
Creating HNSW index...
Testing query performance with HNSW index...
Average query time: 0.53ms

Example query results with HNSW index:
Result 1:
  Vector: [0.999339, -0.018321, 0.031409]
  Similarity: 0.999339
  Metadata: {'id': 7800, 'magnitude': 0.8722829235772224}
Result 2:
  Vector: [0.998916, 0.024585, 0.039516]
  Similarity: 0.998916
  Metadata: {'id': 5068, 'magnitude': 0.8936241220273847}
Result 3:
  Vector: [0.998708, -0.023935, 0.044833]
  Similarity: 0.998708
  Metadata: {'id': 1229, 'magnitude': 0.6710487272036939}

Clearing collection...
==============================================================================
"""
