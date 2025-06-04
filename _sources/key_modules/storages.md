## 1. Concept
The Storage module is a comprehensive framework designed for handling various types of data storage mechanisms. It is composed of abstract base classes and concrete implementations, catering to both key-value storage and vector storage systems.

## 2. Types

### 2.1 Key Value Storages
**`BaseKeyValueStorage`**:

- Purpose: Serves as the foundational abstract class for creating various key-value storage systems.

- Functionality: Standardizes operations like saving, loading, and clearing data records. It primarily interfaces through Python dictionaries.

- Use Cases: Applicable for JSON file storage, NoSQL databases (like MongoDB and Redis), and in-memory Python dictionaries.

**`InMemoryKeyValueStorage`**:

- Description: A concrete implementation of `BaseKeyValueStorage`, utilizing in-memory lists.

- Feature: Ideal for temporary storage as data is volatile and lost when the program terminates.

- Functionality: Implements methods for saving, loading, and clearing records in memory.

**`JsonStorage`**:

- Description: Another concrete implementation of `BaseKeyValueStorage`, focusing on JSON file storage.

- Feature: Ensures persistent storage of records in a human-readable format. Supports customization through a custom JSON encoder for specific enumerated types.

- Functionality: Includes methods for saving data in JSON format, loading, and clearing data.

### 2.2 VectorDB Storages
**`BaseVectorStorage`**:

- Purpose: An abstract base class designed to be extended for specific vector storage implementations.

- Features: Supports various operations like adding, deleting vectors, querying similar vectors, and maintaining the status of the vector database.

- Functionality: Offers flexibility in specifying vector dimensions, collection names, distance metrics, and more.

**`MilvusStorage`**:

- Description: A concrete implementation of `BaseVectorStorage`, tailored for interacting with Milvus, a cloud-native vector search engine.

