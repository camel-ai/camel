# Storages
## 1. Concept
The Storage module is a comprehensive framework designed for handling various types of data storage mechanisms. It is composed of abstract base classes and concrete implementations, catering to both key-value storage and vector storage systems.

## 2. Types

### 2.1. Key Value Storages
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

### 2.2. VectorDB Storages
**`BaseVectorStorage`**:

- Purpose: An abstract base class designed to be extended for specific vector storage implementations.

- Features: Supports various operations like adding, deleting vectors, querying similar vectors, and maintaining the status of the vector database.

- Functionality: Offers flexibility in specifying vector dimensions, collection names, distance metrics, and more.

**`MilvusStorage`**:

- Description: A concrete implementation of `BaseVectorStorage`, tailored for interacting with Milvus, a cloud-native vector search engine.

Reference: [Milvus](https://milvus.io/docs/overview.md/)

**`QdrantStorage`**:

- Description: A concrete implementation of `BaseVectorStorage`, tailored for interacting with Qdrant, a vector search engine.

Reference: [Qdrant](https://qdrant.tech/)

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

### 3.4. Using `QdrantStorage`

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
