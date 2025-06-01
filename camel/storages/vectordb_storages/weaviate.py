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
from typing import TYPE_CHECKING, Any, List, Optional, Union

if TYPE_CHECKING:
    from weaviate import WeaviateAsyncClient, WeaviateClient

from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)
from camel.utils import dependencies_required

logger = logging.getLogger(__name__)


class WeaviateStorage(BaseVectorStorage):
    r"""An implementation of the `BaseVectorStorage` for interacting with
    Weaviate, a cloud-native vector search engine.

    Args:
        client (Union[WeaviateClient, WeaviateAsyncClient]):
          A pre-configured Weaviate client instance. Can be either
            synchronous (WeaviateClient) or asynchronous (WeaviateAsyncClient).
        vector_dim (int): The dimension of storing vectors.
        collection_name (Optional[str], optional): Name for the collection in
            the Weaviate. If not provided, set it to the current time with iso
            format. (default: :obj:`None`)

    Raises:
        ImportError: If `weaviate` package is not installed.
        ValueError: If client is None or invalid.
        RuntimeError: If there's an error setting up the collection.

    Note:
        This implementation currently supports synchronous operations only.
        If an async client is provided, it will be used but operations will
        be performed synchronously.
    """

    @dependencies_required('weaviate')
    def __init__(
        self,
        client: Union["WeaviateClient", "WeaviateAsyncClient"],
        vector_dim: int,
        collection_name: Optional[str] = None,
    ) -> None:
        if client is None:
            raise ValueError("Weaviate client cannot be None")

        self._client: Union["WeaviateClient", "WeaviateAsyncClient"] = client
        self.vector_dim = vector_dim
        self.collection_name = (
            collection_name or self._generate_collection_name()
        )

        self._check_and_create_collection()

    def _generate_collection_name(self) -> str:
        """Generate a collection name if user doesn't provide one."""
        timestamp = datetime.now().isoformat()
        # Weaviate collection names must start with uppercase and be valid
        # GraphQL names
        valid_name = "Collection_" + re.sub(r'[^a-zA-Z0-9_]', '_', timestamp)
        return valid_name

    def _check_and_create_collection(self) -> None:
        """Check if collection exists and create if it doesn't."""
        if not self._collection_exists(self.collection_name):
            self._create_collection()

    def _collection_exists(self, collection_name: str) -> bool:
        """Check if the collection exists."""
        try:
            collection = self._client.collections.get(collection_name)
            collection.config.get()
            return True
        except Exception:
            return False

    def _create_collection(self) -> None:
        """Create a new collection in Weaviate."""
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

            with collection.batch.dynamic() as batch:  # type: ignore[union-attr]
                for record in records:
                    payload_str = (
                        json.dumps(record.payload) if record.payload else ""
                    )
                    batch.add_object(
                        properties={"payload": payload_str},
                        vector=record.vector,
                        uuid=record.id,
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
            # Handle both sync and async return types
            vector_count = 0
            if hasattr(objects, 'total_count'):
                vector_count = (
                    objects.total_count if objects.total_count else 0
                )  # type: ignore[union-attr]

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
        try:
            collection = self._client.collections.get(self.collection_name)

            response = collection.query.near_vector(
                near_vector=query.query_vector,
                limit=query.top_k,
                include_vector=True,
                return_metadata=['distance'],
            )

            results = []
            # Handle both sync and async response types
            objects = getattr(response, 'objects', [])  # type: ignore[union-attr]
            for obj in objects:
                distance = (
                    obj.metadata.distance
                    if obj.metadata.distance is not None
                    else 0.0
                )
                similarity = 1.0 - distance

                payload = None
                payload_value = obj.properties.get('payload')
                if payload_value:
                    try:
                        # Handle different payload types
                        if isinstance(payload_value, str):
                            payload = json.loads(payload_value)
                        else:
                            payload = {"raw": str(payload_value)}
                    except (json.JSONDecodeError, TypeError):
                        payload = {"raw": str(payload_value)}

                # Ensure vector is a list of floats
                vector_data = obj.vector or []
                if isinstance(vector_data, dict):
                    # Handle case where vector is a dict
                    vector_list = []
                    for v in vector_data.values():
                        if isinstance(v, list):
                            vector_list.extend(v)
                        else:
                            vector_list.append(float(v))
                elif isinstance(vector_data, list):
                    vector_list = [float(x) for x in vector_data]
                else:
                    vector_list = []

                result = VectorDBQueryResult.create(
                    similarity=similarity,
                    vector=vector_list,
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
    def client(self) -> Union["WeaviateClient", "WeaviateAsyncClient"]:
        r"""Provides access to the underlying vector database client."""
        return self._client
