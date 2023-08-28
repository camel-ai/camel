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
        self.client.delete_collection(collection_name=collection, **kwargs)

    def check_collection(self, collection: str) -> Dict[str, Any]:
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
