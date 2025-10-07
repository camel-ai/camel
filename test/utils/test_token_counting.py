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

from unittest.mock import Mock

import pytest

from camel.types import ModelType
from camel.utils import (
    AnthropicTokenCounter,
    LiteLLMTokenCounter,
    MistralTokenCounter,
    OpenAITokenCounter,
)


class TestOpenAIUsageExtraction:
    """Test usage extraction for OpenAI token counter."""

    def test_extract_basic_usage(self):
        """Test extracting basic usage data from OpenAI response."""

        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)

        # Create mock response with spec to prevent auto-creation of attributes
        mock_response = Mock()
        mock_response.usage = Mock(
            spec=['prompt_tokens', 'completion_tokens', 'total_tokens']
        )
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 25
        mock_response.usage.total_tokens = 75

        # Extract usage
        usage = counter.extract_usage_from_response(mock_response)

        # Validate
        assert usage is not None
        assert usage["prompt_tokens"] == 50
        assert usage["completion_tokens"] == 25
        assert usage["total_tokens"] == 75
        assert len(usage) == 3  # Only basic fields

    def test_extract_usage_with_prompt_caching(self):
        """Test extracting usage with prompt caching (cached_tokens)."""

        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)

        # Mock response with cached tokens
        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 200
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 250
        mock_response.usage.prompt_tokens_details = Mock()
        mock_response.usage.prompt_tokens_details.cached_tokens = 150

        usage = counter.extract_usage_from_response(mock_response)

        # Validate caching info is extracted
        assert usage is not None
        assert usage["prompt_tokens"] == 200
        assert usage["completion_tokens"] == 50
        assert usage["total_tokens"] == 250
        assert usage["cached_tokens"] == 150

        # Verify 150 out of 200 prompt tokens were cached (75% cache hit)
        cache_hit_rate = usage["cached_tokens"] / usage["prompt_tokens"]
        assert cache_hit_rate == 0.75

    def test_extract_usage_zero_tokens(self):
        """Test extracting usage when all token counts are zero."""

        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)

        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 0
        mock_response.usage.completion_tokens = 0
        mock_response.usage.total_tokens = 0

        usage = counter.extract_usage_from_response(mock_response)

        # Should still return dict with zero values
        assert usage is not None
        assert usage["prompt_tokens"] == 0
        assert usage["completion_tokens"] == 0
        assert usage["total_tokens"] == 0

    def test_extract_usage_no_usage_object(self):
        """Test extracting usage when response has no usage object."""

        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)

        mock_response = Mock()
        mock_response.usage = None

        usage = counter.extract_usage_from_response(mock_response)

        # Should return None when usage unavailable
        assert usage is None

    def test_extract_usage_malformed_response(self):
        """Test extracting usage from malformed response."""

        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)

        # Response without usage attribute
        mock_response = Mock(spec=[])

        usage = counter.extract_usage_from_response(mock_response)

        # Should handle gracefully and return None
        assert usage is None

    def test_extract_usage_partial_fields(self):
        """Test extracting usage when some fields are missing."""

        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)

        # Use spec to only allow prompt_tokens attribute
        mock_response = Mock()
        mock_response.usage = Mock(spec=['prompt_tokens'])
        mock_response.usage.prompt_tokens = 100
        # Missing completion_tokens and total_tokens

        usage = counter.extract_usage_from_response(mock_response)

        # Should extract available fields with defaults
        assert usage is not None
        assert usage["prompt_tokens"] == 100
        assert usage["completion_tokens"] == 0  # Default
        assert usage["total_tokens"] == 0  # Default

    def test_extract_usage_cached_tokens_zero(self):
        """Test extracting usage with zero cached tokens."""

        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)

        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_response.usage.prompt_tokens_details = Mock()
        mock_response.usage.prompt_tokens_details.cached_tokens = 0

        usage = counter.extract_usage_from_response(mock_response)

        # Should still include cached_tokens even if zero
        assert usage["cached_tokens"] == 0


