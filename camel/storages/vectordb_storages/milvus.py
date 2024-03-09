# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)

logger = logging.getLogger(__name__)


class MilvusStorage(BaseVectorStorage):
    r"""An implementation of the `BaseVectorStorage` for interacting with
    Milvus, a vector search engine.

    The detailed information about Milvus is available at:
    `Milvus <https://milvus.io/docs/overview.md/>`_

    Args:
        vector_dim (int): The dimenstion of storing vectors.
        collection_name (Optional[str], optional): Name for the collection in
            the Milvus. If not provided, set it to the current time with iso
            format. (default: :obj:`None`)
        url_and_api_key (Tuple[str, str]]): Tuple containing
            the URL and API key for connecting to a remote Milvus instance.
            (default: :obj:`None`)
        **kwargs (Any): Additional keyword arguments for initializing
            `MilvusClient`.
    """

    def __init__(
        self,
        vector_dim: int,
        url_and_api_key: Tuple[str, str],
        collection_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        try:
            from pymilvus import MilvusClient
        except ImportError as exc:
            raise ImportError(
                "Please install `pymilvus` first. You can install it by "
                "running `pip install pymilvus`.") from exc

        self._client: MilvusClient
        self._create_client(url_and_api_key, **kwargs)

        self.vector_dim = vector_dim
        self.collection_name = (collection_name
                                or self._generate_collection_name())

        self._check_and_create_collection()

    def _create_client(
        self,
        url_and_api_key: Tuple[str, str],
        **kwargs: Any,
    ) -> None:
        from pymilvus import MilvusClient

        self._client = MilvusClient(
            uri=url_and_api_key[0],
            token=url_and_api_key[1],
            **kwargs,
        )

    def _check_and_create_collection(self) -> None:
        if self._collection_exists(self.collection_name):
            in_dim = self._get_collection_info(
                self.collection_name)["vector_dim"]
            if in_dim != self.vector_dim:
                # The name of collection has to be confirmed by the user
                raise ValueError(
                    "Vector dimension of the existing collection "
                    f'"{self.collection_name}" ({in_dim}) is different from '
                    f"the given embedding dim ({self.vector_dim}).")
        else:
            self._create_collection(collection_name=self.collection_name, )

    def _create_collection(
        self,
        collection_name: str,
        **kwargs: Any,
    ) -> None:
        r"""Creates a new collection in the database.

        Args:
            collection_name (str): Name of the collection to be created.
            **kwargs (Any): Additional keyword arguments.
        """
        self._client.create_collection(
            collection_name=collection_name,
            dimension=self.vector_dim,
            **kwargs,
        )

    def _delete_collection(
        self,
        collection_name: str,
    ) -> None:
        r"""Deletes an existing collection from the database.

        Args:
            collection (str): Name of the collection to be deleted.
            **kwargs (Any): Additional keyword arguments.
        """
        self._client.drop_collection(collection_name=collection_name)

    def _collection_exists(self, collection_name: str) -> bool:
        r"""Returns wether the collection exists in the database"""
        for c in self._client.list_collections():
            if collection_name == c.name:
                return True
        return False

    def _generate_collection_name(self) -> str:
        r"""Generates a collection name if user doesn't provide"""
        return datetime.now().isoformat()

    def _get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        r"""Retrieves details of an existing collection.

        Args:
            collection_name (str): Name of the collection to be checked.

        Returns:
            Dict[str, Any]: A dictionary containing details about the
                collection.
        """
        from pymilvus import Collection

        collection = Collection(collection_name)
        return {
            # Return the schema.CollectionSchema of the collection.
            "schema": collection.schema,
            # Return the description of the collection.
            "description": collection.description,
            # Return the name of the collection.
            "name": collection.name,
            # Return the boolean value that indicates if the collection is
            # empty.
            "is_empty": collection.is_empty,
            # Return the number of entities in the collection.
            "num_entities": collection.num_entities,
            # Return the schema.FieldSchema of the primary key field.
            "primary_field": collection.primary_field,
            # Return the list[Partition] object.
            "partitions": collection.partitions,
            # Return the list[Index] object.
            "indexes": collection.indexes,
            # Return the number of vector.
            "vector_count": len(collection.indexes),
            # Return the dimension of vector.
            "vector_dim": collection.schema.fields[-1].params['dim'],
            # Return the expiration time of data in the collection.
            "properties": collection.properties,
        }

    def add(
        self,
        records: List[VectorRecord],
        **kwargs,
    ) -> None:
        r"""Adds a list of vectors to the specified collection.

        Args:
            records (List[VectorRecord]): List of vectors to be added.
            **kwargs (Any): Additional keyword arguments.

        Raises:
            RuntimeError: If there was an error in the addition process.
        """
        op_info = self._client.insert(
            collection_name=self.collection_name,
            data=records,
            **kwargs,
        )
        self._client.flush()
        logger.debug(f"Successfully added vectors in Milvus: {op_info}")

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

        op_info = self._client.delete(collection_name=self.collection_name,
                                      pks=ids, **kwargs)
        logger.debug(f"Successfully deleted vectors in Milvus: {op_info}")

    def status(self) -> VectorDBStatus:
        status = self._get_collection_info(self.collection_name)
        return VectorDBStatus(
            vector_dim=status["vector_dim"],
            vector_count=status["vector_count"],
        )

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
        search_result = self._client.search(
            collection_name=self.collection_name,
            data=query.query_vector,
            limit=query.top_k,
            **kwargs,
        )
        query_results = []
        for point in search_result:
            query_results.append(
                VectorDBQueryResult.construct(  # type: ignore
                    similarity=(1 - point.distance),
                    id=str(point.id),
                ))

        return query_results

    def clear(self) -> None:
        r"""Remove all vectors from the storage."""
        self._delete_collection(self.collection_name)
        self._create_collection(collection_name=self.collection_name)

    @property
    def client(self) -> Any:
        r"""Provides access to the underlying vector database client."""
        return self._client
