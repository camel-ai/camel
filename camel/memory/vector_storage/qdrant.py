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
from dataclasses import asdict, replace
from typing import Any, Dict, List, Optional
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    CollectionStatus,
    Distance,
    PointIdsList,
    PointStruct,
    UpdateStatus,
    VectorParams,
)

from camel.memory.vector_storage.base import BaseVectorStorage, VectorRecord
from camel.typing import VectorDistance


class Qdrant(BaseVectorStorage):
    """
    An implementation of the `BaseVectorStorage` abstract base class tailored
    for Qdrant, a vector search engine.

    This class allows users to interact with Qdrant for operations like
    creating and deleting collections, adding and removing vectors, and
    searching for vectors based on similarity.

    Args:
        path (Optional[str], optional): Local path for the Qdrant database.
            This is used for initializing the client if `url` is not provided.
        url (Optional[str], optional): URL endpoint for a remote Qdrant
            instance. If provided, this takes precedence over the `path`
            parameter.
        api_key (Optional[str], optional): API key for the Qdrant instance, if
            required.
        **kwargs: Additional keyword arguments for QdrantClient.

    Notes:
        - If `url` is provided, it takes priority and the client will attempt
          to connect to the remote Qdrant instance using the URL endpoint.
        - If `url` is not provided and `path` is given, the client will use the
          local path to initialize Qdrant.
        - If neither `url` nor `path` is provided, the client will be
          initialized with an in-memory storage (`":memory:"`).
    """

    def __init__(
        self,
        path: Optional[str] = None,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs,
    ) -> None:
        if url is not None:
            self.client = QdrantClient(url=url, api_key=api_key, **kwargs)
        elif path is not None:
            self.client = QdrantClient(path=path, **kwargs)
        else:
            self.client = QdrantClient(":memory:", **kwargs)

    def create_collection(
        self,
        collection: str,
        size: int,
        distance: VectorDistance = VectorDistance.DOT,
        **kwargs,
    ) -> None:
        """
        See :func:`~camel.memory.vector_storage.base.BaseVectorStorage.\
create_collection`.
        """
        distance_map = {
            VectorDistance.DOT: Distance.DOT,
            VectorDistance.COSINE: Distance.COSINE,
            VectorDistance.EUCLIDEAN: Distance.EUCLID,
        }
        self.client.recreate_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=size,
                                        distance=distance_map[distance]),
            **kwargs,
        )

    def delete_collection(
        self,
        collection: str,
        **kwargs,
    ) -> None:
        """
        See :func:`~camel.memory.vector_storage.base.BaseVectorStorage.\
delete_collection`.
        """
        self.client.delete_collection(collection_name=collection, **kwargs)

    def check_collection(self, collection: str) -> Dict[str, Any]:
        """
        See :func:`~camel.memory.vector_storage.base.BaseVectorStorage.\
check_collection`.

        Raises:
            RuntimeWarning: If the collection's status is not GREEN.
        """
        # TODO: check more information
        collection_info = self.client.get_collection(
            collection_name=collection)
        if collection_info.status != CollectionStatus.GREEN:
            raise RuntimeWarning(f"Qdrant collection \"{collection}\" status: "
                                 f"{collection_info.status}")
        vector_config = collection_info.config.params.vectors
        return {
            "vector_dim":
            vector_config.size
            if isinstance(vector_config, VectorParams) else None,
            "vector_count":
            collection_info.vectors_count,
        }

    def add_vectors(
        self,
        collection: str,
        vectors: List[VectorRecord],
    ) -> List[VectorRecord]:
        """
        See :func:`~camel.memory.vector_storage.base.BaseVectorStorage.\
add_vectors`.

        Raises:
            RuntimeError: If there was an error in the addition process.
        """
        processed_vectors = [replace(v) for v in vectors]
        for v in processed_vectors:
            if v.id is None:
                v.id = str(uuid4())

        qdrant_points = [PointStruct(**asdict(p)) for p in processed_vectors]
        op_info = self.client.upsert(
            collection_name=collection,
            points=qdrant_points,
            wait=True,
        )
        if op_info.status != UpdateStatus.COMPLETED:
            raise RuntimeError(
                "Failed to add vectors in Qdrant, operation info: "
                f"{op_info}")

        return processed_vectors

    def delete_vectors(
        self,
        collection: str,
        vectors: List[VectorRecord],
    ) -> List[VectorRecord]:
        """
        See :func:`~camel.memory.vector_storage.base.BaseVectorStorage.\
delete_vectors`.

        Raises:
            RuntimeError: If there was an error in the deletion process or if a
                provided vector record lacks both an ID and a vector for
                deletion.
        """
        processed_vectors = [replace(v) for v in vectors]
        for v in processed_vectors:
            if v.id is None:
                if v.vector is None:
                    raise RuntimeError("Deleting vector records should "
                                       "contains either id or vector.")
                search_result = self.client.search(
                    collection_name=collection,
                    query_vector=v.vector,
                    with_payload=False,
                    limit=1,
                )
                v.id = search_result[0].id
        delete_points = [v.id for v in processed_vectors if v.id is not None]
        op_info = self.client.delete(
            collection_name=collection,
            points_selector=PointIdsList(points=delete_points),
            wait=True,
        )
        if op_info.status != UpdateStatus.COMPLETED:
            raise RuntimeError(
                "Failed to delete vectors in Qdrant, operation info: "
                f"{op_info}")
        return processed_vectors

    def search(
        self,
        collection: str,
        query_vector: VectorRecord,
        limit: int = 3,
    ) -> List[VectorRecord]:
        """
        See :func:`~camel.memory.vector_storage.base.BaseVectorStorage.\
search`.

        Raises:
            RuntimeError: If the provided search vector is :obj:`None`.
        """
        # TODO: filter
        if query_vector.vector is None:
            raise RuntimeError("Searching vector cannot be None")
        search_result = self.client.search(
            collection_name=collection,
            query_vector=query_vector.vector,
            with_payload=True,
            limit=limit,
        )
        # TODO: including score?
        result_records = []
        for res in search_result:
            result_records.append(
                VectorRecord(
                    id=res.id,
                    payload=res.payload,
                ))

        return result_records
