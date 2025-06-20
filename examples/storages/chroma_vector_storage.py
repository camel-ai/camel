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
    ChromaStorage,
    VectorDBQuery,
    VectorRecord,
)
from camel.types import VectorDistance

"""
Before running this example, you need to setup ChromaDB based on your chosen 
connection type:

(Option 1): Ephemeral ChromaDB (In-Memory):

This is the simplest option for testing and prototyping. No setup required.
Data will be lost when the program ends.

(Option 2): Persistent ChromaDB (Local File Storage):

1. Install ChromaDB: pip install chromadb
2. Choose a local directory to store data (default: "./chroma")
3. Data persists across sessions

(Option 3): HTTP ChromaDB (Remote Server):

1. Start a ChromaDB server:
   - Install ChromaDB: pip install chromadb
   - Run server: chroma run --path /db_path
   - Or use Docker: docker run -v ./chroma-data:/data -p 8000:8000 \
     chromadb/chroma
2. Configure host and port in the example

(Option 4): ChromaDB Cloud:

Currently in development. Will be available in future ChromaDB releases.
Use other client types for now.

Note: ChromaDB requires Python 3.8+ and may have specific system requirements.
For detailed information, visit: https://docs.trychroma.com/
"""


def example_ephemeral_connection():
    """Example using ephemeral ChromaDB (in-memory)."""
    print("=== Ephemeral ChromaDB Connection Example ===")

    # Create ChromaStorage instance with ephemeral connection (default)
    chroma_storage = ChromaStorage(
        vector_dim=4,
        collection_name="camel_ephemeral_example",
        client_type="ephemeral",
        distance=VectorDistance.COSINE,
    )

    run_storage_example(chroma_storage)


def example_persistent_connection():
    """Example using persistent ChromaDB (local file storage)."""
    print("=== Persistent ChromaDB Connection Example ===")

    # Create ChromaStorage instance with persistent connection
    chroma_storage = ChromaStorage(
        vector_dim=4,
        collection_name="camel_persistent_example",
        client_type="persistent",
        path="./chroma_data",  # Local storage path
        distance=VectorDistance.COSINE,
        delete_collection_on_del=False,  # Keep data after object deletion
    )

    run_storage_example(chroma_storage)


def example_http_connection():
    """Example using HTTP ChromaDB (remote server)."""
    print("=== HTTP ChromaDB Connection Example ===")

    # Create ChromaStorage instance with HTTP connection
    chroma_storage = ChromaStorage(
        vector_dim=4,
        collection_name="camel_http_example",
        client_type="http",
        host="localhost",
        port=8000,
        ssl=False,
        headers=None,  # Optional: add authentication headers
        distance=VectorDistance.COSINE,
    )

    run_storage_example(chroma_storage)


def example_cloud_connection():
    """Example using ChromaDB Cloud (future support)."""
    print("=== ChromaDB Cloud Connection Example ===")

    try:
        # Replace these with your ChromaDB Cloud connection parameters
        CHROMA_TENANT = "your-tenant-name"
        CHROMA_DATABASE = "your-database-name"
        CHROMA_API_KEY = "your-api-key"  # Optional

        # Create ChromaStorage instance with cloud connection
        chroma_storage = ChromaStorage(
            vector_dim=4,
            collection_name="camel_cloud_example",
            client_type="cloud",
            cloud_host="api.trychroma.com",
            cloud_port=8000,
            enable_ssl=True,
            api_key=CHROMA_API_KEY,  # Optional
            tenant=CHROMA_TENANT,
            database=CHROMA_DATABASE,
            distance=VectorDistance.COSINE,
        )

        run_storage_example(chroma_storage)

    except RuntimeError as e:
        print(f"Cloud connection not yet available: {e}")
        print("CloudClient will be available in future ChromaDB releases.")


def run_storage_example(chroma_storage: ChromaStorage):
    """Run the common storage operations example."""

    # Get database status
    status = chroma_storage.status()
    print(f"Vector dimension: {status.vector_dim}")
    print(f"Initial vector count: {status.vector_count}")
    print(f"Client type: {chroma_storage.client_type}")
    print(f"Distance metric: {chroma_storage.distance}")

    # Generate vector records
    print("\nAdding vectors...")
    random.seed(20250605)
    vector_records = []
    for i in range(10):
        vector_records.append(
            VectorRecord(
                vector=[random.uniform(-1, 1) for _ in range(4)],
                payload={
                    'idx': i,
                    'category': 'example',
                    'description': f'Vector example {i}',
                },
            )
        )

    # Add vector records to ChromaDB
    chroma_storage.add(vector_records)

    # Check updated status
    status = chroma_storage.status()
    print(f"Vector count after adding: {status.vector_count}")

    # Query similar vectors, use the first vector as query vector
    print("\nQuerying similar vectors...")
    query_vector = vector_records[0].vector
    query_results = chroma_storage.query(
        VectorDBQuery(query_vector=query_vector, top_k=3)
    )

    # Display query results
    for i, result in enumerate(query_results):
        print(f"Result {i+1}:")
        print(f"  ID: {result.record.id}")
        print(f"  Payload: {result.record.payload}")
        print(f"  Similarity: {result.similarity:.4f}")
        # print(f"  Vector: {result.record.vector}")

    # Test deletion - delete the first two vectors
    print("\nDeleting vectors...")
    ids_to_delete = [result.record.id for result in query_results[:2]]
    chroma_storage.delete(ids_to_delete)

    # Verify deletion
    status = chroma_storage.status()
    print(f"Vector count after deletion: {status.vector_count}")

    # Clear all vectors when done
    print("\nClearing all vectors...")
    chroma_storage.clear()
    status = chroma_storage.status()
    print(f"Vector count after clearing: {status.vector_count}")

    print("ChromaDB operations completed.\n")


