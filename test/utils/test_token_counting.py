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
from unittest.mock import Mock
from PIL import Image

from camel.types import ModelType, OpenAIVisionDetailType
from camel.utils import (
    OpenAITokenCounter,
    LiteLLMTokenCounter,
)

try:
    from camel.utils import AnthropicTokenCounter
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from camel.utils import MistralTokenCounter
    MISTRAL_AVAILABLE = True
except ImportError:
    MISTRAL_AVAILABLE = False


@pytest.mark.parametrize(
    "width,height,detail,token_cost",
    [
        (1024, 1024, OpenAIVisionDetailType.HIGH, 765),
        (1024, 1024, OpenAIVisionDetailType.AUTO, 765),
        (2048, 4096, OpenAIVisionDetailType.HIGH, 1105),
        (2048, 4096, OpenAIVisionDetailType.LOW, 85),
    ],
)
def test_openai_count_token_from_image(
    width: int, height: int, detail: OpenAIVisionDetailType, token_cost: int
):
    image = Image.new("RGB", (width, height), "black")
    assert (
        OpenAITokenCounter(ModelType.GPT_4O_MINI)._count_tokens_from_image(
            image, detail
        )
        == token_cost
    )


class TestOpenAITokenCounterExtractUsage:
    """Test cases for OpenAI token counter extract_usage_from_response method."""

    def test_extract_usage_from_openai_response_object(self):
        """Test extracting usage from OpenAI response object with usage attribute."""
        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        
        # Mock OpenAI response object
        mock_usage = Mock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        
        mock_response = Mock()
        mock_response.usage = mock_usage
        
        result = counter.extract_usage_from_response(mock_response)
        
        assert result == {
            'prompt_tokens': 100,
            'completion_tokens': 50,
            'total_tokens': 150,
        }

    def test_extract_usage_from_streaming_response(self):
        """Test extracting usage from streaming response."""
        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        
        mock_usage = Mock()
        mock_usage.prompt_tokens = 120
        mock_usage.completion_tokens = 80
        mock_usage.total_tokens = 200
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.usage = mock_usage
        
        result = counter.extract_usage_from_response(mock_response)
        
        assert result == {
            'prompt_tokens': 120,
            'completion_tokens': 80,
            'total_tokens': 200,
        }

    def test_extract_usage_no_usage_data(self):
        """Test extracting usage when no usage data is available."""
        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        mock_response = Mock()
        mock_response.usage = None
        result = counter.extract_usage_from_response(mock_response)
        
        assert result is None


    def test_extract_usage_exception_handling(self):
        """Test that exceptions are handled gracefully."""
        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        mock_response = object()
        result = counter.extract_usage_from_response(mock_response)
        assert result is None


class TestAnthropicTokenCounterExtractUsage:
    """Test cases for Anthropic token counter extract_usage_from_response method."""

    def test_extract_usage_from_anthropic_response_object(self):
        """Test extracting usage from Anthropic response object."""
        if not ANTHROPIC_AVAILABLE:
            pytest.skip("anthropic module not available")
            
        counter = AnthropicTokenCounter("claude-3-sonnet-20240229")
        mock_usage = Mock()
        mock_usage.input_tokens = 150
        mock_usage.output_tokens = 75
        mock_response = Mock()
        mock_response.usage = mock_usage
        result = counter.extract_usage_from_response(mock_response)
        
        assert result == {
            'prompt_tokens': 150,
            'completion_tokens': 75,
            'total_tokens': 225,
        }

    def test_extract_usage_anthropic_no_usage_data(self):
        """Test extracting usage when no usage data is available."""
        if not ANTHROPIC_AVAILABLE:
            pytest.skip("anthropic module not available")
            
        counter = AnthropicTokenCounter("claude-3-sonnet-20240229")
        mock_response = Mock()
        mock_response.usage = None
        result = counter.extract_usage_from_response(mock_response)
        assert result is None

    def test_extract_usage_anthropic_exception_handling(self):
        """Test that exceptions are handled gracefully."""
        if not ANTHROPIC_AVAILABLE:
            pytest.skip("anthropic module not available")
            
        counter = AnthropicTokenCounter("claude-3-sonnet-20240229")
        mock_response = object()
        result = counter.extract_usage_from_response(mock_response)
        assert result is None


class TestLiteLLMTokenCounterExtractUsage:
    """Test cases for LiteLLM token counter extract_usage_from_response method."""

    def test_extract_usage_from_litellm_response_object(self):
        """Test extracting usage from LiteLLM response object."""
        counter = LiteLLMTokenCounter(ModelType.GPT_4O_MINI)
        
        mock_usage = Mock()
        mock_usage.prompt_tokens = 90
        mock_usage.completion_tokens = 60
        mock_usage.total_tokens = 150
        
        mock_response = Mock()
        mock_response.usage = mock_usage
        
        result = counter.extract_usage_from_response(mock_response)
        
        assert result == {
            'prompt_tokens': 90,
            'completion_tokens': 60,
            'total_tokens': 150,
        }


    def test_extract_usage_litellm_no_usage_data(self):
        """Test extracting usage when no usage data is available."""
        counter = LiteLLMTokenCounter(ModelType.GPT_4O_MINI)
        
        mock_response = Mock()
        mock_response.usage = None
        
        result = counter.extract_usage_from_response(mock_response)
        
        assert result is None

    def test_extract_usage_litellm_exception_handling(self):
        """Test that exceptions are handled gracefully."""
        counter = LiteLLMTokenCounter(ModelType.GPT_4O_MINI)
        mock_response = object()
        result = counter.extract_usage_from_response(mock_response)
        assert result is None

class TestMistralTokenCounterExtractUsage:
    """Test cases for Mistral token counter extract_usage_from_response method."""

    def test_extract_usage_from_mistral_response_object(self):
        """Test extracting usage from Mistral response object."""
        if not MISTRAL_AVAILABLE:
            pytest.skip("mistral_common module not available")
            
        counter = MistralTokenCounter(ModelType.MISTRAL_LARGE)
        mock_usage = Mock()
        mock_usage.prompt_tokens = 130
        mock_usage.completion_tokens = 70
        mock_response = Mock()
        mock_response.usage = mock_usage
        result = counter.extract_usage_from_response(mock_response)
        
        assert result == {
            'prompt_tokens': 130,
            'completion_tokens': 70,
            'total_tokens': 200,
        }

    def test_extract_usage_mistral_no_usage_data(self):
        """Test extracting usage when no usage data is available."""
        if not MISTRAL_AVAILABLE:
            pytest.skip("mistral_common module not available")
            
        counter = MistralTokenCounter(ModelType.MISTRAL_LARGE)
        mock_response = Mock()
        mock_response.usage = None
        result = counter.extract_usage_from_response(mock_response)
        assert result is None

    def test_extract_usage_mistral_exception_handling(self):
        """Test that exceptions are handled gracefully."""
        if not MISTRAL_AVAILABLE:
            pytest.skip("mistral_common module not available")
            
        counter = MistralTokenCounter(ModelType.MISTRAL_LARGE)
        mock_response = object()
        result = counter.extract_usage_from_response(mock_response)
        assert result is None
