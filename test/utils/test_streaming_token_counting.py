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

"""
Comprehensive tests for streaming token counting functionality.

This module tests the streaming token counting capabilities across different
providers, including OpenAI's stream_options feature and other provider-specific
streaming usage extraction methods.
"""

import pytest
from unittest.mock import Mock
from typing import Iterator, AsyncIterator

# Import token counters with conditional availability
try:
    from camel.utils import OpenAITokenCounter
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    class OpenAITokenCounter:
        def __init__(self, *args, **kwargs):
            pass

try:
    from camel.utils import AnthropicTokenCounter
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    class AnthropicTokenCounter:
        def __init__(self, *args, **kwargs):
            pass

try:
    from camel.utils import LiteLLMTokenCounter
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    class LiteLLMTokenCounter:
        def __init__(self, *args, **kwargs):
            pass

try:
    from camel.utils import MistralTokenCounter
    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False
    class MistralTokenCounter:
        def __init__(self, *args, **kwargs):
            pass

from camel.types import ModelType


class TestOpenAIStreamingTokenCounter:
    """Test streaming token counting for OpenAI models."""

    def test_extract_usage_from_sync_streaming_response(self):
        """Test extracting usage from synchronous OpenAI streaming response."""
        if not OPENAI_AVAILABLE:
            pytest.skip("OpenAI not available")
            
        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        
        # Mock streaming chunks - OpenAI sends usage in final chunk
        def mock_stream() -> Iterator[Mock]:
            # Regular content chunks
            chunk1 = Mock()
            chunk1.choices = [Mock()]
            chunk1.usage = None
            yield chunk1
            
            chunk2 = Mock()
            chunk2.choices = [Mock()]
            chunk2.usage = None
            yield chunk2
            
            # Final chunk with usage data
            final_chunk = Mock()
            final_chunk.choices = [Mock()]
            final_chunk.usage = Mock()
            final_chunk.usage.prompt_tokens = 15
            final_chunk.usage.completion_tokens = 25
            final_chunk.usage.total_tokens = 40
            yield final_chunk
        
        usage = counter.extract_usage_from_streaming_response(mock_stream())
        
        assert usage is not None
        assert usage['prompt_tokens'] == 15
        assert usage['completion_tokens'] == 25
        assert usage['total_tokens'] == 40

    @pytest.mark.asyncio
    async def test_extract_usage_from_async_streaming_response(self):
        """Test extracting usage from asynchronous OpenAI streaming response."""
        if not OPENAI_AVAILABLE:
            pytest.skip("OpenAI not available")
            
        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        
        # Mock async streaming chunks
        async def mock_async_stream() -> AsyncIterator[Mock]:
            # Regular content chunks
            chunk1 = Mock()
            chunk1.choices = [Mock()]
            chunk1.usage = None
            yield chunk1
            
            chunk2 = Mock()
            chunk2.choices = [Mock()]
            chunk2.usage = None
            yield chunk2
            
            # Final chunk with usage data
            final_chunk = Mock()
            final_chunk.choices = [Mock()]
            final_chunk.usage = Mock()
            final_chunk.usage.prompt_tokens = 20
            final_chunk.usage.completion_tokens = 30
            final_chunk.usage.total_tokens = 50
            yield final_chunk
        
        usage = await counter.extract_usage_from_async_streaming_response(mock_async_stream())
        
        assert usage is not None
        assert usage['prompt_tokens'] == 20
        assert usage['completion_tokens'] == 30
        assert usage['total_tokens'] == 50

    def test_extract_usage_from_streaming_response_no_usage(self):
        """Test streaming response without usage data."""
        if not OPENAI_AVAILABLE:
            pytest.skip("OpenAI not available")
            
        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        
        def mock_stream_no_usage() -> Iterator[Mock]:
            chunk1 = Mock()
            chunk1.choices = [Mock()]
            chunk1.usage = None
            yield chunk1
            
            chunk2 = Mock()
            chunk2.choices = [Mock()]
            chunk2.usage = None
            yield chunk2
        
        usage = counter.extract_usage_from_streaming_response(mock_stream_no_usage())
        assert usage is None

    def test_extract_usage_from_streaming_response_early_usage(self):
        """Test streaming response with usage data in middle chunk."""
        if not OPENAI_AVAILABLE:
            pytest.skip("OpenAI not available")
            
        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        
        def mock_stream_early_usage() -> Iterator[Mock]:
            chunk1 = Mock()
            chunk1.choices = [Mock()]
            chunk1.usage = None
            yield chunk1
            
            # Usage in middle chunk
            chunk2 = Mock()
            chunk2.choices = [Mock()]
            chunk2.usage = Mock()
            chunk2.usage.prompt_tokens = 10
            chunk2.usage.completion_tokens = 15
            chunk2.usage.total_tokens = 25
            yield chunk2
            
            chunk3 = Mock()
            chunk3.choices = [Mock()]
            chunk3.usage = None
            yield chunk3
        
        usage = counter.extract_usage_from_streaming_response(mock_stream_early_usage())
        
        assert usage is not None
        assert usage['prompt_tokens'] == 10
        assert usage['completion_tokens'] == 15
        assert usage['total_tokens'] == 25


