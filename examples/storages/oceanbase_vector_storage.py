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
    print("\n=== Filtered ANN Query Example ===")

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
    print("\n=== Distance Metrics Example ===")

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


def example_arbitrary_distance_metrics():
    """Example with arbitrary vector values to demonstrate distance metrics."""
    print("\n=== Arbitrary Distance Metrics Example ===")

    # Arbitrary query vector
    query = [0.3, -0.7, 0.2, 0.8]

    # Various test vectors with different relationships to query
    records = [
        VectorRecord(
            vector=[0.3, -0.7, 0.2, 0.8], payload={"name": "exact_match"}
        ),
        VectorRecord(
            vector=[0.6, -1.4, 0.4, 1.6], payload={"name": "scaled_2x"}
        ),
        VectorRecord(
            vector=[0.1, -0.3, 0.1, 0.4], payload={"name": "similar_dir"}
        ),
        VectorRecord(
            vector=[-0.3, 0.7, -0.2, -0.8], payload={"name": "opposite"}
        ),
        VectorRecord(
            vector=[0.8, 0.2, -0.5, 0.1], payload={"name": "orthogonal"}
        ),
        VectorRecord(vector=[0.0, 0.0, 0.0, 1.0], payload={"name": "unit_w"}),
    ]

    for distance_metric in [
        "inner_product",
        "negative_inner_product",
        "cosine",
        "l2",
    ]:
        print(f"\n--- Distance metric: {distance_metric} ---")

        ob_storage = OceanBaseStorage(
            vector_dim=4,
            table_name=f"arbitrary_example_{distance_metric}",
            uri=OB_URI,
            user=OB_USER,
            password=OB_PASSWORD,
            db_name=OB_DB_NAME,
            distance=distance_metric,
            delete_table_on_del=True,
        )

        ob_storage.add(records)

        results = ob_storage.query(VectorDBQuery(query_vector=query, top_k=6))

        print(f"  Query: {query}")
        print("  Results:")
        for i, r in enumerate(results):
            name = r.record.payload['name']
            vec = r.record.vector
            print(f"    {i + 1}. {name}: sim={r.similarity:.4f}, vec={vec}")

    print("\nArbitrary distance metrics example completed.")


if __name__ == "__main__":
    main()
    # Uncomment to run additional examples:
    # example_filtered_query()
    # example_distance_metrics()
    # example_arbitrary_distance_metrics()

