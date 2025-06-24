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
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

if TYPE_CHECKING:
    from chromadb.api import ClientAPI
    from chromadb.api.models.Collection import Collection
    from chromadb.api.types import (
        QueryResult,
    )

from camel.logger import get_logger
from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)
from camel.types import VectorDistance
from camel.utils import dependencies_required

logger = get_logger(__name__)


class ChromaStorage(BaseVectorStorage):
    r"""An implementation of the `BaseVectorStorage` for interacting with
    ChromaDB, a vector database for embeddings.
    ChromaDB is an open-source AI-native vector database focused on developer
    productivity and happiness. The detailed information about ChromaDB is
    available at: `ChromaDB <https://docs.trychroma.com/>`_

    This class provides multiple ways to connect to ChromaDB instances:
    - Ephemeral (in-memory for testing/prototyping)
    - Persistent (local file storage)
    - HTTP (remote ChromaDB server)
    - Cloud (ChromaDB Cloud - future support)

    Args:
        vector_dim (int): The dimension of storing vectors.
        collection_name (Optional[str], optional): Name for the collection in
            ChromaDB. If not provided, auto-generated with timestamp.
            (default: :obj:`None`)
        client_type (Literal["ephemeral", "persistent", "http", "cloud"]):
            Type of ChromaDB client to use. Supported types: 'ephemeral',
            'persistent', 'http', 'cloud'. (default: :obj:`"ephemeral"`)

        # Persistent client parameters
        path (Optional[str], optional): Path to directory for persistent
            storage. Only used when client_type='persistent'.
            (default: :obj:`"./chroma"`)

        # HTTP client parameters
        host (str, optional): Host for remote ChromaDB server.
            (default: :obj:`"localhost"`)
        port (int, optional): Port for remote ChromaDB server.
            (default: :obj:`8000`)
        ssl (bool, optional): Whether to use SSL for HTTP connections.
            (default: :obj:`False`)
        headers (Optional[Dict[str, str]], optional): Additional headers for
            HTTP client requests. (default: :obj:`None`)

        # Cloud client parameters
        api_key (Optional[str], optional): API key for ChromaDB Cloud.
            (default: :obj:`None`)
        cloud_host (str, optional): ChromaDB Cloud host.
            (default: :obj:`"api.trychroma.com"`)
        cloud_port (int, optional): ChromaDB Cloud port.
            (default: :obj:`8000`)
        enable_ssl (bool, optional): Whether to enable SSL for
            cloud connection.(default: :obj:`True`)

        # Common parameters for all client types
        settings (Optional[Any], optional): ChromaDB settings object for
            advanced configuration. (default: :obj:`None`)
        tenant (Optional[str], optional): Tenant name for multi-tenancy
            support. (default: :obj:`None`)
        database (Optional[str], optional): Database name for multi-database
            support. (default: :obj:`None`)
        distance (VectorDistance, optional): The distance metric for vector
            comparison. (default: :obj:`VectorDistance.COSINE`)

        delete_collection_on_del (bool, optional): Flag to determine if the
            collection should be deleted upon object destruction.
            (default: :obj:`False`)

    Raises:
        ImportError: If `chromadb` package is not installed.
        ValueError: If invalid client configuration is provided.
        RuntimeError: If there's an error setting up the collection.

    Examples:
        >>> # In-memory storage (ephemeral)
        >>> storage = ChromaStorage(
        ...     vector_dim=384,
        ...     client_type="ephemeral"
        ... )

        >>> # Persistent storage (custom path)
        >>> storage = ChromaStorage(
        ...     vector_dim=384,
        ...     client_type="persistent",
        ...     path="/path/to/chroma/data"
        ... )

        >>> # Remote HTTP connection (custom host/port)
        >>> storage = ChromaStorage(
        ...     vector_dim=384,
        ...     client_type="http",
        ...     host="remote-server.com",
        ...     port=9000,
        ...     ssl=True
        ... )

        >>> # ChromaDB Cloud (using defaults)
        >>> storage = ChromaStorage(
        ...     vector_dim=384,
        ...     client_type="cloud",
        ...     tenant="my-tenant",
        ...     database="my-database",
        ...     api_key="your-api-key"  # optional
        ... )
    """

    @dependencies_required('chromadb')
    def __init__(
        self,
        vector_dim: int,
        collection_name: Optional[str] = None,
        client_type: Literal[
            "ephemeral", "persistent", "http", "cloud"
        ] = "ephemeral",
        # Persistent client parameters
        path: Optional[str] = "./chroma",
        # HTTP client parameters
        host: str = "localhost",
        port: int = 8000,
        ssl: bool = False,
        headers: Optional[Dict[str, str]] = None,
        # Cloud client parameters
        api_key: Optional[str] = None,
        cloud_host: str = "api.trychroma.com",
        cloud_port: int = 8000,
        enable_ssl: bool = True,
        # Common parameters for all client types
        settings: Optional[Any] = None,
        tenant: Optional[str] = None,
        database: Optional[str] = None,
        distance: VectorDistance = VectorDistance.COSINE,
        delete_collection_on_del: bool = False,
        **kwargs: Any,
    ) -> None:
        self.vector_dim = vector_dim
        self.distance = distance
        self.collection_name = (
            collection_name or self._generate_collection_name()
        )

        self.delete_collection_on_del = delete_collection_on_del

        # Validate client type
        self._validate_client_type(client_type)
        self.client_type: Literal[
            "ephemeral", "persistent", "http", "cloud"
        ] = client_type

        # Store connection parameters for later use
        self._connection_params = {
            'path': path,
            'host': host,
            'port': port,
            'ssl': ssl,
            'headers': headers,
            'api_key': api_key,
            'cloud_host': cloud_host,
            'cloud_port': cloud_port,
            'enable_ssl': enable_ssl,
            'settings': settings,
            'tenant': tenant,
            'database': database,
            **kwargs,
        }

        # Validate client configuration
        self._validate_client_config()

        # Create client using the unified approach
        self._client: "ClientAPI" = self._get_connection_client()
        logger.info(f"Created ChromaDB client with type: {self.client_type}")

        # Create or get the collection
        self._collection: "Collection" = self._get_or_create_collection()

        logger.info(
            f"Successfully initialized ChromaDB storage "
            f"({self.client_type}) with collection: {self.collection_name}"
        )

    def __del__(self) -> None:
        r"""Deletes the collection if :obj:`delete_collection_on_del` is set to
        :obj:`True`.
        """
        if (
            hasattr(self, "delete_collection_on_del")
            and self.delete_collection_on_del
        ):
            try:
                self.delete_collection()
            except Exception as e:
                logger.error(
                    f"Failed to delete collection "
                    f"'{self.collection_name}': {e}"
                )

    def _validate_client_type(
        self, client_type: Literal["ephemeral", "persistent", "http", "cloud"]
    ) -> None:
        r"""Validates client type parameter.

        Args:
            client_type (Literal["ephemeral", "persistent", "http", "cloud"]):
                The client type to validate.

        Raises:
            ValueError: If client type is invalid.
        """
        valid_types = ["ephemeral", "persistent", "http", "cloud"]
        if client_type not in valid_types:
            raise ValueError(
                f"Invalid client_type '{client_type}'. "
                f"Must be one of: {valid_types}"
            )

    def _validate_client_config(self) -> None:
        r"""Validates client configuration parameters.

        Raises:
            ValueError: If configuration is invalid.
        """
        if self.client_type == "persistent":
            # path has a default value, but ensure it's not None
            if self._connection_params.get('path') is None:
                raise ValueError(
                    "path parameter cannot be None "
                    "for 'persistent' client type"
                )
        elif self.client_type == "cloud":
            # For cloud client, tenant and database are required
            if self._connection_params.get('tenant') is None:
                raise ValueError(
                    "tenant parameter is required for 'cloud' client type"
                )
            if self._connection_params.get('database') is None:
                raise ValueError(
                    "database parameter is required for 'cloud' client type"
                )
        # 'ephemeral' and 'http' clients have sensible defaults
        #  and don't require validation

    def _get_connection_client(self) -> "ClientAPI":
        r"""Get ChromaDB client based on client type and user settings."""
        import chromadb

        # Map client types to handler methods
        client_handlers: Dict[
            Literal["ephemeral", "persistent", "http", "cloud"], Any
        ] = {
            'ephemeral': self._create_ephemeral_client,
            'persistent': self._create_persistent_client,
            'http': self._create_http_client,
            'cloud': self._create_cloud_client,
        }

        # Get client handler
        handler = client_handlers[self.client_type]

        try:
            return handler(chromadb)
        except Exception as e:
            logger.error(f"Failed to create {self.client_type} client: {e}")
            raise

    def _create_ephemeral_client(self, chromadb_module: Any) -> "ClientAPI":
        r"""Create an ephemeral ChromaDB client (in-memory)."""
        client_kwargs = self._get_common_client_kwargs()
        client = chromadb_module.EphemeralClient(**client_kwargs)
        logger.info("Created ChromaDB EphemeralClient (in-memory)")
        return client

    def _create_persistent_client(self, chromadb_module: Any) -> "ClientAPI":
        r"""Create a persistent ChromaDB client (local file storage)."""
        client_kwargs = {'path': self._connection_params['path']}
        client_kwargs.update(self._get_common_client_kwargs())
        client = chromadb_module.PersistentClient(**client_kwargs)
        logger.info(
            f"Created ChromaDB PersistentClient: "
            f"{self._connection_params['path']}"
        )
        return client

    def _create_http_client(self, chromadb_module: Any) -> "ClientAPI":
        r"""Create an HTTP ChromaDB client (remote server)."""
        client_kwargs = {
            'host': self._connection_params['host'],
            'port': self._connection_params['port'],
            'ssl': self._connection_params['ssl'],
        }
        if self._connection_params.get('headers') is not None:
            client_kwargs['headers'] = self._connection_params['headers']
        client_kwargs.update(self._get_common_client_kwargs())

        client = chromadb_module.HttpClient(**client_kwargs)
        logger.info(
            f"Created ChromaDB HttpClient: {self._connection_params['host']}:"
            f"{self._connection_params['port']}"
        )
        return client

    def _create_cloud_client(self, chromadb_module: Any) -> "ClientAPI":
        r"""Create a cloud ChromaDB client."""
        try:
            client_kwargs = {
                'cloud_host': self._connection_params['cloud_host'],
                'cloud_port': self._connection_params['cloud_port'],
                'enable_ssl': self._connection_params['enable_ssl'],
            }

            # Add optional API key
            if self._connection_params.get('api_key') is not None:
                client_kwargs['api_key'] = self._connection_params['api_key']

            # Add common parameters (settings, tenant, database)
            client_kwargs.update(self._get_common_client_kwargs())

            client = chromadb_module.CloudClient(**client_kwargs)
            logger.info(
                f"Created ChromaDB CloudClient: "
                f"{self._connection_params['cloud_host']}:"
                f"{self._connection_params['cloud_port']}"
            )
            return client
        except AttributeError:
            raise RuntimeError(
                "CloudClient is not yet available in this version of "
                "ChromaDB. Please use a different client type or "
                "upgrade ChromaDB when CloudClient is released."
            )

    def _get_common_client_kwargs(self) -> Dict[str, Any]:
        r"""Get common kwargs for all ChromaDB clients."""
        common_kwargs: Dict[str, Any] = {}

        # Add truly common parameters that all ChromaDB clients support
        if self._connection_params.get('settings') is not None:
            common_kwargs['settings'] = self._connection_params['settings']
        if self._connection_params.get('tenant') is not None:
            common_kwargs['tenant'] = self._connection_params['tenant']
        if self._connection_params.get('database') is not None:
            common_kwargs['database'] = self._connection_params['database']

        return common_kwargs

    def _generate_collection_name(self) -> str:
        r"""Generates a collection name if user doesn't provide one.

        Returns:
            str: Generated collection name based on current timestamp.
        """
        timestamp = (
            datetime.now().isoformat().replace(':', '-').replace('.', '-')
        )
        return f"chroma_collection_{timestamp}"

    def _get_distance_function(self) -> str:
        r"""Maps VectorDistance to ChromaDB distance function.

        Returns:
            str: ChromaDB distance function name.

        References:
            https://docs.trychroma.com/docs/collections/configure
        """
        distance_map: Dict[VectorDistance, str] = {
            VectorDistance.COSINE: "cosine",
            VectorDistance.EUCLIDEAN: "l2",
            VectorDistance.DOT: "ip",  # inner product
        }
        return distance_map.get(self.distance, "cosine")

    def _get_or_create_collection(self) -> "Collection":
        r"""Gets existing collection or creates a new one.

        Returns:
            ChromaDB collection object.

        Raises:
            RuntimeError: If collection operations fail.
        """
        try:
            logger.info(
                "Using fallback collection creation (older ChromaDB API)"
            )
            collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": self._get_distance_function()},
            )
            logger.info(f"Got or created collection: {self.collection_name}")

            return collection

        except Exception as e:
            raise RuntimeError(f"Failed to get or create collection: {e}")

    def add(
        self,
        records: List[VectorRecord],
        **kwargs: Any,
    ) -> None:
        r"""Adds vector records to ChromaDB collection.

        Args:
            records (List[VectorRecord]): List of vector records to be saved.
            **kwargs (Any): Additional keyword arguments for ChromaDB add
                operation.

        Raises:
            RuntimeError: If there is an error during the saving process.
        """
        if not records:
            return

        try:
            # Prepare data for ChromaDB
            ids: List[str] = [record.id for record in records]
            embeddings: List[List[float]] = [
                record.vector for record in records
            ]

            # Prepare metadatas - ChromaDB requires a list
            metadatas: List[Dict[str, Any]] = []
            for record in records:
                if record.payload is not None:
                    metadatas.append(record.payload)
                else:
                    metadatas.append({})

            # Add to collection using upsert for safety
            add_kwargs: Dict[str, Any] = {
                'ids': ids,
                'embeddings': embeddings,
                'metadatas': metadatas,
            }
            add_kwargs.update(kwargs)

            self._collection.upsert(**add_kwargs)

            logger.info(
                f"Successfully added {len(records)} records to "
                f"ChromaDB collection: {self.collection_name}"
            )

        except Exception as e:
            raise RuntimeError(f"Failed to add records to ChromaDB: {e}")

    def delete(
        self,
        ids: List[str],
        **kwargs: Any,
    ) -> None:
        r"""Deletes vectors by their IDs from ChromaDB collection.

        Args:
            ids (List[str]): List of unique identifiers for the vectors to be
                deleted.
            **kwargs (Any): Additional keyword arguments for ChromaDB delete
                operation.

        Raises:
            RuntimeError: If there is an error during the deletion process.
        """
        if not ids:
            return
        try:
            delete_kwargs: Dict[str, Any] = {'ids': ids}
            delete_kwargs.update(kwargs)

            self._collection.delete(**delete_kwargs)
            logger.info(
                f"Successfully deleted {len(ids)} records from "
                f"ChromaDB collection: {self.collection_name}"
            )

        except Exception as e:
            raise RuntimeError(f"Failed to delete records from ChromaDB: {e}")

    def status(self) -> VectorDBStatus:
        r"""Returns status of the ChromaDB collection.

        Returns:
            VectorDBStatus: The vector database status containing dimension
                and count information.

        Raises:
            RuntimeError: If there is an error getting the status.
        """
        try:
            count: int = self._collection.count()
            return VectorDBStatus(
                vector_dim=self.vector_dim, vector_count=count
            )
        except Exception as e:
            raise RuntimeError(f"Failed to get ChromaDB status: {e}")

    def query(
        self,
        query: VectorDBQuery,
        **kwargs: Any,
    ) -> List[VectorDBQueryResult]:
        r"""Searches for similar vectors in ChromaDB based on the provided
        query.

        Args:
            query (VectorDBQuery): The query object containing the search
                vector and the number of top similar vectors to retrieve.
            **kwargs (Any): Additional keyword arguments for ChromaDB query
                operation.

        Returns:
            List[VectorDBQueryResult]: A list of vectors retrieved from the
                storage based on similarity to the query vector.

        Raises:
            RuntimeError: If there is an error during the query process.
        """
        try:
            # Query ChromaDB
            query_kwargs: Dict[str, Any] = {
                'query_embeddings': [query.query_vector],
                'n_results': query.top_k,
                'include': ["embeddings", "metadatas", "distances"],
            }
            query_kwargs.update(kwargs)

            results: "QueryResult" = self._collection.query(**query_kwargs)

            # Convert ChromaDB results to VectorDBQueryResult format
            query_results: List[VectorDBQueryResult] = []

            if results.get("ids") and len(results["ids"]) > 0:
                ids: List[str] = results["ids"][0]

                # Safely extract embeddings with proper type handling
                embeddings_result = results.get("embeddings")
                if embeddings_result and len(embeddings_result) > 0:
                    embeddings_raw = embeddings_result[0]
                    # Convert to List[List[float]] format
                    if embeddings_raw is not None:
                        embeddings: List[List[float]] = []
                        for emb in embeddings_raw:
                            if hasattr(emb, '__iter__'):
                                # Convert any array-like structure to
                                # list of floats
                                embeddings.append([float(x) for x in emb])
                            else:
                                embeddings.append([])
                    else:
                        embeddings = []
                else:
                    embeddings = []

                # Safely extract metadatas with proper type handling
                metadatas_result = results.get("metadatas")
                if metadatas_result and len(metadatas_result) > 0:
                    metadatas_raw = metadatas_result[0]
                    # Convert to List[Dict[str, Any]] format
                    if metadatas_raw is not None:
                        metadatas: List[Dict[str, Any]] = []
                        for meta in metadatas_raw:
                            if meta is not None:
                                # Convert Mapping to Dict
                                metadatas.append(dict(meta))
                            else:
                                metadatas.append({})
                    else:
                        metadatas = []
                else:
                    metadatas = []

                # Safely extract distances with proper type handling
                distances_result = results.get("distances")
                if distances_result and len(distances_result) > 0:
                    distances_raw = distances_result[0]
                    distances: List[float] = (
                        list(distances_raw)
                        if distances_raw is not None
                        else []
                    )
                else:
                    distances = []

                for i, record_id in enumerate(ids):
                    # ChromaDB returns distances (lower is more similar)
                    # Convert to similarity score (higher is more similar)
                    distance: float = (
                        distances[i] if i < len(distances) else 1.0
                    )
                    similarity: float = self._distance_to_similarity(distance)

                    embedding: List[float] = (
                        embeddings[i] if i < len(embeddings) else []
                    )
                    metadata: Dict[str, Any] = (
                        metadatas[i] if i < len(metadatas) else {}
                    )

                    result = VectorDBQueryResult.create(
                        similarity=similarity,
                        vector=embedding,
                        id=record_id,
                        payload=metadata,
                    )
                    query_results.append(result)

            logger.debug(
                f"Query returned {len(query_results)} results from "
                f"ChromaDB collection: {self.collection_name}"
            )
            return query_results

        except Exception as e:
            raise RuntimeError(f"Failed to query ChromaDB: {e}")

    def _distance_to_similarity(self, distance: float) -> float:
        r"""Convert distance to similarity score based on distance metric.

        Args:
            distance (float): Distance value from ChromaDB.

        Returns:
            float: Similarity score (higher means more similar).
        """
        if self.distance == VectorDistance.COSINE:
            # Cosine distance: 0 (identical) to 2 (opposite)
            # Convert to similarity: 1 - (distance / 2)
            return max(0.0, 1.0 - (distance / 2.0))
        elif self.distance == VectorDistance.EUCLIDEAN:
            # L2 distance: 0 (identical) to ∞
            # Convert to similarity: 1 / (1 + distance)
            return 1.0 / (1.0 + distance)
        elif self.distance == VectorDistance.DOT:
            # Inner product: higher values are more similar
            # ChromaDB returns (1 - dot_product) as distance for inner product
            # Convert back to similarity: similarity = 1 - distance
            return max(0.0, 1.0 - distance)
        else:
            # Default: treat as cosine distance
            return max(0.0, 1.0 - distance)

    def clear(self) -> None:
        r"""Removes all vectors from the ChromaDB collection.

        Raises:
            RuntimeError: If there is an error clearing the collection.
        """
        try:
            # Delete the current collection
            self._client.delete_collection(name=self.collection_name)

            # Recreate the collection
            self._collection = self._get_or_create_collection()

            logger.info(
                f"Successfully cleared collection: {self.collection_name}"
            )

        except Exception as e:
            raise RuntimeError(f"Failed to clear ChromaDB collection: {e}")

    def load(self) -> None:
        r"""Load the collection hosted on cloud service.

        For ChromaDB, collections are automatically available when client
        connects, so this method is a no-op.
        """
        # ChromaDB collections are automatically available when client connects
        # No explicit loading is required
        pass

    def delete_collection(self) -> None:
        r"""Deletes the entire collection from ChromaDB.

        Raises:
            RuntimeError: If there is an error deleting the collection.
        """
        try:
            self._client.delete_collection(name=self.collection_name)
            logger.info(
                f"Successfully deleted collection: {self.collection_name}"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to delete ChromaDB collection: {e}")

    @property
    def client(self) -> "ClientAPI":
        r"""Provides access to the underlying ChromaDB client.

        Returns:
            chromadb.Client: The ChromaDB client instance.
        """
        return self._client

    @property
    def collection(self) -> "Collection":
        r"""Provides access to the underlying ChromaDB collection.

        Returns:
            ChromaDB collection instance.
        """
        return self._collection