class TestAnthropicStreamingTokenCounter:
    """Test streaming token counting for Anthropic models."""

    def test_extract_usage_from_sync_streaming_response(self):
        """Test extracting usage from synchronous Anthropic streaming response."""
        if not ANTHROPIC_AVAILABLE:
            pytest.skip("Anthropic not available")
            
        counter = AnthropicTokenCounter("claude-3-sonnet-20240229")
        
        def mock_anthropic_stream() -> Iterator[Mock]:
            # Anthropic includes usage in message events
            chunk1 = Mock()
            chunk1.usage = Mock()
            chunk1.usage.input_tokens = 12
            chunk1.usage.output_tokens = 18
            yield chunk1
            
            chunk2 = Mock()
            chunk2.usage = None
            yield chunk2
        
        usage = counter.extract_usage_from_streaming_response(mock_anthropic_stream())
        
        assert usage is not None
        assert usage['prompt_tokens'] == 12
        assert usage['completion_tokens'] == 18
        assert usage['total_tokens'] == 30

    @pytest.mark.asyncio
    async def test_extract_usage_from_async_streaming_response(self):
        """Test extracting usage from asynchronous Anthropic streaming response."""
        if not ANTHROPIC_AVAILABLE:
            pytest.skip("Anthropic not available")
            
        counter = AnthropicTokenCounter("claude-3-sonnet-20240229")
        
        async def mock_anthropic_async_stream() -> AsyncIterator[Mock]:
            chunk1 = Mock()
            chunk1.usage = Mock()
            chunk1.usage.input_tokens = 8
            chunk1.usage.output_tokens = 12
            yield chunk1
        
        usage = await counter.extract_usage_from_async_streaming_response(mock_anthropic_async_stream())
        
        assert usage is not None
        assert usage['prompt_tokens'] == 8
        assert usage['completion_tokens'] == 12
        assert usage['total_tokens'] == 20


class TestLiteLLMStreamingTokenCounter:
    """Test streaming token counting for LiteLLM models."""

    def test_extract_usage_from_sync_streaming_response(self):
        """Test extracting usage from synchronous LiteLLM streaming response."""
        if not LITELLM_AVAILABLE:
            pytest.skip("LiteLLM not available")
            
        counter = LiteLLMTokenCounter(ModelType.GPT_4O_MINI)
        
        def mock_litellm_stream() -> Iterator[Mock]:
            chunk1 = Mock()
            chunk1.usage = None
            yield chunk1
            
            # Final chunk with usage
            final_chunk = Mock()
            final_chunk.usage = Mock()
            final_chunk.usage.prompt_tokens = 22
            final_chunk.usage.completion_tokens = 33
            final_chunk.usage.total_tokens = 55
            yield final_chunk
        
        usage = counter.extract_usage_from_streaming_response(mock_litellm_stream())
        
        assert usage is not None
        assert usage['prompt_tokens'] == 22
        assert usage['completion_tokens'] == 33
        assert usage['total_tokens'] == 55


class TestMistralStreamingTokenCounter:
    """Test streaming token counting for Mistral models."""

    def test_extract_usage_from_sync_streaming_response(self):
        """Test extracting usage from synchronous Mistral streaming response."""
        if not MISTRAL_AVAILABLE:
            pytest.skip("Mistral not available")
            
        counter = MistralTokenCounter(ModelType.MISTRAL_LARGE)
        
        def mock_mistral_stream() -> Iterator[Mock]:
            chunk1 = Mock()
            chunk1.usage = None
            yield chunk1
            
            # Final chunk with usage
            final_chunk = Mock()
            final_chunk.usage = Mock()
            final_chunk.usage.prompt_tokens = 18
            final_chunk.usage.completion_tokens = 27
            yield final_chunk
        
        usage = counter.extract_usage_from_streaming_response(mock_mistral_stream())
        
        assert usage is not None
        assert usage['prompt_tokens'] == 18
        assert usage['completion_tokens'] == 27
        assert usage['total_tokens'] == 45  # Should be calculated


