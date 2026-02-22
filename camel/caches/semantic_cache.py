# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

import json
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4

from camel.caches.base import BaseCache, CacheRecord
from camel.embeddings.base import BaseEmbedding
from camel.logger import get_logger
from camel.storages.vectordb_storages import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorRecord,
)

logger = get_logger(__name__)


class SemanticCache(BaseCache):
    r"""A semantic cache implementation that uses vector similarity to find
    cached responses for semantically similar queries.

    This cache generates embeddings for queries and stores them in a vector
    database. When looking up a query, it finds the most similar cached query
    using vector similarity search and returns the corresponding response if
    the similarity exceeds the threshold.

    Args:
        embedding_model (BaseEmbedding): The embedding model to use for
            generating query embeddings.
        vector_storage (BaseVectorStorage): The vector storage backend for
            storing and searching query embeddings.
        similarity_threshold (float): The minimum similarity score (0.0-1.0)
            required for a cache hit. Higher values require closer matches.
            (default: :obj:`0.85`)
        cache_enabled (bool): Whether the cache is enabled.
            (default: :obj:`True`)

    """

    # Payload keys for storing cache data
    _QUERY_KEY = "query"
    _RESPONSE_KEY = "response"
    _CREATED_AT_KEY = "created_at"
    _METADATA_KEY = "metadata"

    def __init__(
        self,
        embedding_model: BaseEmbedding,
        vector_storage: BaseVectorStorage,
        similarity_threshold: float = 0.85,
        cache_enabled: bool = True,
    ) -> None:
        r"""Initialize the semantic cache.

        Args:
            embedding_model (BaseEmbedding): The embedding model for queries.
            vector_storage (BaseVectorStorage): The vector storage backend.
            similarity_threshold (float): Minimum similarity for cache hit.
            cache_enabled (bool): Whether the cache is enabled initially.
        """
        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError(
                f"similarity_threshold must be between 0.0 and 1.0, "
                f"got {similarity_threshold}"
            )

        self._embedding_model = embedding_model
        self._vector_storage = vector_storage
        self._similarity_threshold = similarity_threshold
        self._cache_enabled = cache_enabled
        self._cache_hits = 0
        self._cache_misses = 0
        self._stats_lock = Lock()

        logger.info(
            f"SemanticCache initialized with threshold={similarity_threshold}"
        )

    @property
    def similarity_threshold(self) -> float:
        r"""Returns the similarity threshold for cache hits.

        Returns:
            float: The similarity threshold (0.0-1.0).
        """
        return self._similarity_threshold

    @similarity_threshold.setter
    def similarity_threshold(self, value: float) -> None:
        r"""Set the similarity threshold for cache hits.

        Args:
            value (float): The new threshold value (0.0-1.0).

        Raises:
            ValueError: If value is not between 0.0 and 1.0.
        """
        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"similarity_threshold must be between 0.0 and 1.0, "
                f"got {value}"
            )
        self._similarity_threshold = value

    @property
    def enabled(self) -> bool:
        r"""Returns whether the cache is enabled.

        Returns:
            bool: True if cache is enabled.
        """
        return self._cache_enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        r"""Enable or disable the cache.

        Args:
            value (bool): True to enable, False to disable.
        """
        self._cache_enabled = value

    @property
    def size(self) -> int:
        r"""Returns the number of entries in the cache.

        Returns:
            int: The number of cached entries.
        """
        return self._vector_storage.status().vector_count

    @property
    def hit_rate(self) -> float:
        r"""Returns the cache hit rate.

        Returns:
            float: Cache hit rate (0.0-1.0), or 0.0 if no lookups yet.
        """
        with self._stats_lock:
            total = self._cache_hits + self._cache_misses
            if total == 0:
                return 0.0
            return self._cache_hits / total

    @property
    def stats(self) -> Dict[str, Any]:
        r"""Returns cache statistics.

        Returns:
            Dict[str, Any]: Dictionary containing cache statistics including
                hits, misses, hit rate, and size.
        """
        with self._stats_lock:
            return {
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_rate": (
                    self._cache_hits / (self._cache_hits + self._cache_misses)
                    if (self._cache_hits + self._cache_misses) > 0
                    else 0.0
                ),
                "size": self.size,
                "enabled": self.enabled,
                "similarity_threshold": self._similarity_threshold,
            }

    def _query_similar(self, query: str, top_k: int = 1) -> Optional[List]:
        r"""Internal helper to query vector storage for similar entries.

        This consolidates the common logic of embedding generation and
        vector storage querying used by get, get_with_score, and find_similar.

        Args:
            query (str): The query to search for.
            top_k (int): Number of results to return. (default: :obj:`1`)

        Returns:
            Optional[List]: List of query results from vector storage,
                or None if query fails or is empty.
        """
        if not query or not query.strip():
            return None

        # Generate embedding for the query
        try:
            query_embedding = self._embedding_model.embed(query)
        except Exception as e:
            logger.warning(f"Failed to generate embedding for query: {e}")
            return None

        # Search for similar queries
        try:
            results = self._vector_storage.query(
                VectorDBQuery(query_vector=query_embedding, top_k=top_k)
            )
            return results if results else None
        except Exception as e:
            logger.warning(f"Failed to query vector storage: {e}")
            return None

    def _result_to_cache_record(self, result) -> CacheRecord:
        r"""Convert a vector storage result to a CacheRecord.

        Args:
            result: A query result from vector storage.

        Returns:
            CacheRecord: The converted cache record.
        """
        payload = result.record.payload or {}
        # Deserialize metadata from JSON string (stored as JSON for
        # compatibility with storage backends that don't support nested dicts)
        metadata_raw = payload.get(self._METADATA_KEY, "{}")
        if isinstance(metadata_raw, str):
            try:
                metadata = json.loads(metadata_raw)
            except json.JSONDecodeError:
                metadata = {}
        else:
            metadata = metadata_raw if isinstance(metadata_raw, dict) else {}
        return CacheRecord(
            query=payload.get(self._QUERY_KEY, ""),
            response=payload.get(self._RESPONSE_KEY, ""),
            query_id=result.record.id,
            created_at=datetime.fromisoformat(
                payload.get(self._CREATED_AT_KEY, datetime.now().isoformat())
            ),
            metadata=metadata,
        )

    def _normalize_similarity(self, score: float) -> float:
        r"""Normalize similarity score to 0.0-1.0 range.

        Different vector storage backends may return similarity scores in
        different ranges. This method ensures consistent behavior by clamping
        scores to the expected 0.0-1.0 range.

        Args:
            score (float): Raw similarity score from storage backend.

        Returns:
            float: Normalized similarity score between 0.0 and 1.0.
        """
        return max(0.0, min(1.0, score))

    def get(self, query: str) -> Optional[str]:
        r"""Retrieve a cached response for a semantically similar query.

        Generates an embedding for the query and searches the vector storage
        for similar cached queries. Returns the cached response if a match
        is found with similarity >= threshold.

        Args:
            query (str): The query to look up in the cache.

        Returns:
            Optional[str]: The cached response if a similar query is found
                with sufficient similarity, None otherwise.
        """
        if not self._cache_enabled:
            return None

        results = self._query_similar(query, top_k=1)
        if not results:
            with self._stats_lock:
                self._cache_misses += 1
            logger.debug("Cache miss: no results found for query")
            return None

        # Check if the best match exceeds the threshold
        best_match = results[0]
        similarity = self._normalize_similarity(best_match.similarity)
        if similarity >= self._similarity_threshold:
            with self._stats_lock:
                self._cache_hits += 1
            payload = best_match.record.payload or {}
            response = payload.get(self._RESPONSE_KEY)
            logger.debug(
                f"Cache hit: similarity={similarity:.4f}, "
                f"threshold={self._similarity_threshold}"
            )
            return response

        with self._stats_lock:
            self._cache_misses += 1
        logger.debug(
            f"Cache miss: similarity={similarity:.4f} < "
            f"threshold={self._similarity_threshold}"
        )
        return None

    def get_with_score(
        self, query: str
    ) -> Optional[tuple[str, float, CacheRecord]]:
        r"""Retrieve cached response with similarity score and full record.

        Similar to get(), but returns additional information about the match.

        Args:
            query (str): The query to look up in the cache.

        Returns:
            Optional[tuple[str, float, CacheRecord]]: A tuple of
                (response, similarity_score, cache_record) if found,
                None otherwise.
        """
        if not self._cache_enabled:
            return None

        results = self._query_similar(query, top_k=1)
        if not results:
            with self._stats_lock:
                self._cache_misses += 1
            return None

        # Check if the best match exceeds the threshold
        best_match = results[0]
        similarity = self._normalize_similarity(best_match.similarity)
        if similarity >= self._similarity_threshold:
            with self._stats_lock:
                self._cache_hits += 1
            record = self._result_to_cache_record(best_match)
            return (record.response, similarity, record)

        with self._stats_lock:
            self._cache_misses += 1
        return None

    def set(
        self,
        query: str,
        response: str,
        **kwargs: Any,
    ) -> Optional[str]:
        r"""Store a query-response pair in the cache.

        Generates an embedding for the query and stores it along with the
        response in the vector storage.

        Args:
            query (str): The query text.
            response (str): The response to cache.
            **kwargs (Any): Additional arguments. Supports:
                - metadata (Dict[str, Any]): Additional metadata to store.

        Returns:
            Optional[str]: The unique ID assigned to this cache entry,
                or None if cache is disabled.

        Raises:
            ValueError: If query or response is empty.
        """
        if not self._cache_enabled:
            return None

        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        if not response:
            raise ValueError("Response cannot be empty")

        # Extract metadata from kwargs
        metadata: Optional[Dict[str, Any]] = kwargs.get("metadata")

        # Generate embedding for the query
        query_embedding = self._embedding_model.embed(query)

        # Create unique ID for this entry
        entry_id = str(uuid4())
        created_at = datetime.now()

        # Prepare payload with cache data
        # Serialize metadata to JSON string for storage backends that
        # don't support nested dicts (e.g., ChromaDB)
        payload = {
            self._QUERY_KEY: query,
            self._RESPONSE_KEY: response,
            self._CREATED_AT_KEY: created_at.isoformat(),
            self._METADATA_KEY: json.dumps(metadata or {}),
        }

        # Create vector record
        record = VectorRecord(
            vector=query_embedding,
            id=entry_id,
            payload=payload,
        )

        # Store in vector storage
        self._vector_storage.add([record])

        logger.debug(f"Cached entry with id={entry_id}")
        return entry_id

    def delete(self, entry_id: str) -> bool:
        r"""Delete a specific cache entry by its ID.

        Args:
            entry_id (str): The unique ID of the cache entry to delete.

        Returns:
            bool: True if the entry was deleted, False if not found.
        """
        try:
            self._vector_storage.delete([entry_id])
            logger.debug(f"Deleted cache entry with id={entry_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete cache entry {entry_id}: {e}")
            return False

    def clear(self) -> None:
        r"""Remove all entries from the cache."""
        self._vector_storage.clear()
        with self._stats_lock:
            self._cache_hits = 0
            self._cache_misses = 0
        logger.info("Cache cleared")

    def find_similar(
        self, query: str, top_k: int = 5
    ) -> List[tuple[CacheRecord, float]]:
        r"""Find the top-k most similar cached queries.

        This method returns similar entries regardless of whether they
        meet the similarity threshold.

        Args:
            query (str): The query to search for.
            top_k (int): Number of results to return. (default: :obj:`5`)

        Returns:
            List[tuple[CacheRecord, float]]: List of (record, similarity)
                tuples sorted by similarity in descending order.
        """
        results = self._query_similar(query, top_k=top_k)
        if not results:
            return []

        # Convert results to CacheRecords using helper
        return [
            (
                self._result_to_cache_record(result),
                self._normalize_similarity(result.similarity),
            )
            for result in results
        ]

    def __repr__(self) -> str:
        return (
            f"SemanticCache("
            f"threshold={self._similarity_threshold}, "
            f"size={self.size}, "
            f"enabled={self._cache_enabled})"
        )
