<a id="camel.storages.vectordb_storages.chroma"></a>

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage"></a>

## ChromaStorage

```python
class ChromaStorage(BaseVectorStorage):
```

An implementation of the `BaseVectorStorage` for interacting with
ChromaDB, a vector database for embeddings.
ChromaDB is an open-source AI-native vector database focused on developer
productivity and happiness. The detailed information about ChromaDB is
available at: `ChromaDB <https://docs.trychroma.com/>`_

This class provides multiple ways to connect to ChromaDB instances:
- Ephemeral (in-memory for testing/prototyping)
- Persistent (local file storage)
- HTTP (remote ChromaDB server)
- Cloud (ChromaDB Cloud - future support)

**Parameters:**

- **vector_dim** (int): The dimension of storing vectors.
- **collection_name** (Optional[str], optional): Name for the collection in ChromaDB. If not provided, auto-generated with timestamp. (default: :obj:`None`)
- **client_type** (`Literal["ephemeral", "persistent", "http", "cloud"]`): Type of ChromaDB client to use. Supported types: 'ephemeral', 'persistent', 'http', 'cloud'. (default: :obj:`"ephemeral"`) # Persistent client parameters
- **path** (Optional[str], optional): Path to directory for persistent storage. Only used when client_type='persistent'. (default: :obj:`"./chroma"`) # HTTP client parameters
- **host** (str, optional): Host for remote ChromaDB server. (default: :obj:`"localhost"`)
- **port** (int, optional): Port for remote ChromaDB server. (default: :obj:`8000`)
- **ssl** (bool, optional): Whether to use SSL for HTTP connections. (default: :obj:`False`)
- **headers** (Optional[Dict[str, str]], optional): Additional headers for HTTP client requests. (default: :obj:`None`) # Cloud client parameters
- **api_key** (Optional[str], optional): API key for ChromaDB Cloud. (default: :obj:`None`)
- **cloud_host** (str, optional): ChromaDB Cloud host. (default: :obj:`"api.trychroma.com"`)
- **cloud_port** (int, optional): ChromaDB Cloud port. (default: :obj:`8000`)
- **enable_ssl** (bool, optional): Whether to enable SSL for cloud connection.(default: :obj:`True`) # Common parameters for all client types
- **settings** (Optional[Any], optional): ChromaDB settings object for advanced configuration. (default: :obj:`None`)
- **tenant** (Optional[str], optional): Tenant name for multi-tenancy support. (default: :obj:`None`)
- **database** (Optional[str], optional): Database name for multi-database support. (default: :obj:`None`)
- **distance** (VectorDistance, optional): The distance metric for vector comparison. (default: :obj:`VectorDistance.COSINE`)
- **delete_collection_on_del** (bool, optional): Flag to determine if the collection should be deleted upon object destruction. (default: :obj:`False`)

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage.__init__"></a>

### __init__

```python
def __init__(
    self,
    vector_dim: int,
    collection_name: Optional[str] = None,
    client_type: Literal['ephemeral', 'persistent', 'http', 'cloud'] = 'ephemeral',
    path: Optional[str] = './chroma',
    host: str = 'localhost',
    port: int = 8000,
    ssl: bool = False,
    headers: Optional[Dict[str, str]] = None,
    api_key: Optional[str] = None,
    cloud_host: str = 'api.trychroma.com',
    cloud_port: int = 8000,
    enable_ssl: bool = True,
    settings: Optional[Any] = None,
    tenant: Optional[str] = None,
    database: Optional[str] = None,
    distance: VectorDistance = VectorDistance.COSINE,
    delete_collection_on_del: bool = False,
    **kwargs: Any
):
```

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage.__del__"></a>

### __del__

```python
def __del__(self):
```

Deletes the collection if :obj:`delete_collection_on_del` is set to
:obj:`True`.

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage._validate_client_type"></a>

### _validate_client_type

```python
def _validate_client_type(
    self,
    client_type: Literal['ephemeral', 'persistent', 'http', 'cloud']
):
```

Validates client type parameter.

**Parameters:**

