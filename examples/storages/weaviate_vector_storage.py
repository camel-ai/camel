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
    VectorDBQuery,
    VectorRecord,
    WeaviateStorage,
)

"""
Before running this example, you need to setup a Weaviate instance(reference: https://weaviate.io/developers/weaviate):

(Option 1): Local Docker Weaviate:

1. Install Docker
2. Run the following command to start Weaviate:
   docker run -p 8080:8080 -p 50051:50051 cr.weaviate.io/semitechnologies/
   weaviate:1.31.0
3. The example will automatically connect to the local instance

(Option 2): Weaviate Cloud Service (WCS):

1. Sign up at https://console.weaviate.cloud
2. Create a free Weaviate cluster
3. Get your API key and cluster URL
4. Update the WEAVIATE_URL and WEAVIATE_API_KEY variables below

(Option 3): Embedded Weaviate:

Only supports Linux and macOS systems (Windows is not supported)

(Option 4): Custom Connection:

Configure custom HTTP/gRPC endpoints for specialized deployments

Note: You may see deprecation warnings from the Weaviate client library:
"PydanticDeprecatedSince211: Accessing the 'model_fields' attribute..."
These warnings are from the Weaviate library itself and can be safely ignored.
They do not affect the functionality of the code.

"""


def example_local_connection():
    r"""Example using local Weaviate instance (default connection type)."""
    print("=== Local Weaviate Connection Example ===")

    # Create WeaviateStorage instance with local connection (default)
    weaviate_storage = WeaviateStorage(
        vector_dim=4,
        collection_name="camel_local_example",
        connection_type="local",
        local_host="localhost",
        local_port=8080,
        local_grpc_port=50051,
        # Vector index configuration
        vector_index_type="hnsw",
        distance_metric="cosine",
    )

    run_storage_example(weaviate_storage)


def example_cloud_connection():
    """Example using Weaviate Cloud Service."""
    print("=== Weaviate Cloud Connection Example ===")

    # Replace these with your Weaviate Cloud connection parameters
    WEAVIATE_URL = "your-weaviate-cloud-url"
    WEAVIATE_API_KEY = "your-weaviate-api-key"

    # Create WeaviateStorage instance with cloud connection
    weaviate_storage = WeaviateStorage(
        vector_dim=4,
        collection_name="camel_cloud_example",
        connection_type="cloud",
        wcd_cluster_url=WEAVIATE_URL,
        wcd_api_key=WEAVIATE_API_KEY,
        # Vector index configuration
        vector_index_type="hnsw",
        distance_metric="cosine",
        # Additional headers for third-party API keys
        headers={
            "X-OpenAI-Api-Key": "your-openai-api-key",
            "X-Cohere-Api-Key": "your-cohere-api-key",
        },
    )

    run_storage_example(weaviate_storage)


def example_embedded_connection():
    """Example using embedded Weaviate."""
    print("=== Embedded Weaviate Connection Example ===")

    # Create WeaviateStorage instance with embedded connection
    weaviate_storage = WeaviateStorage(
        vector_dim=4,
        collection_name="camel_embedded_example",
        connection_type="embedded",
        embedded_hostname="127.0.0.1",
        embedded_port=8079,
        embedded_grpc_port=50050,
        # Optional: persist data
        embedded_persistence_data_path="./weaviate_data",
        # Optional: specify Weaviate version
        embedded_version="1.31.0",
        # Optional: environment variables
        embedded_environment_variables={
            "QUERY_DEFAULTS_LIMIT": "25",
            "DEFAULT_VECTORIZER_MODULE": "none",
        },
        # Vector index configuration
        vector_index_type="hnsw",
        distance_metric="cosine",
    )

    run_storage_example(weaviate_storage)


def example_custom_connection():
    """Example using custom Weaviate connection."""
    print("=== Custom Weaviate Connection Example ===")

    # Create WeaviateStorage instance with custom connection
    weaviate_storage = WeaviateStorage(
        vector_dim=4,
        collection_name="camel_custom_example",
        connection_type="custom",
        custom_http_host="localhost",
        custom_http_port=8080,
        custom_http_secure=False,
        custom_grpc_host="localhost",
        custom_grpc_port=50051,
        custom_grpc_secure=False,
        # Optional: custom authentication
        custom_auth_credentials=None,
        # Vector index configuration
        vector_index_type="hnsw",
        distance_metric="cosine",
    )

    run_storage_example(weaviate_storage)


