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


if __name__ == "__main__":
    main()

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
