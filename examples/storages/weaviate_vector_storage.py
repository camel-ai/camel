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
import warnings

import weaviate
from weaviate.classes.init import Auth

from camel.storages.vectordb_storages import (
    VectorDBQuery,
    VectorRecord,
    WeaviateStorage,
)

# Suppress Pydantic deprecation warnings from Weaviate client
warnings.filterwarnings(
    "ignore", message=".*model_fields.*", category=DeprecationWarning
)


"""
Before running this example, you need to setup a Weaviate instance:

(Option 1): Local Docker Weaviate:

1. Install Docker
2. Run the following command to start Weaviate:
   docker run -p 8080:8080 -p 50051:50051 cr.weaviate.io/semitechnologies/
   weaviate:1.31.0
3. Connect to local Weaviate instance example:
   import weaviate
   client = weaviate.connect_to_local(
            host="localhost",
            port=8080,
            grpc_port=50051,
        )

(Option 2): Weaviate Cloud Service (WCS):

1. Sign up at https://console.weaviate.cloud
2. Create a free Weaviate cluster
3. Get your API key and cluster URL
4. Connect to Weaviate Cloud Service example:
   import weaviate
   from weaviate.classes.init import Auth
   client = weaviate.connect_to_weaviate_cloud(
            cluster_url=WEAVIATE_URL,
            auth_credentials=Auth.api_key(WEAVIATE_API_KEY),
        )

        
For the convenience of demonstration,we use weaviate cloud service as an 
example to demonstrate the functionality.
"""

# Replace these with your Weaviate connection parameters
WEAVIATE_URL = (
    "7hh0x7e0qus857pcvhqq.c0.us-west3.gcp.weaviate.cloud"  # WCS cluster URL
)
WEAVIATE_API_KEY = "C7E8Q5ArFevK4DAE704KPHj2gNUkKcc6KQVS"  # WCS API key


def main():
    # Setup weaviate client, here we use weaviate cloud service instance,
    # you can also use local weaviate instance by using connect_to_local.
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=WEAVIATE_URL,
        auth_credentials=Auth.api_key(WEAVIATE_API_KEY),
    )

    # Create WeaviateStorage instance with dimension = 4
    weaviate_storage = WeaviateStorage(
        client=client, vector_dim=4, collection_name="camel_example_vectors"
    )

    # Get database status
    status = weaviate_storage.status()
    print(f"Vector dimension: {status.vector_dim}")
    print(f"Initial vector count: {status.vector_count}")

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

    # Query similar vectors,use the first vector as query vector
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
        print(f"  Similarity: {result.similarity}")
        # print(f"  Vector: {result.record.vector}")

    # Test deletion,delete the first two vectors
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

    # close weaviate client
    client.close()


if __name__ == "__main__":
    main()

"""
===============================================================================
Vector dimension: 4
Initial vector count: 0

Adding vectors...
Vector count after adding: 10

Querying similar vectors...
Result 1:
  ID: 0cf0e63b-2296-4222-b1f7-7e6b1b17822d
  Payload: {'idx': 0, 'category': 'example', 'description': 'Vector example 0'}
  Similarity: 1.0
Result 2:
  ID: bcc25824-4290-45e2-88c8-d380f83280f2
  Payload: {'idx': 1, 'category': 'example', 'description': 'Vector example 1'}
  Similarity: 0.8593824505805969
Result 3:
  ID: a33f3984-39d5-46e4-8062-7972ad2562f0
  Payload: {'idx': 9, 'category': 'example', 'description': 'Vector example 9'}
  Similarity: 0.8499993085861206

Deleting vectors...
Vector count after deletion: 8

Clearing all vectors...
Vector count after clearing: 0
===============================================================================
"""