'''
===============================================================================
Example output from main():

Vector dimension: 4
Initial vector count: 0

Adding vectors in batches...
Vector count after adding batch: 1000

Querying similar vectors...
Result 1:
  ID: e8de28c7-4ec1-4fba-b71c-b9640d11c2d7
  Payload: {'idx': 496, 'batch': 'example'}
  Similarity: 0.9847431876706196
Result 2:
  ID: 62755df8-8f8e-41db-87bc-206f54d324a6
  Payload: {'idx': 306, 'batch': 'example'}
  Similarity: 0.9598140307734809
Result 3:
  ID: 9a9dec55-cfc0-4323-a874-eb38269dc965
  Payload: {'idx': 654, 'batch': 'example'}
  Similarity: 0.9548076959468635
Result 4:
  ID: fd579792-dba1-4aab-8338-8b504f1b5419
  Payload: {'idx': 914, 'batch': 'example'}
  Similarity: 0.9496165658207311
Result 5:
  ID: 76a4f991-c5a7-4a68-9d40-d28311f18f32
  Payload: {'idx': 806, 'batch': 'example'}
  Similarity: 0.9485824622759768

Clearing vectors...
Vector count after clearing: 0

-------------------------------------------------------------------------------
Example output from example_filtered_query():

=== Filtered ANN Query Example ===
Added 5 records with categories: ['electronics', 'clothing', 'books', ...]

1. Query WITHOUT filter:
   - {'price': 199, 'item_id': 0, 'category': 'electronics'}
   - {'price': 25, 'item_id': 2, 'category': 'books'}
   - {'price': 599, 'item_id': 3, 'category': 'electronics'}
   - {'price': 15, 'item_id': 4, 'category': 'books'}
   - {'price': 49, 'item_id': 1, 'category': 'clothing'}

2. Query WITH category filter (electronics only):
   - {'price': 199, 'item_id': 0, 'category': 'electronics'}
   - {'price': 599, 'item_id': 3, 'category': 'electronics'}

3. Query WITH price filter (price < 100):
   - {'price': 25, 'item_id': 2, 'category': 'books'}
   - {'price': 15, 'item_id': 4, 'category': 'books'}
   - {'price': 49, 'item_id': 1, 'category': 'clothing'}

4. Query WITH multiple conditions (books AND price<30):
   - {'price': 25, 'item_id': 2, 'category': 'books'}
   - {'price': 15, 'item_id': 4, 'category': 'books'}

Filtered query example completed.

-------------------------------------------------------------------------------
Example output from example_distance_metrics():

=== Distance Metrics Example ===

--- Distance metric: l2 ---
  Query vector: [0.5, 0.5, 0.5, 0.5]
  Results (ordered by similarity):
    1. same_as_query: sim=1.0000
    2. unit_x: sim=0.3679
    3. unit_y: sim=0.3679
    4. opposite: sim=0.1353

--- Distance metric: cosine ---
  Query vector: [0.5, 0.5, 0.5, 0.5]
  Results (ordered by similarity):
    1. same_as_query: sim=1.0000
    2. unit_x: sim=0.5000
    3. unit_y: sim=0.5000
    4. opposite: sim=0.0000

--- Distance metric: inner_product ---
  Query vector: [0.5, 0.5, 0.5, 0.5]
  Results (ordered by similarity):
    1. same_as_query: sim=0.7311
    2. unit_x: sim=0.6225
    3. unit_y: sim=0.6225
    4. opposite: sim=0.2689

--- Distance metric: negative_inner_product ---
  Query vector: [0.5, 0.5, 0.5, 0.5]
  Results (ordered by similarity):
    1. same_as_query: sim=0.7311
    2. unit_x: sim=0.6225
    3. unit_y: sim=0.6225
    4. opposite: sim=0.2689

Distance metrics example completed.

-------------------------------------------------------------------------------
Example output from example_arbitrary_distance_metrics():

=== Arbitrary Distance Metrics Example ===

--- Distance metric: inner_product ---
  Query: [0.3, -0.7, 0.2, 0.8]
  Results:
    1. scaled_2x: sim=0.9255, vec=[0.6, -1.4, 0.4, 1.6]
    2. exact_match: sim=0.7790, vec=[0.3, -0.7, 0.2, 0.8]
    3. unit_w: sim=0.6900, vec=[0.0, 0.0, 0.0, 1.0]
    4. similar_dir: sim=0.6411, vec=[0.1, -0.3, 0.1, 0.4]
    5. orthogonal: sim=0.5200, vec=[0.8, 0.2, -0.5, 0.1]
    6. opposite: sim=0.2210, vec=[-0.3, 0.7, -0.2, -0.8]

--- Distance metric: negative_inner_product ---
  Query: [0.3, -0.7, 0.2, 0.8]
  Results:
    1. scaled_2x: sim=0.9255, vec=[0.6, -1.4, 0.4, 1.6]
    2. exact_match: sim=0.7790, vec=[0.3, -0.7, 0.2, 0.8]
    3. unit_w: sim=0.6900, vec=[0.0, 0.0, 0.0, 1.0]
    4. similar_dir: sim=0.6411, vec=[0.1, -0.3, 0.1, 0.4]
    5. orthogonal: sim=0.5200, vec=[0.8, 0.2, -0.5, 0.1]
    6. opposite: sim=0.2210, vec=[-0.3, 0.7, -0.2, -0.8]

--- Distance metric: cosine ---
  Query: [0.3, -0.7, 0.2, 0.8]
  Results:
    1. scaled_2x: sim=1.0000, vec=[0.6, -1.4, 0.4, 1.6]
    2. exact_match: sim=1.0000, vec=[0.3, -0.7, 0.2, 0.8]
    3. similar_dir: sim=0.9944, vec=[0.1, -0.3, 0.1, 0.4]
    4. unit_w: sim=0.7127, vec=[0.0, 0.0, 0.0, 1.0]
    5. orthogonal: sim=0.0735, vec=[0.8, 0.2, -0.5, 0.1]
    6. opposite: sim=0.0000, vec=[-0.3, 0.7, -0.2, -0.8]

--- Distance metric: l2 ---
  Query: [0.3, -0.7, 0.2, 0.8]
  Results:
    1. exact_match: sim=1.0000, vec=[0.3, -0.7, 0.2, 0.8]
    2. similar_dir: sim=0.5443, vec=[0.1, -0.3, 0.1, 0.4]
    3. unit_w: sim=0.4438, vec=[0.0, 0.0, 0.0, 1.0]
    4. scaled_2x: sim=0.3255, vec=[0.6, -1.4, 0.4, 1.6]
    5. orthogonal: sim=0.2397, vec=[0.8, 0.2, -0.5, 0.1]
    6. opposite: sim=0.1059, vec=[-0.3, 0.7, -0.2, -0.8]

Arbitrary distance metrics example completed.
===============================================================================
'''
