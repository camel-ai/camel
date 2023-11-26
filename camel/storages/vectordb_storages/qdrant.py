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

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    PointIdsList,
    PointStruct,
    UpdateStatus,
    VectorParams,
)

from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDistance,
    VectorRecord,
)


class QdrantStorage(BaseVectorStorage):
    r"""An implementation of the `BaseVectorStorage` for interacting with
    Qdrant, a vector search engine.

    The detailed information about Qdrant is available at https://qdrant.tech/.

    Args:
        vector_dim (int): The dimenstion of storing vectors.
        collection (Optional[str]): Name for the collection in the Qdrant. If
            not provided, a unique identifier is generated.
            (default: :obj:`None`)
        url_and_api_key (Optional[Tuple[str, str]]): Tuple containing the URL
            and API key for connecting to a remote Qdrant instance.
            (default: :obj:`None`)
        path (Optional[str]): Path to a directory for initializing a local
            Qdrant client. (default: :obj:`None`)
        distance (VectorDistance): The distance metric for vector comparison
            (default: :obj:`VectorDistance.Cosine`).
        del_collection (bool): Flag to determine if the collection should be
            deleted upon object destruction (default: :obj:`False`).
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

    def __init__(
        self,
        vector_dim: int,
        collection: Optional[str] = None,
        url_and_api_key: Optional[Tuple[str, str]] = None,
        path: Optional[str] = None,
        distance: VectorDistance = VectorDistance.Cosine,
        del_collection: bool = False,
        **kwargs: Any,
    ) -> None:
        self.vector_dim = vector_dim
        if url_and_api_key is not None:
            self._client = QdrantClient(
                url=url_and_api_key[0],
                api_key=url_and_api_key[1],
                **kwargs,
            )
        elif path is not None:
            self._client = QdrantClient(path=path, **kwargs)
        else:
            self._client = QdrantClient(":memory:", **kwargs)

        if collection is not None:
            try:
                info = self._check_collection(collection)
                if info["vector_dim"] != self.vector_dim:
                    raise RuntimeError(
                        "Vector dimension of the existing collection "
                        f"{collection} ({info['vector_dim']}) "
                        "is different from the embedding dim "
                        f"({self.vector_dim}).")
                return
            except ValueError:
                pass
        self.collection = collection or datetime.now().isoformat()
        self._create_collection(
            collection=self.collection,
            size=self.vector_dim,
            distance=distance,
        )
        self.distance = distance
        self.del_collection = del_collection

    def __del__(self):
        r"""Deletes the collection if :obj:`del_collection` is set to
        :obj:`True`.
        """
        if self.del_collection:
            self._delete_collection(self.collection)

    def _create_collection(
        self,
        collection: str,
        size: int,
        distance: VectorDistance = VectorDistance.Cosine,
        **kwargs: Any,
    ) -> None:
        r"""Creates a new collection in the database.

        Args:
            collection (str): Name of the collection to be created.
            size (int): Dimensionality of vectors to be stored in this
                collection.
            distance (VectorDistance, optional): The distance metric to be used
                for vector similarity. (default: :obj:`VectorDistance.Cosine`)
            **kwargs (Any): Additional keyword arguments.
        """
        distance_map = {
            VectorDistance.DOT: Distance.DOT,
            VectorDistance.COSINE: Distance.COSINE,
            VectorDistance.EUCLIDEAN: Distance.EUCLID,
        }
        self._client.recreate_collection(
            collection_name=collection,
            vectors_config=VectorParams(
                size=size,
                distance=distance_map[distance],
            ),
            **kwargs,
        )

    def _delete_collection(
        self,
        collection: str,
        **kwargs: Any,
    ) -> None:
        r"""Deletes an existing collection from the database.

        Args:
            collection (str): Name of the collection to be deleted.
            **kwargs (Any): Additional keyword arguments.
        """
        self._client.delete_collection(collection_name=collection, **kwargs)

    def _check_collection(self, collection: str) -> Dict[str, Any]:
        r"""Retrieves details of an existing collection.

        Args:
            collection (str): Name of the collection to be checked.

        Returns:
            Dict[str, Any]: A dictionary containing details about the
                collection.
        """
        # TODO: check more information
        collection_info = self._client.get_collection(
            collection_name=collection)
        vector_config = collection_info.config.params.vectors
        return {
            "vector_dim":
            vector_config.size
            if isinstance(vector_config, VectorParams) else None,
            "vector_count":
            collection_info.vectors_count,
            "status":
            collection_info.status,
            "vectors_count":
            collection_info.vectors_count,
            "config":
            collection_info.config,
        }

    def validate_vector_dimensions(self, records: List[VectorRecord]) -> None:
        r"""Validates that all vectors in the given list have the same
        dimensionality as the collection.

        Args:
            records (List[VectorRecord]): A list of vector records to validate.

        Raises:
            ValueError: If any vector has a different dimensionality than
            the collection.
        """
        if not all(
                len(record.vector) == self.vector_dim for record in records):
            raise ValueError(
                "All vectors must have the same dimensionality as defined"
                "in the collection.")

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
        self.validate_vector_dimensions(records)
        qdrant_points = [PointStruct(**asdict(p)) for p in records]
        op_info = self._client.upsert(collection_name=self.collection,
                                      points=qdrant_points, wait=True,
                                      **kwargs)
        if op_info.status != UpdateStatus.COMPLETED:
            raise RuntimeError(
                "Failed to add vectors in Qdrant, operation info: "
                f"{op_info}")

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
        points = cast(List[Union[str, int]], ids)
        op_info = self._client.delete(
            collection_name=self.collection,
            points_selector=PointIdsList(points=points),
            wait=True,
            **kwargs,
        )
        if op_info.status != UpdateStatus.COMPLETED:
            raise RuntimeError(
                "Failed to delete vectors in Qdrant, operation info: "
                f"{op_info}")

    def query(
        self,
        query: VectorDBQuery,
        **kwargs: Any,
    ) -> List[VectorDBQueryResult]:
        r"""Searches for similar vectors in the storage based on the provided query.

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
            collection_name=self.collection,
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
                    vector=point.vector,  # type: ignore
                ))

        return query_results

    def clear(self) -> None:
        r"""Remove all vectors from the storage."""
        if self.del_collection:
            self._delete_collection(self.collection)
        self._create_collection(
            collection=datetime.now().isoformat(),
            size=self.vector_dim,
            distance=self.distance,
        )

    @property
    def client(self) -> QdrantClient:
        return self._client
