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

from unittest.mock import MagicMock

import pytest

from camel.caches import CacheRecord, SemanticCache


class TestCacheRecord:
    """Tests for the CacheRecord dataclass."""

    def test_cache_record_creation(self):
        """Test that CacheRecord can be created with required fields."""
        record = CacheRecord(
            query="test query",
            response="test response",
            query_id="test-id-123",
        )
        assert record.query == "test query"
        assert record.response == "test response"
        assert record.query_id == "test-id-123"
        assert record.metadata == {}
        assert record.created_at is not None

    def test_cache_record_with_metadata(self):
        """Test CacheRecord with custom metadata."""
        metadata = {"source": "test", "version": 1}
        record = CacheRecord(
            query="test query",
            response="test response",
            query_id="test-id-123",
            metadata=metadata,
        )
        assert record.metadata == metadata


class TestSemanticCache:
    """Tests for the SemanticCache implementation."""

    @pytest.fixture
    def mock_embedding_model(self):
        """Create a mock embedding model."""
        mock = MagicMock()
        mock.embed.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        mock.get_output_dim.return_value = 5
        return mock

    @pytest.fixture
    def mock_vector_storage(self):
        """Create a mock vector storage."""
        mock = MagicMock()
        mock.status.return_value = MagicMock(vector_count=0)
        mock.query.return_value = []
        return mock

    @pytest.fixture
    def cache(self, mock_embedding_model, mock_vector_storage):
        """Create a SemanticCache instance with mocks."""
        return SemanticCache(
            embedding_model=mock_embedding_model,
            vector_storage=mock_vector_storage,
            similarity_threshold=0.85,
        )

    def test_cache_initialization(self, cache):
        """Test that cache initializes with default values."""
        assert cache.similarity_threshold == 0.85
        assert cache.enabled is True
        assert cache.size == 0
        assert cache.hit_rate == 0.0

    def test_cache_initialization_invalid_threshold(
        self, mock_embedding_model, mock_vector_storage
    ):
        """Test that invalid threshold raises ValueError."""
        with pytest.raises(ValueError, match="similarity_threshold must be"):
            SemanticCache(
                embedding_model=mock_embedding_model,
                vector_storage=mock_vector_storage,
                similarity_threshold=1.5,
            )

        with pytest.raises(ValueError, match="similarity_threshold must be"):
            SemanticCache(
                embedding_model=mock_embedding_model,
                vector_storage=mock_vector_storage,
                similarity_threshold=-0.1,
            )

    def test_set_stores_entry(self, cache, mock_vector_storage):
        """Test that set() stores the query-response pair."""
        entry_id = cache.set("What is Python?", "A programming language.")

        assert entry_id is not None
        mock_vector_storage.add.assert_called_once()

        # Check the stored record
        call_args = mock_vector_storage.add.call_args[0][0]
        assert len(call_args) == 1
        record = call_args[0]
        assert record.payload["query"] == "What is Python?"
        assert record.payload["response"] == "A programming language."

    def test_set_with_metadata(self, cache, mock_vector_storage):
        """Test that set() stores metadata correctly."""
        import json

        metadata = {"source": "test", "model": "gpt-4"}
        cache.set("Query", "Response", metadata=metadata)

        call_args = mock_vector_storage.add.call_args[0][0]
        record = call_args[0]
        # Metadata is stored as JSON string for storage backend compatibility
        assert json.loads(record.payload["metadata"]) == metadata

    def test_set_empty_query_raises(self, cache):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            cache.set("", "Some response")

        with pytest.raises(ValueError, match="Query cannot be empty"):
            cache.set("   ", "Some response")

    def test_set_empty_response_raises(self, cache):
        """Test that empty response raises ValueError."""
        with pytest.raises(ValueError, match="Response cannot be empty"):
            cache.set("Some query", "")

    def test_get_cache_hit(
        self, cache, mock_vector_storage, mock_embedding_model
    ):
        """Test cache hit when similarity exceeds threshold."""
        # Mock a similar query result
        mock_result = MagicMock()
        mock_result.similarity = 0.95  # Above threshold
        mock_result.record.payload = {
            "query": "What is Python?",
            "response": "A programming language.",
            "created_at": "2026-01-01T00:00:00",
            "metadata": {},
        }
        mock_result.record.id = "test-id"
        mock_vector_storage.query.return_value = [mock_result]

        response = cache.get("What's Python?")

        assert response == "A programming language."
        assert cache.stats["hits"] == 1
        assert cache.stats["misses"] == 0

    def test_get_cache_miss_below_threshold(
        self, cache, mock_vector_storage, mock_embedding_model
    ):
        """Test cache miss when similarity is below threshold."""
        # Mock a query result below threshold
        mock_result = MagicMock()
        mock_result.similarity = 0.5  # Below threshold
        mock_result.record.payload = {
            "query": "Unrelated query",
            "response": "Unrelated response",
        }
        mock_vector_storage.query.return_value = [mock_result]

        response = cache.get("What is Python?")

        assert response is None
        assert cache.stats["hits"] == 0
        assert cache.stats["misses"] == 1

    def test_get_cache_miss_empty_results(self, cache, mock_vector_storage):
        """Test cache miss when no results found."""
        mock_vector_storage.query.return_value = []

        response = cache.get("Some query")

        assert response is None
        assert cache.stats["misses"] == 1

    def test_get_disabled_cache(self, cache):
        """Test that get returns None when cache is disabled."""
        cache.enabled = False
        response = cache.get("Any query")
        assert response is None

    def test_get_empty_query(self, cache):
        """Test that empty query returns None."""
        assert cache.get("") is None
        assert cache.get("   ") is None

    def test_clear_resets_cache(self, cache, mock_vector_storage):
        """Test that clear removes all entries and resets stats."""
        # Simulate some hits and misses
        cache._cache_hits = 5
        cache._cache_misses = 3

        cache.clear()

        mock_vector_storage.clear.assert_called_once()
        assert cache.stats["hits"] == 0
        assert cache.stats["misses"] == 0

    def test_hit_rate_calculation(self, cache):
        """Test hit rate calculation."""
        cache._cache_hits = 3
        cache._cache_misses = 7

        assert cache.hit_rate == 0.3  # 3 / (3 + 7) = 0.3

    def test_hit_rate_no_lookups(self, cache):
        """Test hit rate is 0.0 when no lookups have been made."""
        assert cache.hit_rate == 0.0

    def test_similarity_threshold_setter(self, cache):
        """Test setting similarity threshold."""
        cache.similarity_threshold = 0.9
        assert cache.similarity_threshold == 0.9

        with pytest.raises(ValueError):
            cache.similarity_threshold = 1.5

        with pytest.raises(ValueError):
            cache.similarity_threshold = -0.1

    def test_enabled_property(self, cache):
        """Test enabling and disabling cache."""
        assert cache.enabled is True
        cache.enabled = False
        assert cache.enabled is False
        cache.enabled = True
        assert cache.enabled is True

    def test_stats_property(self, cache):
        """Test stats property returns correct structure."""
        cache._cache_hits = 10
        cache._cache_misses = 5

        stats = cache.stats

        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert "size" in stats
        assert "enabled" in stats
        assert "similarity_threshold" in stats
        assert stats["hits"] == 10
        assert stats["misses"] == 5

    def test_find_similar(
        self, cache, mock_vector_storage, mock_embedding_model
    ):
        """Test finding similar cached queries."""
        # Mock multiple results
        mock_results = []
        for i, sim in enumerate([0.95, 0.85, 0.75]):
            result = MagicMock()
            result.similarity = sim
            result.record.id = f"id-{i}"
            result.record.payload = {
                "query": f"Query {i}",
                "response": f"Response {i}",
                "created_at": "2026-01-01T00:00:00",
                "metadata": {},
            }
            mock_results.append(result)

        mock_vector_storage.query.return_value = mock_results

        results = cache.find_similar("test query", top_k=3)

        assert len(results) == 3
        assert results[0][1] == 0.95  # Highest similarity first
        assert results[0][0].query == "Query 0"

    def test_delete(self, cache, mock_vector_storage):
        """Test deleting a cache entry."""
        result = cache.delete("test-id")

        assert result is True
        mock_vector_storage.delete.assert_called_once_with(["test-id"])

    def test_delete_failure(self, cache, mock_vector_storage):
        """Test delete returns False on error."""
        mock_vector_storage.delete.side_effect = Exception("Delete failed")

        result = cache.delete("test-id")

        assert result is False

    def test_get_with_score(
        self, cache, mock_vector_storage, mock_embedding_model
    ):
        """Test get_with_score returns response with similarity."""
        mock_result = MagicMock()
        mock_result.similarity = 0.92
        mock_result.record.id = "test-id"
        mock_result.record.payload = {
            "query": "Original query",
            "response": "Cached response",
            "created_at": "2026-01-01T00:00:00",
            "metadata": {"source": "test"},
        }
        mock_vector_storage.query.return_value = [mock_result]

        result = cache.get_with_score("Similar query")

        assert result is not None
        response, score, record = result
        assert response == "Cached response"
        assert score == 0.92
        assert record.query == "Original query"
        assert record.metadata == {"source": "test"}

    def test_repr(self, cache):
        """Test string representation."""
        repr_str = repr(cache)
        assert "SemanticCache" in repr_str
        assert "threshold=0.85" in repr_str
        assert "enabled=True" in repr_str