def run_storage_example(weaviate_storage: WeaviateStorage):
    """Run the common storage operations example."""

    # Get database status
    status = weaviate_storage.status()
    print(f"Vector dimension: {status.vector_dim}")
    print(f"Initial vector count: {status.vector_count}")
    print(f"Vector index type: {weaviate_storage.vector_index_type}")
    print(f"Distance metric: {weaviate_storage.distance_metric}")

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

    # Add vectors records to Weaviate
    weaviate_storage.add(vector_records)

    # Check updated status
    status = weaviate_storage.status()
    print(f"Vector count after adding: {status.vector_count}")

    # Query similar vectors, use the first vector as query vector
    print("\nQuerying similar vectors...")
    query_vector = vector_records[0].vector
    query_results = weaviate_storage.query(
        VectorDBQuery(query_vector=query_vector, top_k=3)
    )

    # Display query results
    for i, result in enumerate(query_results):
        print(f"Result {i+1}:")
        print(f"  ID: {result.record.id}")
        print(f"  Payload: {result.record.payload}")
        print(f"  Similarity: {result.similarity:.4f}")
        # print(f"  Vector: {result.record.vector}")

    # Test deletion, delete the first two vectors
    print("\nDeleting vectors...")
    ids_to_delete = [result.record.id for result in query_results[:2]]
    weaviate_storage.delete(ids_to_delete)

    # Verify deletion
    status = weaviate_storage.status()
    print(f"Vector count after deletion: {status.vector_count}")

    # Clear all vectors when done
    print("\nClearing all vectors...")
    weaviate_storage.clear()
    status = weaviate_storage.status()
    print(f"Vector count after clearing: {status.vector_count}")

    # Close connection explicitly
    weaviate_storage.close()
    print("Connection closed.\n")


def main():
    """Main function demonstrating different connection types and
    configurations."""

    print(
        "This example demonstrates different Weaviate connection types and "
        "configurations."
    )
    print("Make sure you have the appropriate Weaviate instance running.\n")

    # Example 1: Local connection (requires local Weaviate instance)
    try:
        example_local_connection()
    except Exception as e:
        print(f"Local connection failed: {e}")
        print(
            "Make sure you have a local Weaviate instance running on "
            "localhost:8080\n"
        )

    # Example 2: Cloud connection (requires valid cloud credentials)
    # try:
    #     example_cloud_connection()
    # except Exception as e:
    #     print(f"Cloud connection failed: {e}")
    #     print("Make sure you have valid Weaviate Cloud credentials\n")

    # Example 3: Embedded connection (automatically starts embedded Weaviate)
    # Note: Embedded Weaviate client is unsupported on Windows system
    # try:
    #     example_embedded_connection()
    # except Exception as e:
    #     print(f"Embedded connection failed: {e}")
    #     print(
    #         "Make sure you have weaviate-client with embedded support "
    #         "installed\n"
    #     )

    # Example 4: Custom connection (requires custom Weaviate setup)
    # try:
    #     example_custom_connection()
    # except Exception as e:
    #     print(f"Custom connection failed: {e}")
    #     print("Make sure you have a custom Weaviate instance configured\n")


if __name__ == "__main__":
    main()

"""
===============================================================================
This example demonstrates different Weaviate connection types and 
configurations.
 Make sure you have the appropriate Weaviate instance running.

=== Local Weaviate Connection Example ===
Vector dimension: 4
Initial vector count: 0
Vector index type: hnsw
Distance metric: cosine

Adding vectors...
Vector count after adding: 10

Querying similar vectors...
Result 1:
  ID: 0b71d7a8-6913-4c21-8e8b-4ecdd164c4f9
  Payload: {'idx': 0, 'category': 'example', 'description': 'Vector example 0'}
  Similarity: 1.0000
Result 2:
  ID: 416fc9af-47ef-4648-a48a-98397b68b656
  Payload: {'idx': 1, 'category': 'example', 'description': 'Vector example 1'}
  Similarity: 0.8594
Result 3:
  ID: aac5509e-9e24-42c8-8b7e-33564c291d87
  Payload: {'idx': 9, 'category': 'example', 'description': 'Vector example 9'}
  Similarity: 0.8500

Deleting vectors...
Vector count after deletion: 8

Clearing all vectors...
Vector count after clearing: 0
Connection closed.
===============================================================================
"""
