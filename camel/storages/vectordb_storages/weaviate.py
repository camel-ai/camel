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
import json
import math
import re
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Union,
    cast,
)

if TYPE_CHECKING:
    from weaviate import WeaviateClient

from camel.logger import get_logger
from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)
from camel.utils import dependencies_required

logger = get_logger(__name__)


# Type definitions for configuration options
ConnectionType = Literal["local", "cloud", "embedded", "custom"]
VectorIndexType = Literal["hnsw", "flat"]
DistanceMetric = Literal["cosine", "dot", "l2-squared", "hamming", "manhattan"]


class WeaviateStorage(BaseVectorStorage):
    r"""An implementation of the `BaseVectorStorage` for interacting with
    Weaviate, a cloud-native vector search engine.

    This class provides multiple ways to connect to Weaviate instances:
    - Weaviate Cloud (WCD)
    - Local Docker/Kubernetes instances
    - Embedded Weaviate
    - Custom connection parameters

    Args:
        vector_dim (int): The dimension of storing vectors.
        collection_name (Optional[str], optional): Name for the collection in
            Weaviate. If not provided, generates a unique name based on current
            timestamp. (default: :obj:`None`)
        connection_type (ConnectionType, optional): Type of connection to use.
            Supported types: 'local', 'cloud', 'embedded', 'custom'.
            (default: :obj:`"local"`)

        # Weaviate Cloud parameters
        wcd_cluster_url (Optional[str], optional): Weaviate Cloud cluster URL.
            Required when connection_type='cloud'.
        wcd_api_key (Optional[str], optional): Weaviate Cloud API key.
            Required when connection_type='cloud'.

        # Local instance parameters
        local_host (str, optional): Local Weaviate host.
            (default: :obj:`"localhost"`)
        local_port (int, optional): Local Weaviate HTTP port.
            (default: :obj:`8080`)
        local_grpc_port (int, optional): Local Weaviate gRPC port.
            (default: :obj:`50051`)
        local_auth_credentials (Optional[Union[str, Any]], optional):
            Authentication credentials for local instance. Can be an API key
            string or Auth object. (default: :obj:`None`)

        # Embedded Weaviate parameters
        embedded_hostname (str, optional): Embedded instance hostname.
            (default: :obj:`"127.0.0.1"`)
        embedded_port (int, optional): Embedded instance HTTP port.
            (default: :obj:`8079`)
        embedded_grpc_port (int, optional): Embedded instance gRPC port.
            (default: :obj:`50050`)
        embedded_version (Optional[str], optional): Weaviate version for
            embedded instance. If None, uses the default version.
            (default: :obj:`None`)
        embedded_persistence_data_path (Optional[str], optional): Directory
            for embedded database files. (default: :obj:`None`)
        embedded_binary_path (Optional[str], optional): Directory for
            Weaviate binary. (default: :obj:`None`)
        embedded_environment_variables (Optional[Dict[str, str]], optional):
            Environment variables for embedded instance. (default: :obj:`None`)

        # Custom connection parameters
        custom_http_host (Optional[str], optional): Custom HTTP host.
        custom_http_port (Optional[int], optional): Custom HTTP port.
        custom_http_secure (Optional[bool], optional): Use HTTPS.
        custom_grpc_host (Optional[str], optional): Custom gRPC host.
        custom_grpc_port (Optional[int], optional): Custom gRPC port.
        custom_grpc_secure (Optional[bool], optional): Use secure gRPC.
        custom_auth_credentials (Optional[Any], optional): Custom auth.

        # Vector index configuration parameters
        vector_index_type (VectorIndexType, optional): Vector index type.
            Supported types: 'hnsw', 'flat'. (default: :obj:`"hnsw"`)
        distance_metric (DistanceMetric, optional): Distance metric for vector
            similarity. Supported metrics: 'cosine', 'dot', 'l2-squared',
            'hamming', 'manhattan'. (default: :obj:`"cosine"`)

        # Common parameters for all connection types
        headers (Optional[Dict[str, str]], optional): Additional headers for
            third-party API keys (e.g., OpenAI, Cohere). (default: :obj:`None`)
        additional_config (Optional[Any], optional): Advanced configuration
            options like timeouts. (default: :obj:`None`)
        skip_init_checks (bool, optional): Skip initialization checks.
            (default: :obj:`False`)

    Raises:
        ImportError: If `weaviate` package is not installed.
        ValueError: If connection parameters are invalid or missing.
        RuntimeError: If there's an error setting up the collection.

    Note:
        This implementation supports synchronous operations only.
        The client connection is automatically handled and closed when the
        storage instance is destroyed.
    """

    @dependencies_required('weaviate')
    def __init__(
        self,
        vector_dim: int,
        collection_name: Optional[str] = None,
        connection_type: ConnectionType = "local",
        # Weaviate Cloud parameters
        wcd_cluster_url: Optional[str] = None,
        wcd_api_key: Optional[str] = None,
        # Local instance parameters
        local_host: str = "localhost",
        local_port: int = 8080,
        local_grpc_port: int = 50051,
        local_auth_credentials: Optional[Union[str, Any]] = None,
        # Embedded Weaviate parameters
        embedded_hostname: str = "127.0.0.1",
        embedded_port: int = 8079,
        embedded_grpc_port: int = 50050,
        embedded_version: Optional[str] = None,
        embedded_persistence_data_path: Optional[str] = None,
        embedded_binary_path: Optional[str] = None,
        embedded_environment_variables: Optional[Dict[str, str]] = None,
        # Custom connection parameters
        custom_http_host: Optional[str] = None,
        custom_http_port: Optional[int] = None,
        custom_http_secure: Optional[bool] = None,
        custom_grpc_host: Optional[str] = None,
        custom_grpc_port: Optional[int] = None,
        custom_grpc_secure: Optional[bool] = None,
        custom_auth_credentials: Optional[Any] = None,
        # Vector index configuration parameters
        vector_index_type: VectorIndexType = "hnsw",
        distance_metric: DistanceMetric = "cosine",
        # Common parameters
        headers: Optional[Dict[str, str]] = None,
        additional_config: Optional[Any] = None,
        skip_init_checks: bool = False,
        **kwargs: Any,
    ) -> None:
        self.vector_dim = vector_dim
        self.collection_name = (
            collection_name or self._generate_collection_name()
        )

        # Store vector index configuration
        self.vector_index_type: VectorIndexType = vector_index_type
        self.distance_metric: DistanceMetric = distance_metric

        # Store connection type configuration
        self.connection_type: ConnectionType = connection_type

        # Store connection parameters for later use
        self._connection_params = {
            'wcd_cluster_url': wcd_cluster_url,
            'wcd_api_key': wcd_api_key,
            'local_host': local_host,
            'local_port': local_port,
            'local_grpc_port': local_grpc_port,
            'local_auth_credentials': local_auth_credentials,
            'embedded_hostname': embedded_hostname,
            'embedded_port': embedded_port,
            'embedded_grpc_port': embedded_grpc_port,
            'embedded_version': embedded_version,
            'embedded_persistence_data_path': embedded_persistence_data_path,
            'embedded_binary_path': embedded_binary_path,
            'embedded_environment_variables': embedded_environment_variables,
            'custom_http_host': custom_http_host,
            'custom_http_port': custom_http_port,
            'custom_http_secure': custom_http_secure,
            'custom_grpc_host': custom_grpc_host,
            'custom_grpc_port': custom_grpc_port,
            'custom_grpc_secure': custom_grpc_secure,
            'custom_auth_credentials': custom_auth_credentials,
            'headers': headers,
            'additional_config': additional_config,
            'skip_init_checks': skip_init_checks,
            **kwargs,
        }

        # Store original collection creation kwargs for clear() method
        self._original_collection_kwargs = kwargs.copy()

        # Create client using the new unified approach
        self._client = self._get_connection_client()
        logger.info(
            f"Created Weaviate client with connection type: "
            f"{self.connection_type}"
        )

        self._check_and_create_collection(**kwargs)

    def _get_connection_client(self) -> "WeaviateClient":
        r"""Get Weaviate client based on connection type and user settings."""
        import weaviate

        # Map connection types to handler methods
        connection_handlers: Dict[ConnectionType, Any] = {
            'cloud': self._create_cloud_client,
            'local': self._create_local_client,
            'embedded': self._create_embedded_client,
            'custom': self._create_custom_client,
        }

        # Get connection handler
        handler = connection_handlers[self.connection_type]

        try:
            return handler(weaviate)
        except Exception as e:
            logger.error(
                f"Failed to create {self.connection_type} client: {e}"
            )
            raise

    def _create_cloud_client(self, weaviate_module: Any) -> "WeaviateClient":
        r"""Create a Weaviate Cloud client."""
        cluster_url = self._connection_params.get('wcd_cluster_url')
        api_key = self._connection_params.get('wcd_api_key')

        if not cluster_url:
            raise ValueError(
                "wcd_cluster_url is required for cloud connection"
            )
        if not api_key:
            raise ValueError("wcd_api_key is required for cloud connection")

        return weaviate_module.connect_to_weaviate_cloud(
            cluster_url=cluster_url,
            auth_credentials=api_key,
            headers=self._connection_params.get('headers'),
            additional_config=self._connection_params.get('additional_config'),
            skip_init_checks=self._connection_params.get(
                'skip_init_checks', False
            ),
        )

    def _create_local_client(self, weaviate_module: Any) -> "WeaviateClient":
        r"""Create a local Weaviate client."""
        return weaviate_module.connect_to_local(
            host=self._connection_params.get('local_host', 'localhost'),
            port=self._connection_params.get('local_port', 8080),
            grpc_port=self._connection_params.get('local_grpc_port', 50051),
            headers=self._connection_params.get('headers'),
            additional_config=self._connection_params.get('additional_config'),
            skip_init_checks=self._connection_params.get(
                'skip_init_checks', False
            ),
            auth_credentials=self._connection_params.get(
                'local_auth_credentials'
            ),
        )

    def _create_embedded_client(
        self, weaviate_module: Any
    ) -> "WeaviateClient":
        r"""Create an embedded Weaviate client."""
        embedded_kwargs = {
            'hostname': self._connection_params.get(
                'embedded_hostname', '127.0.0.1'
            ),
            'port': self._connection_params.get('embedded_port', 8079),
            'grpc_port': self._connection_params.get(
                'embedded_grpc_port', 50050
            ),
            'headers': self._connection_params.get('headers'),
            'additional_config': self._connection_params.get(
                'additional_config'
            ),
        }

        # Add optional embedded parameters
        if self._connection_params.get('embedded_version') is not None:
            embedded_kwargs['version'] = self._connection_params[
                'embedded_version'
            ]
        if (
            self._connection_params.get('embedded_persistence_data_path')
            is not None
        ):
            embedded_kwargs['persistence_data_path'] = self._connection_params[
                'embedded_persistence_data_path'
            ]
        if self._connection_params.get('embedded_binary_path') is not None:
            embedded_kwargs['binary_path'] = self._connection_params[
                'embedded_binary_path'
            ]
        if (
            self._connection_params.get('embedded_environment_variables')
            is not None
        ):
            embedded_kwargs['environment_variables'] = self._connection_params[
                'embedded_environment_variables'
            ]

        return weaviate_module.connect_to_embedded(**embedded_kwargs)

    def _create_custom_client(self, weaviate_module: Any) -> "WeaviateClient":
        r"""Create a custom Weaviate client."""
        # Validate required custom parameters
        required_params = [
            'custom_http_host',
            'custom_http_port',
            'custom_http_secure',
            'custom_grpc_host',
            'custom_grpc_port',
            'custom_grpc_secure',
        ]

        for param in required_params:
            if self._connection_params.get(param) is None:
                raise ValueError(f"{param} is required for custom connection")

        return weaviate_module.connect_to_custom(
            http_host=self._connection_params['custom_http_host'],
            http_port=self._connection_params['custom_http_port'],
            http_secure=self._connection_params['custom_http_secure'],
            grpc_host=self._connection_params['custom_grpc_host'],
            grpc_port=self._connection_params['custom_grpc_port'],
            grpc_secure=self._connection_params['custom_grpc_secure'],
            headers=self._connection_params.get('headers'),
            additional_config=self._connection_params.get('additional_config'),
            auth_credentials=self._connection_params.get(
                'custom_auth_credentials'
            ),
            skip_init_checks=self._connection_params.get(
                'skip_init_checks', False
            ),
        )

    def __del__(self):
        r"""Clean up client connection."""
        try:
            if hasattr(self, '_client') and self._client is not None:
                self._client.close()
                logger.debug("Closed Weaviate client connection")
        except Exception as e:
            logger.warning(f"Error closing Weaviate client: {e}")

    def close(self) -> None:
        r"""Explicitly close the client connection."""
        if self._client is not None:
            self._client.close()
            logger.info("Explicitly closed Weaviate client connection")

    def _generate_collection_name(self) -> str:
        r"""Generate a collection name if user doesn't provide one."""
        timestamp = datetime.now().isoformat()
        # Weaviate collection names must start with uppercase and be valid
        # GraphQL names
        valid_name = "Collection_" + re.sub(r'[^a-zA-Z0-9_]', '_', timestamp)
        return valid_name

    def _check_and_create_collection(self, **kwargs: Any) -> None:
        r"""Check if collection exists and create if it doesn't."""
        if not self._collection_exists(self.collection_name):
            self._create_collection(**kwargs)

    def _collection_exists(self, collection_name: str) -> bool:
        r"""Check if the collection exists."""
        try:
            collection = self._client.collections.get(collection_name)
            collection.config.get()
            return True
        except Exception:
            return False

    def _get_vector_index_config(self, **kwargs: Any) -> Any:
        r"""Get vector index configuration based on user settings."""
        import weaviate.classes.config as wvc

        # Map distance metrics - type safety guaranteed by Literal
        distance_metric_mapping: Dict[DistanceMetric, Any] = {
            'cosine': wvc.VectorDistances.COSINE,
            'dot': wvc.VectorDistances.DOT,
            'l2-squared': wvc.VectorDistances.L2_SQUARED,
            'hamming': wvc.VectorDistances.HAMMING,
            'manhattan': wvc.VectorDistances.MANHATTAN,
        }

        # Get distance metric - no need for None check due to Literal typing
        distance_metric = distance_metric_mapping[self.distance_metric]

        # Configure vector index based on type
        if self.vector_index_type == 'hnsw':
            return wvc.Configure.VectorIndex.hnsw(
                distance_metric=distance_metric,
                **kwargs,
            )
        else:  # must be 'flat' due to Literal typing
            return wvc.Configure.VectorIndex.flat(
                distance_metric=distance_metric,
                **kwargs,
            )

    def _create_collection(self, **kwargs: Any) -> None:
        r"""Create a new collection in Weaviate."""
        import weaviate.classes.config as wvc

        # Separate vector index kwargs from general kwargs to avoid conflicts
        vector_index_kwargs = {}
        collection_kwargs = {}

        # Known vector index parameters
        vector_index_params = {
            'ef_construction',
            'max_connections',
            'ef',
            'dynamic_ef_min',
            'dynamic_ef_max',
            'dynamic_ef_factor',
            'vector_cache_max_objects',
            'flat_search_cutoff',
            'cleanup_interval_seconds',
            'pq_enabled',
            'pq_segments',
            'pq_centroids',
            'pq_training_limit',
            'pq_encoder',
        }

        for key, value in kwargs.items():
            if key in vector_index_params:
                vector_index_kwargs[key] = value
            else:
                collection_kwargs[key] = value

        self._client.collections.create(
            name=self.collection_name,
            vectorizer_config=wvc.Configure.Vectorizer.none(),
            properties=[
                wvc.Property(name="payload", data_type=wvc.DataType.TEXT),
            ],
            vector_index_config=self._get_vector_index_config(
                **vector_index_kwargs
            ),
            **collection_kwargs,
        )

    def add(
        self,
        records: List[VectorRecord],
        **kwargs: Any,
    ) -> None:
        r"""Saves a list of vector records to the storage.

        Args:
            records (List[VectorRecord]): List of vector records to be saved.
            **kwargs (Any): Additional keyword arguments.

        Raises:
            RuntimeError: If there is an error during the saving process.
        """
        if not records:
            return

        try:
            collection = self._client.collections.get(self.collection_name)

            with collection.batch.dynamic() as batch:
                for record in records:
                    payload_str = (
                        json.dumps(record.payload) if record.payload else ""
                    )
                    batch.add_object(
                        properties={"payload": payload_str},
                        vector=record.vector,
                        uuid=record.id,
                        **kwargs,
                    )
            logger.debug(
                f"Successfully added vectors to Weaviate collection: "
                f"{self.collection_name}"
            )

        except Exception as e:
            raise RuntimeError(f"Failed to add vectors to Weaviate: {e}")

    def delete(
        self,
        ids: List[str],
        **kwargs: Any,
    ) -> None:
        r"""Deletes a list of vectors identified by their IDs from the storage.

        Args:
            ids (List[str]): List of unique identifiers for the vectors to be
                deleted.
            **kwargs (Any): Additional keyword arguments.

        Raises:
            RuntimeError: If there is an error during the deletion process.
        """
        if not ids:
            return

        try:
            collection = self._client.collections.get(self.collection_name)
            from weaviate.classes.query import Filter

            collection.data.delete_many(
                where=Filter.by_id().contains_any(ids), **kwargs
            )
            logger.debug(
                f"Successfully deleted vectors in Weaviate: "
                f"{self.collection_name}"
            )

        except Exception as e:
            raise RuntimeError(f"Failed to delete vectors from Weaviate: {e}")

    def _calculate_similarity_from_distance(
        self, distance: Optional[float]
    ) -> float:
        r"""Calculate similarity score based on distance metric.

        Args:
            distance (Optional[float]): The distance value from Weaviate.

        Returns:
            float: Normalized similarity score between 0 and 1.
        """
        # Return 0.0 if distance is not available
        if distance is None:
            return 0.0

        # Calculate similarity based on distance metric
        if self.distance_metric == "cosine":
            # Cosine: 0 (identical) to 2 (opposite)
            # Convert to similarity: 1 - (distance / 2)
            return max(0.0, 1.0 - (distance / 2.0))

        elif self.distance_metric == "dot":
            # Dot product: Weaviate returns -dot,
            # smaller (more negative) is more similar
            # Use sigmoid function to normalize to [0,1] range
            # For dot product, we use: 1 / (1 + exp(distance))
            return 1.0 / (1.0 + math.exp(distance))

        elif self.distance_metric in ["l2-squared", "manhattan"]:
            # L2-squared and Manhattan: 0 (identical) to ∞
            # Convert to similarity using: 1 / (1 + distance)
            # This provides a smoother decay than exponential
            return 1.0 / (1.0 + distance)

        elif self.distance_metric == "hamming":
            # Hamming: 0 (identical) to vector_dim (completely different)
            # Convert to similarity: 1 - (distance / vector_dim)
            return max(0.0, 1.0 - (distance / self.vector_dim))

        else:
            # Unknown metric, return 0.0
            return 0.0

    def status(self) -> VectorDBStatus:
        r"""Returns status of the vector database.

        Returns:
            VectorDBStatus: The vector database status.
        """
        try:
            collection = self._client.collections.get(self.collection_name)
            objects = collection.aggregate.over_all(total_count=True)

            vector_count = (
                objects.total_count if objects.total_count is not None else 0
            )

            return VectorDBStatus(
                vector_dim=self.vector_dim, vector_count=vector_count
            )

        except Exception as e:
            logger.warning(f"Failed to get status from Weaviate: {e}")
            return VectorDBStatus(vector_dim=self.vector_dim, vector_count=0)

    def query(
        self,
        query: VectorDBQuery,
        **kwargs: Any,
    ) -> List[VectorDBQueryResult]:
        r"""Searches for similar vectors in the storage based on the provided
        query.

        Args:
            query (VectorDBQuery): The query object containing the search
                vector and the number of top similar vectors to retrieve.
            **kwargs (Any): Additional keyword arguments.

        Returns:
            List[VectorDBQueryResult]: A list of vectors retrieved from the
                storage based on similarity to the query vector.
        """
        from weaviate.classes.query import MetadataQuery

        try:
            collection = self._client.collections.get(self.collection_name)

            response = collection.query.near_vector(
                near_vector=query.query_vector,
                limit=query.top_k,
                include_vector=True,
                return_metadata=MetadataQuery(distance=True),
                **kwargs,
            )

            results = []
            for obj in response.objects:
                # Calculate similarity score based on distance metric
                similarity = self._calculate_similarity_from_distance(
                    obj.metadata.distance
                )

                # Handle payload
                payload = None
                if obj.properties.get('payload'):
                    payload_value = obj.properties['payload']
                    if isinstance(payload_value, str):
                        try:
                            payload = json.loads(payload_value)
                        except (json.JSONDecodeError, TypeError):
                            payload = {"raw": payload_value}
                    else:
                        payload = {"raw": str(payload_value)}

                # Handle vector data
                # In newer versions of Weaviate, obj.vector returns a dict
                # with 'default' key

                vector: List[float] = []
                if hasattr(obj, 'vector') and obj.vector is not None:
                    # New format: {'default': [vector_values]}
                    vector_data = obj.vector.get('default', [])
                    if (
                        vector_data
                        and isinstance(vector_data, list)
                        and len(vector_data) > 0
                        and isinstance(vector_data[0], float)
                    ):
                        vector = cast(List[float], vector_data)
                    else:
                        # unsupported vector data format
                        vector = []
                else:
                    vector = []

                result = VectorDBQueryResult.create(
                    similarity=similarity,
                    vector=vector,
                    id=str(obj.uuid),
                    payload=payload,
                )
                results.append(result)

            return results

        except Exception as e:
            raise RuntimeError(f"Failed to query vectors from Weaviate: {e}")

    def clear(self) -> None:
        r"""Remove all vectors from the storage."""
        try:
            self._client.collections.delete(self.collection_name)
            self._create_collection(**self._original_collection_kwargs)
        except Exception as e:
            raise RuntimeError(f"Failed to clear Weaviate collection: {e}")

    def load(self) -> None:
        r"""Load the collection hosted on cloud service."""
        # For Weaviate, collections are automatically available when client
        # connects
        pass

    @property
    def client(self) -> "WeaviateClient":
        r"""Provides access to the underlying vector database client."""
        return self._client
