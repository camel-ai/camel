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
import logging
import re
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

if TYPE_CHECKING:
    from weaviate import WeaviateClient

from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)
from camel.utils import dependencies_required

logger = logging.getLogger(__name__)


class WeaviateConnectionType(Enum):
    r"""Supported Weaviate connection types."""

    CLOUD = "cloud"
    LOCAL = "local"
    EMBEDDED = "embedded"
    CUSTOM = "custom"


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
        connection_type (WeaviateConnectionType or str, optional): Type of
            connection to use. Options: 'cloud', 'local', 'embedded', 'custom'.
            (default: :obj:`WeaviateConnectionType.LOCAL`)

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
        connection_type: Union[
            WeaviateConnectionType, str
        ] = WeaviateConnectionType.LOCAL,
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

        # Handle string connection type
        if isinstance(connection_type, str):
            try:
                connection_type = WeaviateConnectionType(
                    connection_type.lower()
                )
            except ValueError:
                raise ValueError(
                    f"Invalid connection_type: {connection_type}. "
                    f"Must be one of: "
                    f"{[t.value for t in WeaviateConnectionType]}"
                )

        self.connection_type = connection_type

        # Create client based on connection type
        self._client = self._create_client(
            connection_type=connection_type,
            wcd_cluster_url=wcd_cluster_url,
            wcd_api_key=wcd_api_key,
            local_host=local_host,
            local_port=local_port,
            local_grpc_port=local_grpc_port,
            local_auth_credentials=local_auth_credentials,
            embedded_hostname=embedded_hostname,
            embedded_port=embedded_port,
            embedded_grpc_port=embedded_grpc_port,
            embedded_version=embedded_version,
            embedded_persistence_data_path=embedded_persistence_data_path,
            embedded_binary_path=embedded_binary_path,
            embedded_environment_variables=embedded_environment_variables,
            custom_http_host=custom_http_host,
            custom_http_port=custom_http_port,
            custom_http_secure=custom_http_secure,
            custom_grpc_host=custom_grpc_host,
            custom_grpc_port=custom_grpc_port,
            custom_grpc_secure=custom_grpc_secure,
            custom_auth_credentials=custom_auth_credentials,
            headers=headers,
            additional_config=additional_config,
            skip_init_checks=skip_init_checks,
            **kwargs,
        )
        logger.info(
            f"Created Weaviate client with connection type: "
            f"{connection_type.value}"
        )

        self._check_and_create_collection()

    def _create_client(
        self, connection_type: WeaviateConnectionType, **kwargs: Any
    ) -> "WeaviateClient":
        r"""Create a Weaviate client based on connection type
        and parameters."""

        import weaviate

        if connection_type == WeaviateConnectionType.CLOUD:
            return self._create_cloud_client(weaviate, **kwargs)
        elif connection_type == WeaviateConnectionType.LOCAL:
            return self._create_local_client(weaviate, **kwargs)
        elif connection_type == WeaviateConnectionType.EMBEDDED:
            return self._create_embedded_client(weaviate, **kwargs)
        elif connection_type == WeaviateConnectionType.CUSTOM:
            return self._create_custom_client(weaviate, **kwargs)
        else:
            raise ValueError(f"Unsupported connection type: {connection_type}")

    def _create_cloud_client(
        self, weaviate_module: Any, **kwargs: Any
    ) -> "WeaviateClient":
        r"""Create a Weaviate Cloud client."""
        cluster_url = kwargs.get('wcd_cluster_url')
        api_key = kwargs.get('wcd_api_key')

        if not cluster_url:
            raise ValueError(
                "wcd_cluster_url is required for cloud connection"
            )
        if not api_key:
            raise ValueError("wcd_api_key is required for cloud connection")

        return weaviate_module.connect_to_weaviate_cloud(
            cluster_url=cluster_url,
            auth_credentials=api_key,
            headers=kwargs.get('headers'),
            additional_config=kwargs.get('additional_config'),
            skip_init_checks=kwargs.get('skip_init_checks', False),
        )

    def _create_local_client(
        self, weaviate_module: Any, **kwargs: Any
    ) -> "WeaviateClient":
        r"""Create a local Weaviate client."""
        return weaviate_module.connect_to_local(
            host=kwargs.get('local_host', 'localhost'),
            port=kwargs.get('local_port', 8080),
            grpc_port=kwargs.get('local_grpc_port', 50051),
            headers=kwargs.get('headers'),
            additional_config=kwargs.get('additional_config'),
            skip_init_checks=kwargs.get('skip_init_checks', False),
            auth_credentials=kwargs.get('local_auth_credentials'),
        )

    def _create_embedded_client(
        self, weaviate_module: Any, **kwargs: Any
    ) -> "WeaviateClient":
        r"""Create an embedded Weaviate client."""
        embedded_kwargs = {
            'hostname': kwargs.get('embedded_hostname', '127.0.0.1'),
            'port': kwargs.get('embedded_port', 8079),
            'grpc_port': kwargs.get('embedded_grpc_port', 50050),
            'headers': kwargs.get('headers'),
            'additional_config': kwargs.get('additional_config'),
        }

        # Add optional embedded parameters
        if kwargs.get('embedded_version') is not None:
            embedded_kwargs['version'] = kwargs['embedded_version']
        if kwargs.get('embedded_persistence_data_path') is not None:
            embedded_kwargs['persistence_data_path'] = kwargs[
                'embedded_persistence_data_path'
            ]
        if kwargs.get('embedded_binary_path') is not None:
            embedded_kwargs['binary_path'] = kwargs['embedded_binary_path']
        if kwargs.get('embedded_environment_variables') is not None:
            embedded_kwargs['environment_variables'] = kwargs[
                'embedded_environment_variables'
            ]

        return weaviate_module.connect_to_embedded(**embedded_kwargs)

    def _create_custom_client(
        self, weaviate_module: Any, **kwargs: Any
    ) -> "WeaviateClient":
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
            if kwargs.get(param) is None:
                raise ValueError(f"{param} is required for custom connection")

        return weaviate_module.connect_to_custom(
            http_host=kwargs['custom_http_host'],
            http_port=kwargs['custom_http_port'],
            http_secure=kwargs['custom_http_secure'],
            grpc_host=kwargs['custom_grpc_host'],
            grpc_port=kwargs['custom_grpc_port'],
            grpc_secure=kwargs['custom_grpc_secure'],
            headers=kwargs.get('headers'),
            additional_config=kwargs.get('additional_config'),
            auth_credentials=kwargs.get('custom_auth_credentials'),
            skip_init_checks=kwargs.get('skip_init_checks', False),
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

    def _check_and_create_collection(self) -> None:
        r"""Check if collection exists and create if it doesn't."""
        if not self._collection_exists(self.collection_name):
            self._create_collection()

    def _collection_exists(self, collection_name: str) -> bool:
        r"""Check if the collection exists."""
        try:
            collection = self._client.collections.get(collection_name)
            collection.config.get()
            return True
        except Exception:
            return False

    def _create_collection(self) -> None:
        r"""Create a new collection in Weaviate."""
        import weaviate.classes.config as wvc

        self._client.collections.create(
            name=self.collection_name,
            vectorizer_config=wvc.Configure.Vectorizer.none(),
            properties=[
                wvc.Property(name="payload", data_type=wvc.DataType.TEXT),
            ],
            vector_index_config=wvc.Configure.VectorIndex.hnsw(
                distance_metric=wvc.VectorDistances.COSINE
            ),
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

            collection.data.delete_many(where=Filter.by_id().contains_any(ids))
            logger.debug(
                f"Successfully deleted vectors in Weaviate: "
                f"{self.collection_name}"
            )

        except Exception as e:
            raise RuntimeError(f"Failed to delete vectors from Weaviate: {e}")

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
                return_metadata=MetadataQuery(certainty=True),
            )

            results = []
            for obj in response.objects:
                # calculate similarity score
                similarity = (
                    obj.metadata.certainty
                    if obj.metadata.certainty is not None
                    else 0.0
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
            self._create_collection()
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
