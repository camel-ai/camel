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

import pytest

from camel.utils.deduplication import deduplicate_internally, DeduplicationResult


class TestLLMSuperviseDeduplication:
    """Test cases for LLM-supervise deduplication strategy."""

    def test_llm_supervise_strategy_exists(self):
        """Test that the llm-supervise strategy is recognized."""
        # Test that the function accepts the strategy parameter
        # This should not raise a NotImplementedError anymore
        # Single text doesn't need embeddings, so it should work
        result = deduplicate_internally(
            texts=["test"],
            strategy="llm-supervise"
        )
        
        # Should return a valid result for single text
        assert isinstance(result, DeduplicationResult)
        assert result.original_texts == ["test"]
        assert result.unique_ids == [0]
        assert result.duplicate_to_target_map == {}

    def test_llm_supervise_strategy_parameter(self):
        """Test that the strategy parameter accepts llm-supervise."""
        import inspect
        sig = inspect.signature(deduplicate_internally)
        strategy_param = sig.parameters['strategy']
        
        # Check that 'llm-supervise' is a valid option
        if hasattr(strategy_param.annotation, '__args__'):
            valid_strategies = strategy_param.annotation.__args__
            assert 'llm-supervise' in valid_strategies, f"llm-supervise not in valid strategies: {valid_strategies}"
            assert 'top1' in valid_strategies, f"top1 not in valid strategies: {valid_strategies}"

    def test_llm_supervise_empty_texts(self):
        """Test llm-supervise with empty text list."""
        result = deduplicate_internally(
            texts=[],
            strategy="llm-supervise"
        )
        
        assert isinstance(result, DeduplicationResult)
        assert result.original_texts == []
        assert result.unique_ids == []
        assert result.unique_embeddings_dict == {}
        assert result.duplicate_to_target_map == {}

    def test_llm_supervise_single_text(self):
        """Test llm-supervise with single text."""
        texts = ["Single text"]
        
        # Mock embeddings for testing
        mock_embeddings = [[0.1, 0.2, 0.3]]
        
        result = deduplicate_internally(
            texts=texts,
            embeddings=mock_embeddings,
            strategy="llm-supervise"
        )
        
        assert isinstance(result, DeduplicationResult)
        assert result.original_texts == texts
        assert result.unique_ids == [0]
        assert result.unique_embeddings_dict == {0: mock_embeddings[0]}
        assert result.duplicate_to_target_map == {}

    def test_llm_supervise_invalid_threshold(self):
        """Test llm-supervise with invalid threshold."""
        texts = ["text1", "text2"]
        mock_embeddings = [[0.1, 0.2], [0.3, 0.4]]
        
        with pytest.raises(ValueError, match="Threshold must be between 0 and 1"):
            deduplicate_internally(
                texts=texts,
                embeddings=mock_embeddings,
                threshold=1.5,  # Invalid threshold
                strategy="llm-supervise"
            )

    def test_llm_supervise_missing_embeddings(self):
        """Test llm-supervise without providing embeddings."""
        texts = ["text1", "text2"]
        
        with pytest.raises(ValueError, match="Either 'embedding_instance' or 'embeddings' must be provided"):
            deduplicate_internally(
                texts=texts,
                strategy="llm-supervise"
            )

    def test_llm_supervise_mismatched_embeddings_length(self):
        """Test llm-supervise with mismatched embeddings length."""
        texts = ["text1", "text2"]
        mock_embeddings = [[0.1, 0.2]]  # Only one embedding for two texts
        
        with pytest.raises(ValueError, match="The length of 'embeddings' does not match the length of 'texts'"):
            deduplicate_internally(
                texts=texts,
                embeddings=mock_embeddings,
                strategy="llm-supervise"
            )

    def test_llm_supervise_both_embedding_sources_provided(self):
        """Test llm-supervise with both embedding_instance and embeddings."""
        texts = ["text1", "text2"]
        mock_embeddings = [[0.1, 0.2], [0.3, 0.4]]
        
        # Mock embedding instance
        class MockEmbedding:
            def embed_list(self, texts):
                return [[0.1, 0.2], [0.3, 0.4]]
        
        with pytest.raises(ValueError, match="Cannot provide both 'embedding_instance' and 'embeddings'"):
            deduplicate_internally(
                texts=texts,
                embeddings=mock_embeddings,
                embedding_instance=MockEmbedding(),
                strategy="llm-supervise"
            )

    def test_llm_supervise_basic_functionality(self):
        """Test basic llm-supervise functionality with mock data."""
        texts = [
            "What is artificial intelligence?",
            "AI is a field of computer science",
            "What is artificial intelligence?",  # Duplicate
            "Deep learning is a subset of AI",
        ]
        
        # Mock embeddings with high similarity for duplicates
        mock_embeddings = [
            [0.1, 0.2, 0.3],  # text 0
            [0.4, 0.5, 0.6],  # text 1
            [0.1, 0.2, 0.3],  # text 2 (same as text 0)
            [0.7, 0.8, 0.9],  # text 3
        ]
        
        result = deduplicate_internally(
            texts=texts,
            embeddings=mock_embeddings,
            threshold=0.8,  # High threshold to avoid false positives in test
            strategy="llm-supervise"
        )
        
        assert isinstance(result, DeduplicationResult)
        assert result.original_texts == texts
        # Should have unique IDs (exact behavior depends on LLM judgment)
        assert len(result.unique_ids) >= 1
        assert len(result.unique_embeddings_dict) >= 1 