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

import os
import pickle
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from camel.logger import get_logger
from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorDBQueryResult,
    VectorDBStatus,
    VectorRecord,
)
from camel.types import VectorDistance
from camel.utils import dependencies_required

if TYPE_CHECKING:
    from numpy import ndarray

logger = get_logger(__name__)


class FaissStorage(BaseVectorStorage):
    r"""An implementation of the `BaseVectorStorage` using FAISS,
    Facebook AI's Similarity Search library for efficient vector search.

    The detailed information about FAISS is available at:
    `FAISS <https://github.com/facebookresearch/faiss>`_

    Args:
        vector_dim (int): The dimension of storing vectors.
        index_type (str, optional): Type of FAISS index to create.
            Options include 'Flat', 'IVF', 'HNSW', etc. (default:
            :obj:`'Flat'`)
        collection_name (Optional[str], optional): Name for the collection.
            If not provided, set it to the current time with iso format.
            (default: :obj:`None`)
        storage_path (Optional[str], optional): Path to directory where
            the index will be stored. If None, index will only exist in memory.
            (default: :obj:`None`)
        distance (VectorDistance, optional): The distance metric for vector
            comparison (default: :obj:`VectorDistance.COSINE`)
        nlist (int, optional): Number of cluster centroids for IVF indexes.
            Only used if index_type includes 'IVF'. (default: :obj:`100`)
        m (int, optional): HNSW parameter. Number of connections per node.
            Only used if index_type includes 'HNSW'. (default: :obj:`16`)
        **kwargs (Any): Additional keyword arguments.

    Notes:
        - FAISS offers various index types optimized for different use cases:
          - 'Flat': Exact search, but slowest for large datasets
          - 'IVF': Inverted file index, good balance of speed and recall
          - 'HNSW': Hierarchical Navigable Small World, fast with high recall
          - 'PQ': Product Quantization for memory-efficient storage
        - The choice of index should be based on your specific requirements
          for search speed, memory usage, and accuracy.
    """

    @dependencies_required('faiss')
    def __init__(
        self,
        vector_dim: int,
        index_type: str = 'Flat',
        collection_name: Optional[str] = None,
        storage_path: Optional[str] = None,
        distance: VectorDistance = VectorDistance.COSINE,
        nlist: int = 100,
        m: int = 16,
        **kwargs: Any,
    ) -> None:
        r"""Initialize the FAISS vector storage.

        Args:
            vector_dim: Dimension of vectors to be stored
            index_type: FAISS index type ('Flat', 'IVF', 'HNSW', etc.)
            collection_name: Name of the collection (defaults to timestamp)
            storage_path: Directory to save the index (None for in-memory only)
            distance: Vector distance metric
            nlist: Number of clusters for IVF indexes
            m: HNSW parameter for connections per node
            **kwargs: Additional parameters
        """
        import faiss
        import numpy as np

        self.vector_dim = vector_dim
        self.index_type = index_type
        self.collection_name = (
            collection_name or self._generate_collection_name()
        )
        self.storage_path = storage_path
        self.distance = distance
        self.nlist = nlist
        self.m = m
        self._faiss_client = faiss  # Store the faiss module as the client

        # Create directory for storage if it doesn't exist
        if self.storage_path is not None:
            os.makedirs(self.storage_path, exist_ok=True)

        # Initialize the FAISS index
        self._index = self._create_index()

        # Storage for IDs and payloads (FAISS only stores vectors)
        self._id_to_index: Dict[str, int] = {}
        self._index_to_id: Dict[int, str] = {}
        self._payloads: Dict[str, Dict[str, Any]] = {}
        self._vectors: Dict[str, np.ndarray] = {}

        # Load existing index if it exists
        if self.storage_path:
            self._load_from_disk()

    def _generate_collection_name(self) -> str:
        r"""Generates a collection name if user doesn't provide"""
        return f"faiss_index_{datetime.now().isoformat()}"

    def _get_index_path(self) -> str:
        r"""Returns the path to the index file"""
        if self.storage_path is None:
            raise ValueError("Storage path is not set.")
        return os.path.join(self.storage_path, f"{self.collection_name}.index")

    def _get_metadata_path(self) -> str:
        r"""Returns the path to the metadata file"""
        if self.storage_path is None:
            raise ValueError("Storage path is not set.")
        return os.path.join(
            self.storage_path, f"{self.collection_name}.metadata"
        )

    def _create_index(self):
        r"""Creates a new FAISS index based on specified parameters.

        Returns:
            A FAISS index object configured according to the parameters.
        """
        import faiss

        # Determine the metric to use based on distance type
        if self.distance == VectorDistance.COSINE:
            # For cosine similarity, we need to normalize vectors
            metric = faiss.METRIC_INNER_PRODUCT
        elif self.distance == VectorDistance.EUCLIDEAN:
            metric = faiss.METRIC_L2
        elif self.distance == VectorDistance.DOT:
            metric = faiss.METRIC_INNER_PRODUCT
        else:
            raise ValueError(f"Unsupported distance metric: {self.distance}")

        # Create the appropriate index based on index_type
        if self.index_type == 'Flat':
            if metric == faiss.METRIC_INNER_PRODUCT:
                index = faiss.IndexFlatIP(self.vector_dim)
            else:
                index = faiss.IndexFlatL2(self.vector_dim)
        elif self.index_type.startswith('IVF'):
            # IVF requires a quantizer (often a flat index)
            quantizer = faiss.IndexFlatL2(self.vector_dim)
            if 'Flat' in self.index_type:
                index = faiss.IndexIVFFlat(
                    quantizer, self.vector_dim, self.nlist, metric
                )
            elif 'PQ' in self.index_type:
                # M value for PQ, typically a divisor of vector_dim
                m = self.vector_dim // 4  # default setting
                nbits = 8  # typically 8 bits per sub-vector
                index = faiss.IndexIVFPQ(
                    quantizer, self.vector_dim, self.nlist, m, nbits
                )
            else:
                raise ValueError(
                    f"Unsupported IVF index type: {self.index_type}"
                )

            # IVF indexes need to be trained before use
            # This is a placeholder since actual training requires data
            # Number of clusters to search (trade-off between speed and
            # accuracy)
            index.nprobe = 10
        elif self.index_type == 'HNSW':
            index = faiss.IndexHNSWFlat(self.vector_dim, self.m, metric)
        else:
            raise ValueError(f"Unsupported index type: {self.index_type}")

        return index

    def _save_to_disk(self) -> None:
        r"""Save the index and metadata to disk if storage_path is provided."""
        if self.storage_path is None:
            return

        import faiss

        # Save the FAISS index
        faiss.write_index(self._index, self._get_index_path())

        # Save the metadata (IDs, payloads, vectors)
        metadata = {
            "id_to_index": self._id_to_index,
            "index_to_id": self._index_to_id,
            "payloads": self._payloads,
            "vectors": self._vectors,
            "vector_dim": self.vector_dim,
            "distance": self.distance,
        }

        with open(self._get_metadata_path(), 'wb') as f:
            pickle.dump(metadata, f)

        logger.info(f"Saved FAISS index and metadata to {self.storage_path}")

    def _load_from_disk(self) -> None:
        r"""Loads the index and metadata from disk if they exist."""
        if self.storage_path is None:
            return

        import faiss

        index_path = self._get_index_path()
        metadata_path = self._get_metadata_path()

        if os.path.exists(index_path) and os.path.exists(metadata_path):
            try:
                # Load the FAISS index
                self._index = faiss.read_index(index_path)

                # Load the metadata
                with open(metadata_path, 'rb') as f:
                    metadata = pickle.load(f)

                # Verify metadata structure before assigning
                required_keys = [
                    "id_to_index",
                    "index_to_id",
                    "payloads",
                    "vectors",
                    "vector_dim",
                ]
                if not all(key in metadata for key in required_keys):
                    missing_keys = [
                        key for key in required_keys if key not in metadata
                    ]
                    raise ValueError(
                        f"Metadata is missing required keys: {missing_keys}"
                    )

                self._id_to_index = metadata["id_to_index"]
                self._index_to_id = metadata["index_to_id"]
                self._payloads = metadata["payloads"]
                self._vectors = metadata["vectors"]

                # Check that the loaded index is compatible
                if metadata["vector_dim"] != self.vector_dim:
                    logger.warning(
                        f"Loaded index has different vector dimension "
                        f"({metadata['vector_dim']}) than specified "
                        f"({self.vector_dim})."
                    )

                logger.info(
                    f"Loaded FAISS index and metadata from {self.storage_path}"
                )
            except Exception as e:
                logger.error(f"Failed to load index from disk: {e}")
                # Initialize a new index
                self._index = self._create_index()
        else:
            logger.info("No existing index found. Creating new one.")

    def add(
        self,
        records: List[VectorRecord],
        **kwargs,
    ) -> None:
        r"""Adds a list of vectors to the index.

        Args:
            records (List[VectorRecord]): List of vector records to be added.
            **kwargs (Any): Additional keyword arguments.

        Raises:
            RuntimeError: If there was an error in the addition process.
        """
        import numpy as np

        if not records:
            return

        # Check if the index needs training (for IVF indexes)
        if self.index_type.startswith('IVF') and not self._index.is_trained:
            # For IVF indexes, we need to train with vectors before adding
            vectors = np.array(
                [record.vector for record in records], dtype=np.float32
            )
            try:
                self._index.train(vectors)
            except Exception as e:
                raise RuntimeError(f"Failed to train FAISS index: {e}")

        # Add each record to the index
        for record in records:
            # Normalize vector if using cosine similarity
            vector = np.array(record.vector, dtype=np.float32).reshape(1, -1)
            if self.distance == VectorDistance.COSINE:
                vector = self._normalize_vector(vector)

            # Get the next index
            idx = len(self._id_to_index)

            # Add to FAISS index and update mappings atomically
            try:
                self._index.add(vector)
                # Store mapping from ID to index
                self._id_to_index[record.id] = idx
                self._index_to_id[idx] = record.id
                # Store payload
                if record.payload is not None:
                    self._payloads[record.id] = record.payload.copy()
                else:
                    self._payloads[record.id] = {}
                # Store the original vector for later retrieval
                self._vectors[record.id] = vector.flatten().copy()
            except Exception as e:
                # If adding to the index fails, roll back any partial changes
                if record.id in self._id_to_index:
                    del self._id_to_index[record.id]
                if idx in self._index_to_id:
                    del self._index_to_id[idx]
                if record.id in self._payloads:
                    del self._payloads[record.id]
                if record.id in self._vectors:
                    del self._vectors[record.id]
                raise RuntimeError(f"Failed to add vector to FAISS index: {e}")

        # Save to disk if storage path is provided
        self._save_to_disk()

    def update_payload(
        self, ids: List[str], payload: Dict[str, Any], **kwargs: Any
    ) -> None:
        r"""Updates the payload of the vectors identified by their IDs.

        Args:
            ids (List[str]): List of unique identifiers for the vectors to be
                updated.
            payload (Dict[str, Any]): Payload to be updated for all specified
                IDs.
            **kwargs (Any): Additional keyword arguments.

        Raises:
            KeyError: If any of the provided IDs does not exist in the index.
        """
        for id in ids:
            if id not in self._payloads:
                raise KeyError(f"Vector with ID {id} not found in the index.")

            # Update payload (merge with existing payload)
            if id in self._payloads:
                self._payloads[id].update(payload)
            else:
                self._payloads[id] = payload.copy()

        # Save to disk if storage path is provided
        self._save_to_disk()

    def delete_collection(self) -> None:
        r"""Deletes the entire collection (index and metadata)."""
        # Reset the index
        self._index = self._create_index()

        # Clear metadata
        self._id_to_index = {}
        self._index_to_id = {}
        self._payloads = {}
        self._vectors = {}

        # Remove files from disk if storage path is provided
        if self.storage_path:
            index_path = self._get_index_path()
            metadata_path = self._get_metadata_path()

            if os.path.exists(index_path):
                os.remove(index_path)

            if os.path.exists(metadata_path):
                os.remove(metadata_path)

            logger.info(
                f"Deleted FAISS index and metadata from {self.storage_path}"
            )

    def delete(
        self,
        ids: Optional[List[str]] = None,
        payload_filter: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        r"""Deletes vectors from the index based on either IDs or payload
        filters.

        Args:
            ids (Optional[List[str]], optional): List of unique identifiers
                for the vectors to be deleted.
            payload_filter (Optional[Dict[str, Any]], optional): A filter for
                the payload to delete points matching specific conditions.
            **kwargs (Any): Additional keyword arguments.

        Raises:
            ValueError: If neither `ids` nor `payload_filter` is provided.
            RuntimeError: If the FAISS index does not support removal.

        Notes:
            - FAISS does not support efficient single vector removal for most
              index types. This implementation recreates the index without the
              deleted vectors, which can be inefficient for large datasets.
            - If both `ids` and `payload_filter` are provided, both filters
              will be applied (vectors matching either will be deleted).
        """
        import faiss
        import numpy as np

        if not ids and not payload_filter:
            raise ValueError(
                "You must provide either `ids` or `payload_filter` to delete "
                "vectors."
            )

        # Get IDs to delete from payload filter
        if payload_filter:
            filtered_ids = [
                id
                for id, payload in self._payloads.items()
                if all(
                    payload.get(key) == value
                    for key, value in payload_filter.items()
                )
            ]
        else:
            filtered_ids = []

        # Combine with explicit IDs
        ids_to_delete = set(ids or []) | set(filtered_ids)
        if not ids_to_delete:
            return

        # Check if the index supports removal
        if hasattr(self._index, 'remove_ids'):
            # Convert IDs to indices
            indices_to_remove = np.array(
                [
                    self._id_to_index[id]
                    for id in ids_to_delete
                    if id in self._id_to_index
                ],
                dtype=np.int64,
            )

            if len(indices_to_remove) > 0:
                # Create a selector where 1 means "remove"
                selector = np.zeros(self._index.ntotal, dtype=bool)
                selector[indices_to_remove] = True

                try:
                    # Remove from FAISS index
                    id_selector = faiss.IDSelectorArray(
                        len(indices_to_remove), indices_to_remove
                    )
                    self._index.remove_ids(id_selector)

                    # Update mappings and storage
                    for id in ids_to_delete:
                        if id in self._id_to_index:
                            idx = self._id_to_index[id]
                            del self._index_to_id[idx]
                            del self._id_to_index[id]
                            if id in self._payloads:
                                del self._payloads[id]
                            if id in self._vectors:
                                del self._vectors[id]

                    # Save to disk if storage path is provided
                    self._save_to_disk()
                except Exception as e:
                    raise RuntimeError(
                        f"Failed to remove vectors from FAISS index: {e}"
                    )
        else:
            # Index doesn't support removal, need to rebuild
            logger.warning(
                "This FAISS index type doesn't support direct removal. "
                "Rebuilding entire index (may be slow for large datasets)."
            )

            # Get all vectors and IDs that should be kept
            keep_ids = [
                id
                for id in self._id_to_index.keys()
                if id not in ids_to_delete
            ]

            # Create a new index
            new_index = self._create_index()

            # If it's an IVF index and there are vectors to train on, train it
            if self.index_type.startswith('IVF') and keep_ids:
                train_vectors = np.vstack(
                    [self._vectors[id].reshape(1, -1) for id in keep_ids]
                )
                new_index.train(train_vectors)

            # Add the vectors to keep to the new index
            new_id_to_index = {}
            new_index_to_id = {}

            for new_idx, id in enumerate(keep_ids):
                vector = self._vectors[id].reshape(1, -1)
                new_index.add(vector)
                new_id_to_index[id] = new_idx
                new_index_to_id[new_idx] = id

            # Replace the old index and mappings
            self._index = new_index
            self._id_to_index = new_id_to_index
            self._index_to_id = new_index_to_id

            # Remove deleted IDs from payloads and vectors
            for id in ids_to_delete:
                if id in self._payloads:
                    del self._payloads[id]
                if id in self._vectors:
                    del self._vectors[id]

            # Save to disk if storage path is provided
            self._save_to_disk()

    def status(self) -> VectorDBStatus:
        r"""Returns the status of the vector database.

        Returns:
            VectorDBStatus: Current status of the vector database.
        """
        return VectorDBStatus(
            vector_dim=self.vector_dim,
            vector_count=self._index.ntotal,
        )

    def query(
        self,
        query: VectorDBQuery,
        filter_conditions: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[VectorDBQueryResult]:
        r"""Searches for similar vectors in the storage based on the provided
        query.

        Args:
            query (VectorDBQuery): The query object containing the search
                vector and the number of top similar vectors to retrieve.
            filter_conditions (Optional[Dict[str, Any]], optional): A
                dictionary specifying conditions to filter the query results.
            **kwargs (Any): Additional keyword arguments.

        Returns:
            List[VectorDBQueryResult]: A list of query results ordered by
                similarity.
        """
        import numpy as np

        if self._index.ntotal == 0:
            return []

        # Prepare the query vector
        query_vector = np.array(query.query_vector, dtype=np.float32)
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        # Normalize if using cosine similarity
        if self.distance == VectorDistance.COSINE:
            query_vector = self._normalize_vector(query_vector)

        # For IVF indexes, set the number of clusters to probe (higher = more
        # accurate but slower)
        if hasattr(self._index, 'nprobe'):
            nprobe = kwargs.get('nprobe', 10)  # Default to 10
            self._index.nprobe = nprobe

        # Determine how many results to fetch initially when using filters
        k = query.top_k
        if filter_conditions:
            # Fetch more results if filtering is applied to ensure we have
            # enough after filtering
            # This is a simple heuristic - multiply by 2 or by a user-provided
            # factor
            fetch_factor = kwargs.get('fetch_factor', 2)
            fetch_k = min(int(k * fetch_factor), self._index.ntotal)
        else:
            fetch_k = min(k, self._index.ntotal)

        # Perform the search
        distances, indices = self._index.search(query_vector, fetch_k)

        # Convert results to VectorDBQueryResult objects
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue

            vector_id = self._index_to_id.get(idx)
            if not vector_id:
                continue

            # If there are filter conditions, check if this result passes
            if filter_conditions and not self._matches_filter(
                vector_id, filter_conditions
            ):
                continue

            # Adjust similarity score based on distance metric
            if self.distance == VectorDistance.EUCLIDEAN:
                # For Euclidean distance, smaller is better, so we invert
                similarity = 1.0 / (1.0 + distances[0][i])
            else:
                # For inner product/cosine, higher is better
                similarity = float(distances[0][i])

            vector = self._vectors.get(vector_id)
            if vector is not None:
                vector = vector.tolist()
            else:
                vector = []  # type: ignore[assignment]

            results.append(
                VectorDBQueryResult.create(
                    similarity=similarity,
                    id=vector_id,
                    payload=self._payloads.get(vector_id, {}),
                    vector=cast(List[float], vector),
                )
            )

            # Stop once we have enough results
            if len(results) >= k:
                break

        return results

    def clear(self) -> None:
        r"""Remove all vectors from the storage."""
        self.delete_collection()

    def load(self) -> None:
        r"""Load the index from disk if storage_path is provided."""
        if self.storage_path:
            self._load_from_disk()
        else:
            logger.warning("No storage path provided. Cannot load index.")

    @property
    def client(self) -> Any:
        r"""Provides access to the underlying FAISS client."""
        return self._faiss_client

    def _matches_filter(
        self, vector_id: str, filter_conditions: Dict[str, Any]
    ) -> bool:
        r"""Checks if a vector's payload matches the filter conditions.

        Args:
            vector_id (str): ID of the vector to check.
            filter_conditions (Dict[str, Any]): Conditions to match against.

        Returns:
            bool: True if the payload matches all conditions, False otherwise.
        """
        payload = self._payloads.get(vector_id, {})
        for key, value in filter_conditions.items():
            if key not in payload or payload[key] != value:
                return False
        return True

    def _normalize_vector(self, vector: "ndarray") -> "ndarray":
        r"""Normalizes a vector to unit length for cosine similarity.

        Args:
            vector (ndarray): Vector to normalize, either 1D or 2D array.

        Returns:
            ndarray: Normalized vector with the same shape as input.
        """
        import numpy as np

        if vector.ndim == 1:
            vector = vector.reshape(1, -1)
        norm = np.linalg.norm(vector, axis=1, keepdims=True)
        # Avoid division by zero
        norm = np.maximum(norm, 1e-10)
        return vector / norm
