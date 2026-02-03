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

from camel.configs import AnthropicConfig
from camel.models import AnthropicModel
from camel.models.anthropic_model import (
    strip_trailing_whitespace_from_messages,
)
from camel.types import ModelType
from camel.utils import AnthropicTokenCounter, BaseTokenCounter

# Skip all tests in this module if the anthropic package is not available.
pytest.importorskip("anthropic", reason="anthropic package is required")


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.CLAUDE_3_HAIKU,
        ModelType.CLAUDE_3_5_HAIKU,
        ModelType.CLAUDE_3_7_SONNET,
        ModelType.CLAUDE_SONNET_4_5,
        ModelType.CLAUDE_OPUS_4_5,
        ModelType.CLAUDE_SONNET_4,
        ModelType.CLAUDE_OPUS_4,
        ModelType.CLAUDE_OPUS_4_1,
    ],
)
def test_anthropic_model(model_type: ModelType):
    model = AnthropicModel(model_type, api_key="dummy_api_key")
    assert model.model_type == model_type
    assert model.model_config_dict == AnthropicConfig().as_dict()
    assert isinstance(model.token_counter, AnthropicTokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


def test_anthropic_model_uses_provided_token_counter():
    class DummyTokenCounter(BaseTokenCounter):
        def count_tokens_from_messages(self, messages):
            return 42

        def encode(self, text: str):
            return [1, 2, 3]

        def decode(self, token_ids):
            return "decoded"

    token_counter = DummyTokenCounter()
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        model_config_dict=AnthropicConfig().as_dict(),
        api_key="dummy_api_key",
        token_counter=token_counter,
    )

    assert model.token_counter is token_counter


def test_anthropic_model_cache_control_valid_and_invalid():
    # Valid cache_control values should configure _cache_control_config
    model_config = AnthropicConfig(cache_control="5m").as_dict()
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        model_config_dict=model_config,
        api_key="dummy_api_key",
    )
    assert model._cache_control_config == {
        "type": "ephemeral",
        "ttl": "5m",
    }

    # Invalid cache_control should raise ValueError
    with pytest.raises(ValueError):
        invalid_config = AnthropicConfig(cache_control="10m").as_dict()
        AnthropicModel(
            ModelType.CLAUDE_3_HAIKU,
            model_config_dict=invalid_config,
            api_key="dummy_api_key",
        )


def test_anthropic_model_cache_control_from_config():
    model_config = AnthropicConfig(cache_control="1h").as_dict()
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        model_config_dict=model_config,
        api_key="dummy_api_key",
    )
    assert model._cache_control_config == {
        "type": "ephemeral",
        "ttl": "1h",
    }


def test_anthropic_model_stream_property():
    model_stream = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        model_config_dict={"stream": True},
        api_key="dummy_api_key",
    )
    assert model_stream.stream is True

    model_non_stream = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        model_config_dict={"stream": False},
        api_key="dummy_api_key",
    )
    assert model_non_stream.stream is False


def test_strip_trailing_whitespace_empty_messages():
    """Test that empty message list returns empty list."""
    result = strip_trailing_whitespace_from_messages([])
    assert result == []


def test_strip_trailing_whitespace_string_content():
    """Test stripping whitespace from string content."""
    messages = [
        {"role": "user", "content": "Hello world   "},
        {"role": "assistant", "content": "Hi there\n\n"},
    ]
    result = strip_trailing_whitespace_from_messages(messages)

    assert result[0]["content"] == "Hello world"
    assert result[1]["content"] == "Hi there"
    # Original should not be modified
    assert messages[0]["content"] == "Hello world   "


def test_strip_trailing_whitespace_list_content_with_dict():
    """Test stripping whitespace from list content with dict parts."""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello   "},
                {
                    "type": "image_url",
                    "image_url": {"url": "http://example.com"},
                },
            ],
        }
    ]
    result = strip_trailing_whitespace_from_messages(messages)

    assert result[0]["content"][0]["text"] == "Hello"
    # Non-text parts should remain unchanged
    assert result[0]["content"][1]["type"] == "image_url"


def test_strip_trailing_whitespace_list_content_with_strings():
    """Test stripping whitespace from list content with string parts."""
    messages = [{"role": "user", "content": ["Hello   ", "World  \n"]}]
    result = strip_trailing_whitespace_from_messages(messages)

    assert result[0]["content"][0] == "Hello"
    assert result[0]["content"][1] == "World"


def test_strip_trailing_whitespace_none_content():
    """Test handling of None content."""
    messages = [{"role": "user", "content": None}]
    result = strip_trailing_whitespace_from_messages(messages)

    assert result[0]["content"] is None