def example_different_distance_metrics():
    """Example demonstrating different distance metrics."""
    print("=== Different Distance Metrics Example ===")

    # Test with different distance metrics
    distance_metrics = [
        VectorDistance.COSINE,
        VectorDistance.EUCLIDEAN,
        VectorDistance.DOT,
    ]

    # Generate test vectors
    random.seed(42)
    test_vectors = [
        [1.0, 0.0, 0.0, 0.0],
        [0.8, 0.6, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
    ]

    for distance in distance_metrics:
        print(f"\nTesting with {distance.value} distance:")

        chroma_storage = ChromaStorage(
            vector_dim=4,
            collection_name=f"camel_distance_{distance.value}",
            client_type="ephemeral",
            distance=distance,
        )

        # Add test vectors
        records = [
            VectorRecord(vector=vector, payload={'name': f'vector_{i}'})
            for i, vector in enumerate(test_vectors)
        ]
        chroma_storage.add(records)

        # Query with first vector
        query_results = chroma_storage.query(
            VectorDBQuery(query_vector=test_vectors[0], top_k=3)
        )

        for result in query_results:
            print(
                f"  {result.record.payload['name']}: "
                f"similarity = {result.similarity:.4f}"
            )


def main():
    """Main function demonstrating different ChromaDB connection types and
    configurations."""

    print(
        "This example demonstrates different ChromaDB connection types and "
        "configurations."
    )
    print("ChromaDB is an AI-native vector database for embeddings.\n")

    # Example 1: Ephemeral connection (in-memory, no setup required)
    try:
        example_ephemeral_connection()
    except Exception as e:
        print(f"Ephemeral connection failed: {e}")
        print("Make sure ChromaDB is installed: pip install chromadb\n")

    # Example 2: Persistent connection (local file storage)
    try:
        example_persistent_connection()
    except Exception as e:
        print(f"Persistent connection failed: {e}")
        print("Make sure you have write permissions for the storage path\n")

    # Example 3: HTTP connection (requires ChromaDB server)
    # Uncomment to test with a running ChromaDB server
    try:
        example_http_connection()
    except Exception as e:
        print(f"HTTP connection failed: {e}")
        print("Make sure ChromaDB server is running on localhost:8000\n")

    # Example 4: Cloud connection (future support)
    # try:
    #     example_cloud_connection()
    # except Exception as e:
    #     print(f"Cloud connection failed: {e}")

    # Example 5: Different distance metrics
    try:
        example_different_distance_metrics()
    except Exception as e:
        print(f"Distance metrics example failed: {e}")


if __name__ == "__main__":
    main()

"""
===============================================================================
This example demonstrates different ChromaDB connection types and 
configurations.ChromaDB is an AI-native vector database for embeddings.

=== Ephemeral ChromaDB Connection Example ===
Vector dimension: 4
Initial vector count: 0
Client type: ephemeral
Distance metric: VectorDistance.COSINE

Adding vectors...
Vector count after adding: 10

Querying similar vectors...
Result 1:
  ID: cc158e98-af38-4cce-9406-4618bd91cfab
  Payload: {'category': 'example', 'description': 'Vector example 0', 'idx': 0}
  Similarity: 1.0000
Result 2:
  ID: bb3d09ab-5a16-4818-aa05-0717c1125306
  Payload: {'category': 'example', 'description': 'Vector example 1', 'idx': 1}
  Similarity: 0.8594
Result 3:
  ID: 9015109e-e9aa-4d8a-83b8-7fbfe80856a4
  Payload: {'category': 'example', 'description': 'Vector example 9', 'idx': 9}
  Similarity: 0.8500

Deleting vectors...
Vector count after deletion: 8

Clearing all vectors...
Vector count after clearing: 0
ChromaDB operations completed.

=== Persistent ChromaDB Connection Example ===
Persistent connection failed: Failed to get or create collection: '_type'
Make sure you have write permissions for the storage path

=== HTTP ChromaDB Connection Example ===
Vector dimension: 4
Initial vector count: 0
Client type: http
Distance metric: VectorDistance.COSINE

Adding vectors...
Vector count after adding: 10

Querying similar vectors...
Result 1:
  ID: 6bdd24ad-382b-4f95-88ef-f784b881fc2c
  Payload: {'category': 'example', 'description': 'Vector example 0', 'idx': 0}
  Similarity: 1.0000
Result 2:
  ID: d0b95d8f-89e3-4330-9bf5-2c5a03610c4e
  Payload: {'category': 'example', 'description': 'Vector example 1', 'idx': 1}
  Similarity: 0.8594
Result 3:
  ID: 19d2cf62-f4cc-44a9-9866-ad491308fd95
  Payload: {'category': 'example', 'description': 'Vector example 9', 'idx': 9}
  Similarity: 0.8500

Deleting vectors...
Vector count after deletion: 8

Clearing all vectors...
Vector count after clearing: 0
ChromaDB operations completed.

=== Different Distance Metrics Example ===

Testing with cosine distance:
  vector_0: similarity = 1.0000
  vector_1: similarity = 0.9000
  vector_2: similarity = 0.5000

Testing with euclidean distance:
  vector_0: similarity = 1.0000
  vector_1: similarity = 0.7143
  vector_2: similarity = 0.3333

Testing with dot distance:
  vector_0: similarity = 1.0000
  vector_1: similarity = 0.8000
  vector_2: similarity = 0.0000
===============================================================================
"""