class TestStreamingTokenCountingEdgeCases:
    """Test edge cases and error handling for streaming token counting."""

    def test_empty_stream(self):
        """Test handling of empty streams."""
        if not OPENAI_AVAILABLE:
            pytest.skip("OpenAI not available")
            
        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        
        def empty_stream() -> Iterator[Mock]:
            return
            yield  # This line never executes
        
        usage = counter.extract_usage_from_streaming_response(empty_stream())
        assert usage is None

    def test_stream_with_exception(self):
        """Test handling of streams that raise exceptions."""
        if not OPENAI_AVAILABLE:
            pytest.skip("OpenAI not available")
            
        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        
        def error_stream() -> Iterator[Mock]:
            chunk1 = Mock()
            chunk1.usage = None
            yield chunk1
            
            raise Exception("Stream error")
        
        usage = counter.extract_usage_from_streaming_response(error_stream())
        assert usage is None

    @pytest.mark.asyncio
    async def test_async_stream_with_exception(self):
        """Test handling of async streams that raise exceptions."""
        if not OPENAI_AVAILABLE:
            pytest.skip("OpenAI not available")
            
        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        
        async def error_async_stream() -> AsyncIterator[Mock]:
            chunk1 = Mock()
            chunk1.usage = None
            yield chunk1
            
            raise Exception("Async stream error")
        
        usage = await counter.extract_usage_from_async_streaming_response(error_async_stream())
        assert usage is None

    def test_mixed_stream_types(self):
        """Test handling of unsupported stream types."""
        if not OPENAI_AVAILABLE:
            pytest.skip("OpenAI not available")
            
        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        
        usage = counter.extract_usage_from_streaming_response("not_a_stream")
        assert usage is None



class TestStreamingUsageUtils:
    """Test streaming usage utility functions."""

    def test_enable_streaming_usage_for_openai(self):
        """Test enabling streaming usage for OpenAI configuration."""
        from examples.token_counter.streaming_token_counting_utils import enable_streaming_usage_for_openai
        
        config = {"stream": True, "temperature": 0.7}
        updated_config = enable_streaming_usage_for_openai(config)
        
        assert updated_config["stream"] is True
        assert updated_config["temperature"] == 0.7
        assert updated_config["stream_options"]["include_usage"] is True

    def test_enable_streaming_usage_for_openai_no_stream(self):
        """Test that stream_options is not added when streaming is disabled."""
        from examples.token_counter.streaming_token_counting_utils import enable_streaming_usage_for_openai
        
        config = {"stream": False, "temperature": 0.7}
        updated_config = enable_streaming_usage_for_openai(config)
        
        assert "stream_options" not in updated_config

    def test_get_streaming_usage_config_for_provider(self):
        """Test provider-specific streaming configuration."""
        from examples.token_counter.streaming_token_counting_utils import get_streaming_usage_config_for_provider
        
        base_config = {"stream": True, "temperature": 0.5}
        
        openai_config = get_streaming_usage_config_for_provider("openai", base_config)
        assert openai_config["stream_options"]["include_usage"] is True
        
        anthropic_config = get_streaming_usage_config_for_provider("anthropic", base_config)
        assert "stream_options" not in anthropic_config
        
        unknown_config = get_streaming_usage_config_for_provider("unknown", base_config)
        assert unknown_config == base_config

    def test_validate_streaming_usage_support(self):
        """Test validation of streaming usage support."""
        from examples.token_counter.streaming_token_counting_utils import validate_streaming_usage_support
        
        openai_config = {
            "stream": True,
            "stream_options": {"include_usage": True}
        }
        assert validate_streaming_usage_support("openai", openai_config) is True
        
        openai_config_bad = {"stream": True}
        assert validate_streaming_usage_support("openai", openai_config_bad) is False
        
        anthropic_config = {"stream": True}
        assert validate_streaming_usage_support("anthropic", anthropic_config) is True
        
        non_streaming_config = {"stream": False}
        assert validate_streaming_usage_support("openai", non_streaming_config) is True


if __name__ == "__main__":
    pytest.main([__file__])
