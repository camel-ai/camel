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


import logging
from typing import Any, Callable, ClassVar, Dict, List

import faiss  # type: ignore[import-untyped]
import numpy as np

from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)

logger = logging.getLogger(__name__)


class FaissStorage(BaseVectorStorage):
    r"""An implementation of the `BaseVectorStorage` for FAISS-based
    similarity search.

    This storage provides efficient similarity search for dense
    vectors using FAISS.

    Args:
        vector_dim (int): The dimension of stored vectors.
        index_type (str, optional): FAISS index type
            (e.g., 'IndexFlatL2', 'IndexFlatIP', 'IVFFlat').
            Defaults to 'IndexFlatL2'.
        use_gpu (bool, optional): Whether to use GPU for faster
            computations. Defaults to `False`
            (throws an exception if `True`). Need to implement this
            in CAMEL later.
        num_threads (int, optional): Number of threads for parallel
            queries. Defaults to `4`.
    """

    SUPPORTED_INDEX_TYPES: ClassVar[
        Dict[str, Callable[[int], faiss.Index]]
    ] = {
        "IndexFlatL2": lambda d: faiss.IndexFlatL2(d),
        "IndexFlatIP": lambda d: faiss.IndexFlatIP(d),
        "IVFFlat": lambda d: faiss.IndexIVFFlat(faiss.IndexFlatL2(d), d, 100),
        "HNSW": lambda d: faiss.IndexHNSWFlat(d, 32),
        "PQ": lambda d: faiss.IndexPQ(d, 8, 8),
    }

    def __init__(
        self,
        vector_dim: int,
        index_type: str = "IndexFlatL2",
        use_gpu: bool = False,
        num_threads: int = 4,
    ) -> None:
        if use_gpu:
            raise ValueError(
                "GPU support is not available for now."
                " Please use FAISS-CPU."
            )

        if index_type not in self.SUPPORTED_INDEX_TYPES:
            raise ValueError(
                f"Unsupported FAISS index type '{index_type}'. "
                f"Supported types: {list(self.SUPPORTED_INDEX_TYPES.keys())}"
            )

        self.vector_dim = vector_dim
        self.index_type = index_type
        self.num_threads = num_threads
        self.index = self._create_index()

        # Store metadata for vectors
        self._id_to_vector: Dict[str, VectorRecord] = {}

        # Set FAISS to use multiple threads
        faiss.omp_set_num_threads(num_threads)

    def _create_index(self) -> faiss.Index:
        r"""Creates a FAISS index based on the specified type."""
        logger.info(f"Creating FAISS index of type '{self.index_type}'")
        return self.SUPPORTED_INDEX_TYPES[self.index_type](self.vector_dim)

    def add(self, records: List[VectorRecord], **kwargs: Any) -> None:
        r"""Adds vectors to the FAISS index."""
        if not records:
            return

        vectors = np.array(
            [record.vector for record in records], dtype=np.float32
        )

        self.index.add(vectors)

        for record in records:
            self._id_to_vector[record.id] = record

        logger.debug(f"Added {len(records)} vectors to FAISS storage.")

    def delete(self, ids: List[str], **kwargs: Any) -> None:
        r"""Deletes vectors from the FAISS index (rebuilds index since
        FAISS lacks deletion).
        """
        if not ids:
            return

        remaining_vectors = [
            record.vector
            for record_id, record in self._id_to_vector.items()
            if record_id not in ids
        ]
        remaining_ids = [
            record_id
            for record_id in self._id_to_vector
            if record_id not in ids
        ]

        # Clear index and re-add remaining vectors
        self.index.reset()
        if remaining_vectors:
            self.index.add(np.array(remaining_vectors, dtype=np.float32))

        # Update metadata storage
        self._id_to_vector = {
            record_id: self._id_to_vector[record_id]
            for record_id in remaining_ids
        }

        logger.debug(f"Deleted {len(ids)} vectors from FAISS storage.")

    def query(
        self, query: VectorDBQuery, **kwargs: Any
    ) -> List[VectorDBQueryResult]:
        r"""Searches for similar vectors in FAISS storage."""
        query_vector = np.array([query.query_vector], dtype=np.float32)

        distances, indices = self.index.search(query_vector, query.top_k)

        results = []
        for i in range(query.top_k):
            index = indices[0][i]
            similarity = distances[0][i]

            if index < 0 or index >= len(self._id_to_vector):
                continue

            record = self._id_to_vector[list(self._id_to_vector.keys())[index]]
            results.append(
                VectorDBQueryResult.create(
                    similarity=similarity,
                    id=record.id,
                    vector=record.vector,
                    payload=record.payload,
                )
            )

        return results

    def status(self) -> VectorDBStatus:
        r"""Returns the status of the FAISS storage."""
        return VectorDBStatus(
            vector_dim=self.vector_dim, vector_count=len(self._id_to_vector)
        )

    def clear(self) -> None:
        r"""Clears the FAISS index."""
        self.index.reset()
        self._id_to_vector.clear()
        logger.debug("Cleared FAISS storage.")

    def load(self) -> None:
        r"""(Optional) Load functionality (not required for in-memory
        FAISS).
        """
        pass  # Can be extended later if we want to load from disk

    @property
    def client(self) -> Any:
        r"""Returns the FAISS index client."""
        return self.index
