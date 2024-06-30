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
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)
from camel.types import VectorDistance
from camel.utils import dependencies_required

_qdrant_local_client_map: Dict[str, Tuple[Any, int]] = {}


class QdrantStorage(BaseVectorStorage):
    r"""An implementation of the `BaseVectorStorage` for interacting with
    Qdrant, a vector search engine.

    The detailed information about Qdrant is available at:
    `Qdrant <https://qdrant.tech/>`_

    Args:
        vector_dim (int): The dimenstion of storing vectors.
        collection_name (Optional[str], optional): Name for the collection in
            the Qdrant. If not provided, set it to the current time with iso
            format. (default: :obj:`None`)
        url_and_api_key (Optional[Tuple[str, str]], optional): Tuple containing
            the URL and API key for connecting to a remote Qdrant instance.
            (default: :obj:`None`)
        path (Optional[str], optional): Path to a directory for initializing a
            local Qdrant client. (default: :obj:`None`)
        distance (VectorDistance, optional): The distance metric for vector
            comparison (default: :obj:`VectorDistance.COSINE`)
        delete_collection_on_del (bool, optional): Flag to determine if the
            collection should be deleted upon object destruction.
            (default: :obj:`False`)
        **kwargs (Any): Additional keyword arguments for initializing
            `QdrantClient`.

    Notes:
        - If `url_and_api_key` is provided, it takes priority and the client
          will attempt to connect to the remote Qdrant instance using the URL
          endpoint.
        - If `url_and_api_key` is not provided and `path` is given, the client
          will use the local path to initialize Qdrant.
        - If neither `url_and_api_key` nor `path` is provided, the client will
          be initialized with an in-memory storage (`":memory:"`).
    """

    @dependencies_required('qdrant_client')
    def __init__(
        self,
        vector_dim: int,
        collection_name: Optional[str] = None,
        url_and_api_key: Optional[Tuple[str, str]] = None,
        path: Optional[str] = None,
        distance: VectorDistance = VectorDistance.COSINE,
        delete_collection_on_del: bool = False,
        **kwargs: Any,
    ) -> None:
        from qdrant_client import QdrantClient

        self._client: QdrantClient
        self._local_path: Optional[str] = None
        self._create_client(url_and_api_key, path, **kwargs)

        self.vector_dim = vector_dim
        self.distance = distance
        self.collection_name = (
            collection_name or self._generate_collection_name()
        )

        self._check_and_create_collection()

        self.delete_collection_on_del = delete_collection_on_del

    def __del__(self):
        r"""Deletes the collection if :obj:`del_collection` is set to
        :obj:`True`.
        """
        # If the client is a local client, decrease count by 1
        if self._local_path is not None:
            # if count decrease to 0, remove it from the map
            _client, _count = _qdrant_local_client_map.pop(self._local_path)
            if _count > 1:
                _qdrant_local_client_map[self._local_path] = (
                    _client,
                    _count - 1,
                )

        if (
            hasattr(self, "delete_collection_on_del")
            and self.delete_collection_on_del
        ):
            self._delete_collection(self.collection_name)

    def _create_client(
        self,
        url_and_api_key: Optional[Tuple[str, str]],
        path: Optional[str],
        **kwargs: Any,
    ) -> None:
        from qdrant_client import QdrantClient

        if url_and_api_key is not None:
            self._client = QdrantClient(
                url=url_and_api_key[0],
                api_key=url_and_api_key[1],
                **kwargs,
            )
        elif path is not None:
            # Avoid creating a local client multiple times,
            # which is prohibited by Qdrant
            self._local_path = path
            if path in _qdrant_local_client_map:
                # Store client instance in the map and maintain counts
                self._client, count = _qdrant_local_client_map[path]
                _qdrant_local_client_map[path] = (self._client, count + 1)
            else:
                self._client = QdrantClient(path=path, **kwargs)
                _qdrant_local_client_map[path] = (self._client, 1)
        else:
            self._client = QdrantClient(":memory:", **kwargs)

    def _check_and_create_collection(self) -> None:
        if self._collection_exists(self.collection_name):
            in_dim = self._get_collection_info(self.collection_name)[
                "vector_dim"
            ]
            if in_dim != self.vector_dim:
                # The name of collection has to be confirmed by the user
                raise ValueError(
                    "Vector dimension of the existing collection "
                    f'"{self.collection_name}" ({in_dim}) is different from '
                    f"the given embedding dim ({self.vector_dim})."
                )
        else:
            self._create_collection(
                collection_name=self.collection_name,
                size=self.vector_dim,
                distance=self.distance,
            )

    def _create_collection(
        self,
        collection_name: str,
        size: int,
        distance: VectorDistance = VectorDistance.COSINE,
        **kwargs: Any,
    ) -> None:
        r"""Creates a new collection in the database.

        Args:
            collection_name (str): Name of the collection to be created.
            size (int): Dimensionality of vectors to be stored in this
                collection.
            distance (VectorDistance, optional): The distance metric to be used
                for vector similarity. (default: :obj:`VectorDistance.COSINE`)
            **kwargs (Any): Additional keyword arguments.
        """
        from qdrant_client.http.models import Distance, VectorParams

        distance_map = {
            VectorDistance.DOT: Distance.DOT,
            VectorDistance.COSINE: Distance.COSINE,
            VectorDistance.EUCLIDEAN: Distance.EUCLID,
        }
        # Since `recreate_collection` method will be removed in the future
        # by Qdrant, `create_collection` is recommended instead.
        self._client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=size,
                distance=distance_map[distance],
            ),
            **kwargs,
        )

    def _delete_collection(
        self,
        collection_name: str,
        **kwargs: Any,
    ) -> None:
        r"""Deletes an existing collection from the database.

        Args:
            collection (str): Name of the collection to be deleted.
            **kwargs (Any): Additional keyword arguments.
        """
        self._client.delete_collection(
            collection_name=collection_name, **kwargs
        )

    def _collection_exists(self, collection_name: str) -> bool:
        r"""Returns wether the collection exists in the database"""
        for c in self._client.get_collections().collections:
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
        from qdrant_client.http.models import VectorParams

        # TODO: check more information
        collection_info = self._client.get_collection(
            collection_name=collection_name
        )
        vector_config = collection_info.config.params.vectors
        return {
            "vector_dim": vector_config.size
            if isinstance(vector_config, VectorParams)
            else None,
            "vector_count": collection_info.points_count,
            "status": collection_info.status,
            "vectors_count": collection_info.vectors_count,
            "config": collection_info.config,
        }

    def add(
        self,
        records: List[VectorRecord],
        **kwargs,
    ) -> None:
        r"""Adds a list of vectors to the specified collection.

        Args:
            vectors (List[VectorRecord]): List of vectors to be added.
            **kwargs (Any): Additional keyword arguments.

        Raises:
            RuntimeError: If there was an error in the addition process.
        """
        from qdrant_client.http.models import PointStruct, UpdateStatus

        qdrant_points = [PointStruct(**asdict(p)) for p in records]
        op_info = self._client.upsert(
            collection_name=self.collection_name,
            points=qdrant_points,
            wait=True,
            **kwargs,
        )
        if op_info.status != UpdateStatus.COMPLETED:
            raise RuntimeError(
                "Failed to add vectors in Qdrant, operation info: "
                f"{op_info}."
            )

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
        from qdrant_client.http.models import PointIdsList, UpdateStatus

        points = cast(List[Union[str, int]], ids)
        op_info = self._client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(points=points),
            wait=True,
            **kwargs,
        )
        if op_info.status != UpdateStatus.COMPLETED:
            raise RuntimeError(
                "Failed to delete vectors in Qdrant, operation info: "
                f"{op_info}"
            )

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
        # TODO: filter
        search_result = self._client.search(
            collection_name=self.collection_name,
            query_vector=query.query_vector,
            with_payload=True,
            with_vectors=True,
            limit=query.top_k,
            **kwargs,
        )
        query_results = []
        for point in search_result:
            query_results.append(
                VectorDBQueryResult.construct(
                    similarity=point.score,
                    id=str(point.id),
                    payload=point.payload,
                    vector=point.vector,  # type: ignore[arg-type]
                )
            )

        return query_results

    def clear(self) -> None:
        r"""Remove all vectors from the storage."""
        self._delete_collection(self.collection_name)
        self._create_collection(
            collection_name=self.collection_name,
            size=self.vector_dim,
            distance=self.distance,
        )

    def load(self) -> None:
        r"""Load the collection hosted on cloud service."""
        pass

    @property
    def client(self) -> Any:
        r"""Provides access to the underlying vector database client."""
        return self._client