def test_convert_openai_to_anthropic_system_message():
    """Test conversion of system message."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
    )
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
    ]

    system_msg, anthropic_msgs = model._convert_openai_to_anthropic_messages(
        messages
    )

    assert system_msg == "You are a helpful assistant."
    assert len(anthropic_msgs) == 1
    assert anthropic_msgs[0]["role"] == "user"
    assert anthropic_msgs[0]["content"] == "Hello"


def test_convert_openai_to_anthropic_system_message_list_content():
    """Test conversion of system message with list content."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
    )
    messages = [
        {
            "role": "system",
            "content": [
                {"type": "text", "text": "You are helpful."},
                "Be concise.",
            ],
        },
        {"role": "user", "content": "Hello"},
    ]

    system_msg, anthropic_msgs = model._convert_openai_to_anthropic_messages(
        messages
    )

    assert system_msg == "You are helpful.\nBe concise."


def test_convert_openai_to_anthropic_tool_calls():
    """Test conversion of assistant message with tool calls."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
    )
    messages = [
        {
            "role": "assistant",
            "content": "Let me search for that.",
            "tool_calls": [
                {
                    "id": "call_123",
                    "function": {
                        "name": "search",
                        "arguments": '{"query": "test"}',
                    },
                }
            ],
        }
    ]

    _, anthropic_msgs = model._convert_openai_to_anthropic_messages(messages)

    assert len(anthropic_msgs) == 1
    assert anthropic_msgs[0]["role"] == "assistant"
    content = anthropic_msgs[0]["content"]
    assert len(content) == 2
    assert content[0]["type"] == "text"
    assert content[0]["text"] == "Let me search for that."
    assert content[1]["type"] == "tool_use"
    assert content[1]["id"] == "call_123"
    assert content[1]["name"] == "search"
    assert content[1]["input"] == {"query": "test"}


def test_convert_openai_to_anthropic_tool_response():
    """Test conversion of tool response message."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
    )
    messages = [
        {
            "role": "tool",
            "tool_call_id": "call_123",
            "content": "Search results: found 5 items",
        }
    ]

    _, anthropic_msgs = model._convert_openai_to_anthropic_messages(messages)

    assert len(anthropic_msgs) == 1
    assert anthropic_msgs[0]["role"] == "user"
    content = anthropic_msgs[0]["content"]
    assert len(content) == 1
    assert content[0]["type"] == "tool_result"
    assert content[0]["tool_use_id"] == "call_123"
    assert content[0]["content"] == "Search results: found 5 items"


def test_convert_anthropic_response_text_only():
    """Test conversion of text-only response."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
    )

    # Create mock response
    mock_response = MagicMock()
    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = "Hello, how can I help?"
    mock_response.content = [mock_text_block]
    mock_response.stop_reason = "end_turn"
    mock_response.id = "msg_123"
    mock_response.usage = MagicMock()
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 5

    result = model._convert_anthropic_to_openai_response(
        mock_response, "claude-3-haiku"
    )

    assert result.choices[0].message.content == "Hello, how can I help?"
    assert result.choices[0].message.role == "assistant"
    assert result.choices[0].finish_reason == "stop"
    assert result.usage.prompt_tokens == 10
    assert result.usage.completion_tokens == 5
    assert result.usage.total_tokens == 15


def test_convert_anthropic_response_with_tool_use():
    """Test conversion of response with tool use."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
    )

    # Create mock response with tool use
    mock_response = MagicMock()
    mock_text_block = MagicMock()
    mock_text_block.type = "text"
    mock_text_block.text = "I'll search for that."

    mock_tool_block = MagicMock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.id = "tool_123"
    mock_tool_block.name = "search"
    mock_tool_block.input = {"query": "test"}

    mock_response.content = [mock_text_block, mock_tool_block]
    mock_response.stop_reason = "tool_use"
    mock_response.id = "msg_123"
    mock_response.usage = MagicMock()
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 5

    result = model._convert_anthropic_to_openai_response(
        mock_response, "claude-3-haiku"
    )

    assert result.choices[0].message.content == "I'll search for that."
    assert result.choices[0].finish_reason == "tool_calls"
    tool_calls = result.choices[0].message.tool_calls
    assert len(tool_calls) == 1
    assert tool_calls[0].id == "tool_123"
    assert tool_calls[0].type == "function"
    assert tool_calls[0].function.name == "search"


def test_convert_anthropic_response_stop_reasons():
    """Test conversion of different stop reasons."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
    )

    stop_reason_mapping = {
        "end_turn": "stop",
        "max_tokens": "length",
        "stop_sequence": "stop",
        "tool_use": "tool_calls",
    }

    for anthropic_reason, openai_reason in stop_reason_mapping.items():
        mock_response = MagicMock()
        mock_response.content = []
        mock_response.stop_reason = anthropic_reason
        mock_response.id = "msg_123"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 0
        mock_response.usage.output_tokens = 0

        result = model._convert_anthropic_to_openai_response(
            mock_response, "claude-3-haiku"
        )
        assert result.choices[0].finish_reason == openai_reason


def test_convert_tools_none():
    """Test conversion of None tools."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
    )

    result = model._convert_openai_tools_to_anthropic(None)
    assert result is None


