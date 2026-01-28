# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

import random

from sqlalchemy import text

from camel.storages.vectordb_storages import (
    OceanBaseStorage,
    VectorDBQuery,
    VectorRecord,
)

"""
Before running this example, you need to setup an OceanBase instance:

(Option 1): OceanBase Community Edition (OCE):

1. Download and install OCE from the official website:
   https://www.oceanbase.com/docs/oceanbase-database-cn

2. Start the OceanBase server and create a database user

3. Install PyOBVector package:
   pip install pyobvector

(Option 2): OceanBase Cloud Service:

1. Sign up for OceanBase Cloud Service

2. Create a cluster with OceanBase Vector enabled

3. Get your connection parameters from the service console

The connection parameters should include:
- URI: hostname:port
- User: username@tenant
- Password: your_password
- Database name: database_name
"""

# Replace these with your OceanBase connection parameters
OB_URI = "127.0.0.1:2881"
OB_USER = "root@sys"
OB_PASSWORD = ""
OB_DB_NAME = "oceanbase"


def main():
    # Create an instance of OceanBaseStorage with dimension = 64
    ob_storage = OceanBaseStorage(
        vector_dim=4,
        table_name="my_ob_vector_table",
        uri=OB_URI,
        user=OB_USER,
        password=OB_PASSWORD,
        db_name=OB_DB_NAME,
        distance="cosine",
    )

    # Get database status
    status = ob_storage.status()
    print(f"Vector dimension: {status.vector_dim}")
    print(f"Initial vector count: {status.vector_count}")

    # Generate and add a larger number of vectors using batching
    print("\nAdding vectors in batches...")
    random.seed(20241023)

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
    ob_storage.add(large_batch, batch_size=100)

    # Check updated status
    status = ob_storage.status()
    print(f"Vector count after adding batch: {status.vector_count}")

    # Generate a query vector and search for similar vectors
    print("\nQuerying similar vectors...")
    query_vector = [random.uniform(-1, 1) for _ in range(4)]
    query_results = ob_storage.query(
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
    ob_storage.clear()
    status = ob_storage.status()
    print(f"Vector count after clearing: {status.vector_count}")


def example_filtered_query():
    """Example demonstrating filtered ANN query using where_clause.

    This example shows how to use the where_clause parameter to filter
    results based on metadata using SQLAlchemy expressions.
    """
    print("\n" + "=" * 70)
    print("FILTERED ANN QUERY EXAMPLE")
    print("=" * 70)

    # Create storage with cosine distance
    ob_storage = OceanBaseStorage(
        vector_dim=4,
        table_name="filtered_query_example",
        uri=OB_URI,
        user=OB_USER,
        password=OB_PASSWORD,
        db_name=OB_DB_NAME,
        distance="cosine",
        delete_table_on_del=True,  # Auto-cleanup
    )

    # Add vectors with different categories in metadata
    random.seed(42)
    records = []
    categories = ["electronics", "clothing", "books", "electronics", "books"]
    prices = [199, 49, 25, 599, 15]

    for i, (category, price) in enumerate(zip(categories, prices)):
        records.append(
            VectorRecord(
                vector=[random.uniform(-1, 1) for _ in range(4)],
                payload={
                    "item_id": i,
                    "category": category,
                    "price": price,
                },
            )
        )

    ob_storage.add(records)
    print(f"Added {len(records)} records with categories: {categories}")

    # Query without filter - returns all matching results
    query_vector = records[0].vector
    print("\n1. Query WITHOUT filter:")
    results = ob_storage.query(
        VectorDBQuery(query_vector=query_vector, top_k=5)
    )
    for r in results:
        print(f"   - {r.record.payload}")

    # Query with category filter using where_clause
    print("\n2. Query WITH category filter (electronics only):")
    results = ob_storage.query(
        VectorDBQuery(query_vector=query_vector, top_k=5),
        where_clause=[text("metadata->>'$.category' = 'electronics'")],
    )
    for r in results:
        print(f"   - {r.record.payload}")

    # Query with price filter
    print("\n3. Query WITH price filter (price < 100):")
    results = ob_storage.query(
        VectorDBQuery(query_vector=query_vector, top_k=5),
        where_clause=[text("CAST(metadata->>'$.price' AS SIGNED) < 100")],
    )
    for r in results:
        print(f"   - {r.record.payload}")

    # Query with multiple conditions (AND)
    print("\n4. Query WITH multiple conditions (books AND price<30):")
    results = ob_storage.query(
        VectorDBQuery(query_vector=query_vector, top_k=5),
        where_clause=[
            text("metadata->>'$.category' = 'books'"),
            text("CAST(metadata->>'$.price' AS SIGNED) < 30"),
        ],
    )
    for r in results:
        print(f"   - {r.record.payload}")

    print("\nFiltered query example completed.")


def example_distance_metrics():
    """Example demonstrating different distance metrics.

    OceanBase supports four distance metrics:
    - l2: Euclidean distance (lower = more similar)
    - cosine: Cosine distance (lower = more similar)
    - inner_product: Inner product (higher = more similar)
    - negative_inner_product: Negative inner product (lower = more similar)
    """
    print("\n" + "=" * 70)
    print("DISTANCE METRICS EXAMPLE")
    print("=" * 70)

    random.seed(123)
    test_vector = [0.5, 0.5, 0.5, 0.5]

    for distance_metric in [
        "l2",
        "cosine",
        "inner_product",
        "negative_inner_product",
    ]:
        print(f"\n--- Distance metric: {distance_metric} ---")

        ob_storage = OceanBaseStorage(
            vector_dim=4,
            table_name=f"distance_example_{distance_metric}",
            uri=OB_URI,
            user=OB_USER,
            password=OB_PASSWORD,
            db_name=OB_DB_NAME,
            distance=distance_metric,
            delete_table_on_del=True,
        )

        # Add some test vectors
        records = [
            VectorRecord(
                vector=[1.0, 0.0, 0.0, 0.0], payload={"name": "unit_x"}
            ),
            VectorRecord(
                vector=[0.0, 1.0, 0.0, 0.0], payload={"name": "unit_y"}
            ),
            VectorRecord(
                vector=[0.5, 0.5, 0.5, 0.5], payload={"name": "same_as_query"}
            ),
            VectorRecord(
                vector=[-0.5, -0.5, -0.5, -0.5], payload={"name": "opposite"}
            ),
        ]
        ob_storage.add(records)

        # Query and show results
        results = ob_storage.query(
            VectorDBQuery(query_vector=test_vector, top_k=4)
        )

        print(f"  Query vector: {test_vector}")
        print("  Results (ordered by similarity):")
        for i, r in enumerate(results):
            name = r.record.payload['name']
            print(f"    {i + 1}. {name}: sim={r.similarity:.4f}")

    print("\nDistance metrics example completed.")


if __name__ == "__main__":
    main()
    # Uncomment to run additional examples:
    # example_filtered_query()
    # example_distance_metrics()

'''
===============================================================================
Vector dimension: 4
Initial vector count: 0

Adding vectors in batches...
Vector count after adding batch: 1000

Querying similar vectors...
Result 1:
  ID: f33f008d-688a-468a-9a2d-e005d27ad9d8
  Payload: {'idx': 496, 'batch': 'example'}
  Similarity: 0.9847431876706196
Result 2:
  ID: 0946ca4a-9129-4343-b339-b2f13a64c827
  Payload: {'idx': 306, 'batch': 'example'}
  Similarity: 0.9598140307734809
Result 3:
  ID: e2505cc3-7bee-433e-a723-c830b9404f61
  Payload: {'idx': 654, 'batch': 'example'}
  Similarity: 0.9548076959468635
Result 4:
  ID: 8d6359ff-49fd-4fb7-99fd-bf4ca0a0cdcc
  Payload: {'idx': 914, 'batch': 'example'}
  Similarity: 0.9496165658207311
Result 5:
  ID: 45cef390-3e1f-4e16-8375-b4108951a93b
  Payload: {'idx': 806, 'batch': 'example'}
  Similarity: 0.9485824622759768

Clearing vectors...
Vector count after clearing: 0
===============================================================================
'''