- **client_type** (`Literal["ephemeral", "persistent", "http", "cloud"]`): The client type to validate.

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage._validate_client_config"></a>

### _validate_client_config

```python
def _validate_client_config(self):
```

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage._get_connection_client"></a>

### _get_connection_client

```python
def _get_connection_client(self):
```

Get ChromaDB client based on client type and user settings.

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage._create_ephemeral_client"></a>

### _create_ephemeral_client

```python
def _create_ephemeral_client(self, chromadb_module: Any):
```

Create an ephemeral ChromaDB client (in-memory).

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage._create_persistent_client"></a>

### _create_persistent_client

```python
def _create_persistent_client(self, chromadb_module: Any):
```

Create a persistent ChromaDB client (local file storage).

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage._create_http_client"></a>

### _create_http_client

```python
def _create_http_client(self, chromadb_module: Any):
```

Create an HTTP ChromaDB client (remote server).

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage._create_cloud_client"></a>

### _create_cloud_client

```python
def _create_cloud_client(self, chromadb_module: Any):
```

Create a cloud ChromaDB client.

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage._get_common_client_kwargs"></a>

### _get_common_client_kwargs

```python
def _get_common_client_kwargs(self):
```

Get common kwargs for all ChromaDB clients.

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage._generate_collection_name"></a>

### _generate_collection_name

```python
def _generate_collection_name(self):
```

**Returns:**

  str: Generated collection name based on current timestamp.

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage._get_distance_function"></a>

### _get_distance_function

```python
def _get_distance_function(self):
```

**Returns:**

  str: ChromaDB distance function name.

References:
https://docs.trychroma.com/docs/collections/configure

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage._get_or_create_collection"></a>

### _get_or_create_collection

```python
def _get_or_create_collection(self):
```

**Returns:**

  ChromaDB collection object.

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage.add"></a>

### add

```python
def add(self, records: List[VectorRecord], **kwargs: Any):
```

Adds vector records to ChromaDB collection.

**Parameters:**

- **records** (List[VectorRecord]): List of vector records to be saved. **kwargs (Any): Additional keyword arguments for ChromaDB add operation.

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage.delete"></a>

### delete

```python
def delete(self, ids: List[str], **kwargs: Any):
```

Deletes vectors by their IDs from ChromaDB collection.

**Parameters:**

- **ids** (List[str]): List of unique identifiers for the vectors to be deleted. **kwargs (Any): Additional keyword arguments for ChromaDB delete operation.

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage.status"></a>

### status

```python
def status(self):
```

**Returns:**

  VectorDBStatus: The vector database status containing dimension
and count information.

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage.query"></a>

### query

```python
def query(self, query: VectorDBQuery, **kwargs: Any):
```

Searches for similar vectors in ChromaDB based on the provided
query.

**Parameters:**

- **query** (VectorDBQuery): The query object containing the search vector and the number of top similar vectors to retrieve. **kwargs (Any): Additional keyword arguments for ChromaDB query operation.

**Returns:**

  List[VectorDBQueryResult]: A list of vectors retrieved from the
storage based on similarity to the query vector.

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage._distance_to_similarity"></a>

### _distance_to_similarity

```python
def _distance_to_similarity(self, distance: float):
```

Convert distance to similarity score based on distance metric.

**Parameters:**

- **distance** (float): Distance value from ChromaDB.

**Returns:**

  float: Similarity score (higher means more similar).

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage.clear"></a>

### clear

```python
def clear(self):
```

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage.load"></a>

### load

```python
def load(self):
```

Load the collection hosted on cloud service.

For ChromaDB, collections are automatically available when client
connects, so this method is a no-op.

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage.delete_collection"></a>

### delete_collection

```python
def delete_collection(self):
```

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage.client"></a>

### client

```python
def client(self):
```

**Returns:**

  chromadb.Client: The ChromaDB client instance.

<a id="camel.storages.vectordb_storages.chroma.ChromaStorage.collection"></a>

### collection

```python
def collection(self):
```

**Returns:**

  ChromaDB collection instance.