class TestAnthropicUsageExtraction:
    """Test usage extraction for Anthropic token counter."""

    def test_extract_basic_usage(self):
        """Test extracting basic usage from Anthropic response."""

        counter = AnthropicTokenCounter("claude-3-sonnet-20240229")

        # Anthropic uses input_tokens/output_tokens
        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 120
        mock_response.usage.output_tokens = 80

        usage = counter.extract_usage_from_response(mock_response)

        # Should map to standard field names
        assert usage is not None
        assert usage["prompt_tokens"] == 120  # Mapped from input_tokens
        assert usage["completion_tokens"] == 80  # Mapped from output_tokens
        assert usage["total_tokens"] == 200  # Calculated

    def test_extract_usage_with_cache_creation(self):
        """Test extracting usage with cache creation tokens."""

        counter = AnthropicTokenCounter("claude-3-sonnet-20240229")

        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 500
        mock_response.usage.output_tokens = 100
        mock_response.usage.cache_creation_input_tokens = 450

        usage = counter.extract_usage_from_response(mock_response)

        assert usage is not None
        assert usage["prompt_tokens"] == 500
        assert usage["completion_tokens"] == 100
        assert usage["total_tokens"] == 600
        assert usage["cache_creation_input_tokens"] == 450

    def test_extract_usage_with_cache_read(self):
        """Test extracting usage with cache read tokens."""

        counter = AnthropicTokenCounter("claude-3-sonnet-20240229")

        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.usage.cache_read_input_tokens = 400

        usage = counter.extract_usage_from_response(mock_response)

        assert usage is not None
        assert usage["cache_read_input_tokens"] == 400

        # Cache read tokens save 90% cost in Anthropic pricing
        print(
            f"\nCache efficiency: {usage['cache_read_input_tokens']}"
            f"tokens read from cache"
        )

    def test_extract_usage_with_full_caching(self):
        """Test extracting usage with both cache creation and read."""

        counter = AnthropicTokenCounter("claude-3-sonnet-20240229")

        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 1000
        mock_response.usage.output_tokens = 200
        mock_response.usage.cache_creation_input_tokens = 800
        mock_response.usage.cache_read_input_tokens = 600

        usage = counter.extract_usage_from_response(mock_response)

        assert usage is not None
        assert usage["cache_creation_input_tokens"] == 800
        assert usage["cache_read_input_tokens"] == 600

        # Both creation and read can be present in same response
        total_cache_activity = (
            usage["cache_creation_input_tokens"]
            + usage["cache_read_input_tokens"]
        )
        assert total_cache_activity == 1400

    def test_extract_usage_no_usage_object(self):
        """Test extracting usage when Anthropic response has no usage."""

        counter = AnthropicTokenCounter("claude-3-sonnet-20240229")

        mock_response = Mock()
        mock_response.usage = None

        usage = counter.extract_usage_from_response(mock_response)

        assert usage is None


class TestLiteLLMUsageExtraction:
    """Test usage extraction for LiteLLM token counter."""

    def test_extract_basic_usage(self):
        """Test extracting usage from LiteLLM response."""

        counter = LiteLLMTokenCounter(ModelType.GPT_4O_MINI)

        # LiteLLM uses OpenAI-compatible format
        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 75
        mock_response.usage.completion_tokens = 35
        mock_response.usage.total_tokens = 110

        usage = counter.extract_usage_from_response(mock_response)

        assert usage is not None
        assert usage["prompt_tokens"] == 75
        assert usage["completion_tokens"] == 35
        assert usage["total_tokens"] == 110

    def test_extract_usage_inherits_from_openai(self):
        """Test that LiteLLM inherits OpenAI extraction behavior."""

        counter = LiteLLMTokenCounter(ModelType.GPT_4O_MINI)

        # Test with cached tokens (OpenAI feature)
        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 200
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 250
        mock_response.usage.prompt_tokens_details = Mock()
        mock_response.usage.prompt_tokens_details.cached_tokens = 180

        usage = counter.extract_usage_from_response(mock_response)

        # Should support cached tokens like OpenAI
        assert usage is not None
        assert usage["cached_tokens"] == 180


class TestMistralUsageExtraction:
    """Test usage extraction for Mistral token counter."""

    def test_extract_basic_usage(self):
        """Test extracting basic usage from Mistral response."""

        counter = MistralTokenCounter(ModelType.MISTRAL_LARGE)

        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 90
        mock_response.usage.completion_tokens = 60
        mock_response.usage.total_tokens = 150

        usage = counter.extract_usage_from_response(mock_response)

        assert usage is not None
        assert usage["prompt_tokens"] == 90
        assert usage["completion_tokens"] == 60
        assert usage["total_tokens"] == 150

    def test_extract_usage_calculated_total(self):
        """Test extracting usage when total_tokens is missing."""

        counter = MistralTokenCounter(ModelType.MISTRAL_LARGE)

        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        # total_tokens not provided

        usage = counter.extract_usage_from_response(mock_response)

        # Should calculate total_tokens automatically
        assert usage is not None
        assert usage["prompt_tokens"] == 100
        assert usage["completion_tokens"] == 50
        assert usage["total_tokens"] == 150  # Calculated: 100 + 50

    def test_extract_usage_with_cached_tokens(self):
        """Test extracting usage with Mistral's cached tokens."""

        counter = MistralTokenCounter(ModelType.MISTRAL_LARGE)

        mock_response = Mock()
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 300
        mock_response.usage.completion_tokens = 100
        mock_response.usage.total_tokens = 400
        mock_response.usage.prompt_tokens_details = Mock()
        mock_response.usage.prompt_tokens_details.cached_tokens = 250

        usage = counter.extract_usage_from_response(mock_response)

        assert usage is not None
        assert usage["cached_tokens"] == 250


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