Reference: [Milvus](https://milvus.io/docs/overview.md/)

**`TiDBStorage`**:

- Description: A concrete implementation of `BaseVectorStorage`, tailored for interacting with TiDB, one database for all your AI ambitions: vector embeddings, knowledge graphs, and operational data.

Reference: [TiDB](https://ai.pingcap.com/)

**`QdrantStorage`**:

- Description: A concrete implementation of `BaseVectorStorage`, tailored for interacting with Qdrant, a vector search engine.

Reference: [Qdrant](https://qdrant.tech/)


**`OceanBaseStorage`**:

- Description: A concrete implementation of `BaseVectorStorage`, tailored for interacting with OceanBase vector engine.

Reference: [OceanBase](https://www.oceanbase.com/)

### 2.3 Graph Storages
**`BaseGraphStorage`**:

- Purpose: An abstract base class designed to be extended for specific graph storage implementations.

- Features: Supports various operations like `get_client`, `get_schema`, `get_structured_schema`, `refresh_schema`, `add_triplet`, `delete_triplet`, and `query`. 

**`NebulaGraph`**:

- Description: A concrete implementation of `BaseGraphStorage`, tailored for interacting with NebulaGraph, an open source, distributed, scalable, lightning fast graph database.

Reference: [NebulaGraph](https://www.nebula-graph.io/)

**`Neo4jGraph`**:

- Description: A concrete implementation of `BaseGraphStorage`, tailored for interacting with Neo4jGraph, one of the most trusted graph database.

Reference: [Neo4jGraph](https://neo4j.com/)

## 3. Get Started

To get started with the storage module you've provided, you'll need to understand the basic usage of the key classes and their methods. The module includes an abstract base class `BaseKeyValueStorage` and its concrete implementations `InMemoryKeyValueStorage` and `JsonStorage`, as well as a vector storage system through `BaseVectorStorage` and its implementation `MilvusStorage` or `QdrantStorage`.

### 3.1. Using `InMemoryKeyValueStorage`

```python
from camel.storages.key_value_storages import InMemoryKeyValueStorage

# Create an instance of InMemoryKeyValueStorage
memory_storage = InMemoryKeyValueStorage()

# Save records
memory_storage.save([{'key1': 'value1'}, {'key2': 'value2'}])

# Load records
records = memory_storage.load()
print(records)

# Clear all records
memory_storage.clear()
```
```markdown
>>> [{'key1': 'value1'}, {'key2': 'value2'}]
```

### 3.2. Using `JsonStorage`

```python
from camel.storages.key_value_storages import JsonStorage
from pathlib import Path

# Create an instance of JsonStorage with a specific file path
json_storage = JsonStorage(Path("my_data.json"))

# Save records
json_storage.save([{'key1': 'value1'}, {'key2': 'value2'}])

# Load records
records = json_storage.load()
print(records)

# Clear all records
json_storage.clear()
```
```markdown
>>>  [{'key1': 'value1'}, {'key2': 'value2'}]
```

### 3.3. Using `MilvusStorage`

```python
from camel.storages import MilvusStorage, VectorDBQuery, VectorRecord

# Create an instance of MilvusStorage with dimension = 4
milvus_storage = MilvusStorage(
    url_and_api_key=("Your Milvus URI","Your Milvus Token"),
    vector_dim=4,
    collection_name="my_collection")

# Add two vector records
milvus_storage.add([VectorRecord(
            vector=[-0.1, 0.1, -0.1, 0.1],
            payload={'key1': 'value1'},
        ),
        VectorRecord(
            vector=[-0.1, 0.1, 0.1, 0.1],
            payload={'key2': 'value2'},
        ),])

# Load the remote collection
milvus_storage.load()

# Query similar vectors
query_results = milvus_storage.query(VectorDBQuery(query_vector=[0.1, 0.2, 0.1, 0.1], top_k=1))
for result in query_results:
    print(result.record.payload, result.similarity)

# Clear all vectors
milvus_storage.clear()
```
```markdown
>>> {'key2': 'value2'} 0.5669466853141785
```

### 3.4. Using `TiDBStorage`

If you use TiDB Serverless, you can redirect to [TiDB Cloud Web Console](https://tidbcloud.com/console/clusters) to get the database URL. (Select Connect with "SQLAlchemy" > "PyMySQL" on the connection panel)

```python
import os
from camel.storages import TiDBStorage, VectorDBQuery, VectorRecord

os.environ["TIDB_DATABASE_URL"] = "The database url of your TiDB cluster."

# Create an instance of TiDBStorage with dimension = 4
tidb_storage = TiDBStorage(
    url_and_api_key=(os.getenv("DATABASE_URL"), ''),
    vector_dim=4,
    collection_name="my_collection"
)

# Add two vector records
tidb_storage.add([
    VectorRecord(
        vector=[-0.1, 0.1, -0.1, 0.1],
        payload={'key1': 'value1'},
    ),
    VectorRecord(
        vector=[-0.1, 0.1, 0.1, 0.1],
        payload={'key2': 'value2'},
    ),
])

# Load the remote collection
tidb_storage.load()

# Query similar vectors
query_results = tidb_storage.query(VectorDBQuery(query_vector=[0.1, 0.2, 0.1, 0.1], top_k=1))
for result in query_results:
    print(result.record.payload, result.similarity)

# Clear all vectors
tidb_storage.clear()
```
```markdown
>>> {'key2': 'value2'} 0.5669466755703252
```

### 3.5. Using `QdrantStorage`

```python
from camel.storages import QdrantStorage, VectorDBQuery, VectorRecord

# Create an instance of QdrantStorage with dimension = 4
qdrant_storage = QdrantStorage(vector_dim=4, collection_name="my_collection")

# Add two vector records
qdrant_storage.add([VectorRecord(
            vector=[-0.1, 0.1, -0.1, 0.1],
            payload={'key1': 'value1'},
        ),
        VectorRecord(
            vector=[-0.1, 0.1, 0.1, 0.1],
            payload={'key2': 'value2'},
        ),])

# Query similar vectors
query_results = qdrant_storage.query(VectorDBQuery(query_vector=[0.1, 0.2, 0.1, 0.1], top_k=1))
for result in query_results:
    print(result.record.payload, result.similarity)

# Clear all vectors
qdrant_storage.clear()
```
```markdown
>>> {'key2': 'value2'} 0.5669467095138407
```
### 3.6. Using `OceanBaseStorage`

```python
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
   https://www.oceanbase.com/docs/oceanbase-database
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

```
```markdown
'''
===============================================================================
Vector dimension: 4
Initial vector count: 0
Adding vectors in batches...
Vector count after adding batch: 1000
Querying similar vectors...
Result 1:
  ID: f33f008d-688a-468a-9a2d-e005d27ad9d9
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
  ID: 8d6359ff-49fd-4fb7-99fd-bf4ca0a0cdcx
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

```

### 3.7. Using `NebulaGraph`

```python
from camel.storages.graph_storages import NebulaGraph

nebula_graph = NebulaGraph("your_host", "your_username", "your_password", "your_space")

# Show existing tags
query = 'SHOW TAGS;'
print(nebula_graph.query(query))
```

### 3.8. Using `Neo4jGraph`

```python
from camel.storages import Neo4jGraph

neo4j_graph = Neo4jGraph(
    url="your_url",
    username="your_username",
    password="your_password",
)

query = "MATCH (n) DETACH DELETE n"
print(neo4j_graph.query(query))
```