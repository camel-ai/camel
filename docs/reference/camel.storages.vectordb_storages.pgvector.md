<a id="camel.storages.vectordb_storages.pgvector"></a>

<a id="camel.storages.vectordb_storages.pgvector.PgVectorStorage"></a>

## PgVectorStorage

```python
class PgVectorStorage(BaseVectorStorage):
```

PgVectorStorage is an implementation of BaseVectorStorage for
PostgreSQL with pgvector extension.

This class provides methods to add, delete, query, and manage vector
records in a PostgreSQL database using the pgvector extension.
It supports different distance metrics for similarity search.

**Parameters:**

- **vector_dim** (int): The dimension of the vectors to be stored.
- **conn_info** (Dict[str, Any]): Connection information for psycopg2.connect.
- **table_name** (str, optional): Name of the table to store vectors. (default: :obj:`None`)
- **distance** (VectorDistance, optional): Distance metric for vector comparison. (default: :obj:`VectorDistance.COSINE`)

<a id="camel.storages.vectordb_storages.pgvector.PgVectorStorage.__init__"></a>

### __init__

```python
def __init__(
    self,
    vector_dim: int,
    conn_info: Dict[str, Any],
    table_name: Optional[str] = None,
    distance: VectorDistance = VectorDistance.COSINE,
    **kwargs: Any
):
```

Initialize PgVectorStorage.

**Parameters:**

- **vector_dim** (int): The dimension of the vectors.
- **conn_info** (Dict[str, Any]): Connection info for psycopg2.connect.
- **table_name** (str, optional): Table name. (default: :obj:`None`)
- **distance** (VectorDistance, optional): Distance metric. (default: :obj:`VectorDistance.COSINE`)

<a id="camel.storages.vectordb_storages.pgvector.PgVectorStorage._ensure_table"></a>

### _ensure_table

```python
def _ensure_table(self):
```

Ensure the vector table exists in the database.
Creates the table if it does not exist.

<a id="camel.storages.vectordb_storages.pgvector.PgVectorStorage._ensure_index"></a>

### _ensure_index

```python
def _ensure_index(self):
```

Ensure vector similarity search index exists for better
performance.

<a id="camel.storages.vectordb_storages.pgvector.PgVectorStorage.add"></a>

### add

```python
def add(self, records: List[VectorRecord], **kwargs: Any):
```

Add or update vector records in the database.

**Parameters:**

- **records** (List[VectorRecord]): List of vector records to add or update.

<a id="camel.storages.vectordb_storages.pgvector.PgVectorStorage.delete"></a>

### delete

```python
def delete(self, ids: List[str], **kwargs: Any):
```

Delete vector records from the database by their IDs.

**Parameters:**

- **ids** (List[str]): List of record IDs to delete.

<a id="camel.storages.vectordb_storages.pgvector.PgVectorStorage.query"></a>

### query

```python
def query(self, query: VectorDBQuery, **kwargs: Any):
```

Query the database for the most similar vectors to the given
query vector.

**Parameters:**

- **query** (VectorDBQuery): Query object containing the query vector and top_k. **kwargs (Any): Additional keyword arguments for the query.

**Returns:**

  List[VectorDBQueryResult]: List of query results sorted by
similarity.

<a id="camel.storages.vectordb_storages.pgvector.PgVectorStorage.status"></a>

### status

```python
def status(self, **kwargs: Any):
```

Get the status of the vector database, including vector
dimension and count.

**Returns:**

  VectorDBStatus: Status object with vector dimension and count.

<a id="camel.storages.vectordb_storages.pgvector.PgVectorStorage.clear"></a>

### clear

```python
def clear(self):
```

Remove all vectors from the storage by truncating the table.

<a id="camel.storages.vectordb_storages.pgvector.PgVectorStorage.load"></a>

### load

```python
def load(self):
```

Load the collection hosted on cloud service (no-op for pgvector).
This method is provided for interface compatibility.

<a id="camel.storages.vectordb_storages.pgvector.PgVectorStorage.close"></a>

### close

```python
def close(self):
```

Close the database connection.

<a id="camel.storages.vectordb_storages.pgvector.PgVectorStorage.__del__"></a>

### __del__

```python
def __del__(self):
```

Ensure connection is closed when object is destroyed.

<a id="camel.storages.vectordb_storages.pgvector.PgVectorStorage.client"></a>

### client

```python
def client(self):
```

**Returns:**

  Any: The underlying psycopg connection object.
