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

"""
Before running this example, you need to setup a PostgreSQL instance with 
the pgvector extension:

1. Install PostgreSQL and pgvector extension:
   https://github.com/pgvector/pgvector#installation

2. Create a database and enable the extension:
   CREATE EXTENSION IF NOT EXISTS vector;

3. Install required Python packages:
   pip install psycopg[binary] pgvector psycopg-binary

The connection parameters should include:
- host
- port
- user
- password
- dbname
"""

# Replace these with your PostgreSQL connection parameters
PG_CONN_INFO = {
    "host": "127.0.0.1",
    "port": 5432,
    "user": "postgres",
    "password": "postgres",
    "dbname": "postgres",
}


def main():
    # Create an instance of PgVectorStorage with dimension = 4
    pg_storage = PgVectorStorage(
        vector_dim=4,
        conn_info=PG_CONN_INFO,
        table_name="my_pgvector_table",
        # distance can be omitted for default (cosine)
    )

    # Get database status
    status = pg_storage.status()
    print(f"Vector dimension: {status.vector_dim}")
    print(f"Initial vector count: {status.vector_count}")

    # Generate and add a larger number of vectors using batching
    print("\nAdding vectors in batches...")
    random.seed(20240624)

    # Create a large batch of vector records
    large_batch = []
    for i in range(1000):
        large_batch.append(
            VectorRecord(
                vector=[random.uniform(-1, 1) for _ in range(4)],
                payload={'idx': i, 'batch': 'example'},
            )
        )

    # Add vectors with automatic batching (batch_size=100)
    pg_storage.add(large_batch)

    # Check updated status
    status = pg_storage.status()
    print(f"Vector count after adding batch: {status.vector_count}")

    # Generate a query vector and search for similar vectors
    print("\nQuerying similar vectors...")
    query_vector = [random.uniform(-1, 1) for _ in range(4)]
    query_results = pg_storage.query(
        VectorDBQuery(query_vector=query_vector, top_k=5)
    )

    # Display results
    for i, result in enumerate(query_results):
        print(f"Result {i+1}:")
        print(f"  ID: {result.record.id}")
        print(f"  Payload: {result.record.payload}")
        print(f"  Similarity: {result.similarity}")

    # Clear all vectors when done
    print("\nClearing vectors...")
    pg_storage.clear()
    status = pg_storage.status()
    print(f"Vector count after clearing: {status.vector_count}")


if __name__ == "__main__":
    main()