def test_convert_tools_empty():
    """Test conversion of empty tools list."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
    )

    result = model._convert_openai_tools_to_anthropic([])
    assert result is None


def test_convert_tools_basic():
    """Test basic tool conversion."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
    )

    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                    },
                    "required": ["location"],
                },
            },
        }
    ]

    result = model._convert_openai_tools_to_anthropic(openai_tools)

    assert len(result) == 1
    assert result[0]["name"] == "get_weather"
    assert result[0]["description"] == "Get the weather for a location"
    assert result[0]["input_schema"]["type"] == "object"


def test_convert_tools_with_beta_structured_outputs():
    """Test tool conversion with beta structured outputs enabled."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
        use_beta_for_structured_outputs=True,
    )

    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {},
                "strict": False,
            },
        }
    ]

    result = model._convert_openai_tools_to_anthropic(openai_tools)

    assert result[0]["strict"] is False


def test_convert_stream_chunk_message_start():
    """Test conversion of message_start chunk."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
    )

    mock_chunk = MagicMock()
    mock_chunk.type = "message_start"
    mock_chunk.message = MagicMock()
    mock_chunk.message.id = "msg_123"

    tool_call_index = {}
    result = model._convert_anthropic_stream_to_openai_chunk(
        mock_chunk, "claude-3-haiku", tool_call_index
    )

    assert result.id == "msg_123"
    assert result.choices[0].delta.content is None
    assert result.choices[0].finish_reason is None


def test_convert_stream_chunk_content_block_delta_text():
    """Test conversion of text content_block_delta chunk."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
    )

    mock_chunk = MagicMock()
    mock_chunk.type = "content_block_delta"
    mock_chunk.delta = MagicMock()
    mock_chunk.delta.type = "text_delta"
    mock_chunk.delta.text = "Hello"

    tool_call_index = {}
    result = model._convert_anthropic_stream_to_openai_chunk(
        mock_chunk, "claude-3-haiku", tool_call_index
    )

    assert result.choices[0].delta.content == "Hello"


def test_convert_stream_chunk_tool_use_start():
    """Test conversion of tool_use content_block_start chunk."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
    )

    mock_chunk = MagicMock()
    mock_chunk.type = "content_block_start"
    mock_chunk.content_block = MagicMock()
    mock_chunk.content_block.type = "tool_use"
    mock_chunk.content_block.id = "tool_123"
    mock_chunk.content_block.name = "search"

    tool_call_index = {}
    result = model._convert_anthropic_stream_to_openai_chunk(
        mock_chunk, "claude-3-haiku", tool_call_index
    )

    assert result.choices[0].delta.tool_calls is not None
    tool_calls = result.choices[0].delta.tool_calls
    assert len(tool_calls) == 1
    assert tool_calls[0].id == "tool_123"
    assert tool_calls[0].function.name == "search"
    assert tool_calls[0].index == 0
    # Check that index was recorded
    assert tool_call_index["tool_123"] == 0


def test_convert_stream_chunk_tool_use_delta():
    """Test conversion of tool_use input_json_delta chunk."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
    )

    # Create mock with spec to avoid MagicMock auto-creating attributes
    mock_chunk = MagicMock()
    mock_chunk.type = "content_block_delta"
    mock_chunk.index = 0

    # Create delta mock without 'text' attribute
    mock_delta = MagicMock(spec=["type", "partial_json"])
    mock_delta.type = "input_json_delta"
    mock_delta.partial_json = '{"query":'
    mock_chunk.delta = mock_delta

    tool_call_index = {"tool_123": 0}
    result = model._convert_anthropic_stream_to_openai_chunk(
        mock_chunk, "claude-3-haiku", tool_call_index
    )

    assert result.choices[0].delta.tool_calls is not None
    tool_calls = result.choices[0].delta.tool_calls
    assert tool_calls[0].function.arguments == '{"query":'


def test_convert_stream_chunk_message_delta_stop():
    """Test conversion of message_delta chunk with stop reason."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
    )

    mock_chunk = MagicMock()
    mock_chunk.type = "message_delta"
    mock_chunk.delta = MagicMock()
    mock_chunk.delta.stop_reason = "end_turn"

    tool_call_index = {}
    result = model._convert_anthropic_stream_to_openai_chunk(
        mock_chunk, "claude-3-haiku", tool_call_index
    )

    assert result.choices[0].finish_reason == "stop"


def test_convert_stream_chunk_message_stop():
    """Test conversion of message_stop chunk."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
    )

    mock_chunk = MagicMock()
    mock_chunk.type = "message_stop"

    tool_call_index = {}
    result = model._convert_anthropic_stream_to_openai_chunk(
        mock_chunk, "claude-3-haiku", tool_call_index
    )

    assert result.choices[0].finish_reason == "stop"


def test_use_beta_for_structured_outputs():
    """Test that beta API is used when configured."""
    model = AnthropicModel(
        ModelType.CLAUDE_3_HAIKU,
        api_key="dummy_api_key",
        use_beta_for_structured_outputs=True,
    )

    assert model._use_beta_for_structured_outputs is True
