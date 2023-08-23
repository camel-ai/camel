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
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    CollectionStatus,
    Distance,
    PointStruct,
    UpdateStatus,
    VectorParams,
)

import camel.memory.vector_storage.base as base


class Qdrant():

    def __init__(
        self,
        path: Optional[str] = None,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs,
    ) -> None:
        if url is not None:
            self.client = QdrantClient(url=url, api_key=api_key)
        elif path is not None:
            self.client = QdrantClient(path=path)
        else:
            self.client = QdrantClient(":memory:")

    def create_collection(
        self,
        collection: str,
        size: int,
        distance: base.Distance.DOT,
        **kwargs,
    ):
        distance_map = {
            base.Distance.DOT: Distance.DOT,
            base.Distance.COSINE: Distance.COSINE,
            base.Distance.EUCLID: Distance.EUCLID,
        }

        self.client.recreate_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=size,
                                        distance=distance_map[distance]),
            **kwargs)

    def check_collection(self, collection: str) -> None:
        collection_info = self.client.get_collection(
            collection_name=collection)
        if collection_info.status != CollectionStatus.GREEN:
            raise RuntimeError(
                f"Connect to Qdrant collection \"{collection}\" failed.")

    def add_points(
        self,
        collection: str,
        points: List[base.VectorRecord],
    ) -> None:
        points = [PointStruct(**asdict(p)) for p in points]
        operation_info = self.client.upsert(
            collection_name=collection,
            points=points,
            wait=True,
        )
        if operation_info.status != UpdateStatus.COMPLETED:
            raise RuntimeError(
                "Failed to add points in Qdrant, operation_info: "
                f"{operation_info}")

    def search(
        self,
        query_point: base.VectorRecord,
        limit: int = 3,
    ) -> List[base.VectorRecord]:
        # TODO: filter
        search_result = self.client.search(
            collection_name="test_collection",
            query_vector=query_point.vector,
            with_payload=True,
            with_vectors=True,  # not necessary?
            limit=limit,
        )
        # TODO: including score?
        result_records = [
            base.VectorRecord(
                id=res.id,
                vector=res.vector,
                payload=res.payload,
            ) for res in search_result
        ]
        return result_records
