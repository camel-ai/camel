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

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from camel.configs import AnthropicConfig
from camel.models import AnthropicModel
from camel.models.anthropic_model import (
    strip_trailing_whitespace_from_messages,
)
from camel.types import ModelType
from camel.utils import AnthropicTokenCounter, BaseTokenCounter

# Skip all tests in this module if the anthropic package is not available.
pytest.importorskip("anthropic", reason="anthropic package is required")


class TravelResponse(BaseModel):
    city: str


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.CLAUDE_3_7_SONNET,
        ModelType.CLAUDE_SONNET_4_5,
        ModelType.CLAUDE_OPUS_4_5,
        ModelType.CLAUDE_OPUS_4_6,
        ModelType.CLAUDE_HAIKU_4_5,
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
        ModelType.CLAUDE_HAIKU_4_5,
        model_config_dict=AnthropicConfig().as_dict(),
        api_key="dummy_api_key",
        token_counter=token_counter,
    )

    assert model.token_counter is token_counter


def test_anthropic_model_cache_control_valid_and_invalid():
    # Valid cache_control values should configure _cache_control_config
    model_config = AnthropicConfig(cache_control="5m").as_dict()
    model = AnthropicModel(
        ModelType.CLAUDE_HAIKU_4_5,
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
            ModelType.CLAUDE_HAIKU_4_5,
            model_config_dict=invalid_config,
            api_key="dummy_api_key",
        )


def test_anthropic_model_cache_control_from_config():
    model_config = AnthropicConfig(cache_control="1h").as_dict()
    model = AnthropicModel(
        ModelType.CLAUDE_HAIKU_4_5,
        model_config_dict=model_config,
        api_key="dummy_api_key",
    )
    assert model._cache_control_config == {
        "type": "ephemeral",
        "ttl": "1h",
    }


def test_anthropic_model_stream_property():
    model_stream = AnthropicModel(
        ModelType.CLAUDE_HAIKU_4_5,
        model_config_dict={"stream": True},
        api_key="dummy_api_key",
    )
    assert model_stream.stream is True

    model_non_stream = AnthropicModel(
        ModelType.CLAUDE_HAIKU_4_5,
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
        ModelType.CLAUDE_HAIKU_4_5,
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
        ModelType.CLAUDE_HAIKU_4_5,
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
        ModelType.CLAUDE_HAIKU_4_5,
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
        ModelType.CLAUDE_HAIKU_4_5,
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
        ModelType.CLAUDE_HAIKU_4_5,
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
        mock_response, "claude-haiku-4-5"
    )

    assert result.choices[0].message.content == "Hello, how can I help?"
    assert result.choices[0].message.role == "assistant"
    assert result.choices[0].finish_reason == "stop"
    assert result.usage.prompt_tokens == 10
    assert result.usage.completion_tokens == 5
    assert result.usage.total_tokens == 15


def test_convert_anthropic_response_preserves_cache_usage_fields():
    """Test conversion preserves Anthropic prompt cache usage fields."""
    model = AnthropicModel(
        ModelType.CLAUDE_SONNET_4_5,
        api_key="dummy_api_key",
    )

    mock_response = MagicMock()
    mock_response.content = [{"type": "text", "text": "cached"}]
    mock_response.stop_reason = "end_turn"
    mock_response.id = "msg_cached"
    mock_response.usage = MagicMock()
    mock_response.usage.input_tokens = 20
    mock_response.usage.output_tokens = 6
    mock_response.usage.cache_read_input_tokens = 12
    mock_response.usage.cache_creation_input_tokens = 8
    mock_response.usage.cache_creation = {
        "ephemeral_5m_input_tokens": 5,
        "ephemeral_1h_input_tokens": 3,
    }

    result = model._convert_anthropic_to_openai_response(
        mock_response, "claude-haiku-4-5"
    )

    assert result.usage.prompt_tokens == 20
    assert result.usage.completion_tokens == 6
    assert result.usage.total_tokens == 26
    assert result.usage.cache_read_input_tokens == 12
    assert result.usage.cache_creation_input_tokens == 8
    assert result.usage.cache_creation == {
        "ephemeral_5m_input_tokens": 5,
        "ephemeral_1h_input_tokens": 3,
    }


def test_convert_anthropic_response_with_tool_use():
    """Test conversion of response with tool use."""
    model = AnthropicModel(
        ModelType.CLAUDE_HAIKU_4_5,
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
        mock_response, "claude-haiku-4-5"
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
        ModelType.CLAUDE_HAIKU_4_5,
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
            mock_response, "claude-haiku-4-5"
        )
        assert result.choices[0].finish_reason == openai_reason


def test_convert_tools_none():
    """Test conversion of None tools."""
    model = AnthropicModel(
        ModelType.CLAUDE_HAIKU_4_5,
        api_key="dummy_api_key",
    )

    result = model._convert_openai_tools_to_anthropic(None)
    assert result is None


def test_convert_tools_empty():
    """Test conversion of empty tools list."""
    model = AnthropicModel(
        ModelType.CLAUDE_HAIKU_4_5,
        api_key="dummy_api_key",
    )

    result = model._convert_openai_tools_to_anthropic([])
    assert result is None


def test_convert_tools_basic():
    """Test basic tool conversion."""
    model = AnthropicModel(
        ModelType.CLAUDE_HAIKU_4_5,
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


def test_convert_tools_preserves_strict_flag():
    """Test tool conversion preserves the strict field."""
    model = AnthropicModel(
        ModelType.CLAUDE_HAIKU_4_5,
        api_key="dummy_api_key",
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
        ModelType.CLAUDE_HAIKU_4_5,
        api_key="dummy_api_key",
    )

    mock_chunk = MagicMock()
    mock_chunk.type = "message_start"
    mock_chunk.message = MagicMock()
    mock_chunk.message.id = "msg_123"

    tool_call_index = {}
    result = model._convert_anthropic_stream_to_openai_chunk(
        mock_chunk, "claude-haiku-4-5", tool_call_index
    )

    assert result.id == "msg_123"
    assert result.choices[0].delta.content is None
    assert result.choices[0].finish_reason is None


def test_convert_stream_chunk_message_start_preserves_cache_usage():
    """Test message_start chunk conversion preserves prompt cache usage."""
    model = AnthropicModel(
        ModelType.CLAUDE_SONNET_4_5,
        api_key="dummy_api_key",
    )

    mock_chunk = MagicMock()
    mock_chunk.type = "message_start"
    mock_chunk.message = MagicMock()
    mock_chunk.message.id = "msg_cached"
    mock_chunk.message.usage = MagicMock()
    mock_chunk.message.usage.input_tokens = 30
    mock_chunk.message.usage.output_tokens = 0
    mock_chunk.message.usage.cache_read_input_tokens = 18

    tool_call_index = {}
    result = model._convert_anthropic_stream_to_openai_chunk(
        mock_chunk, "claude-haiku-4-5", tool_call_index
    )

    assert result.usage.prompt_tokens == 30
    assert result.usage.completion_tokens == 0
    assert result.usage.total_tokens == 30
    assert result.usage.cache_read_input_tokens == 18


def test_convert_stream_chunk_content_block_delta_text():
    """Test conversion of text content_block_delta chunk."""
    model = AnthropicModel(
        ModelType.CLAUDE_HAIKU_4_5,
        api_key="dummy_api_key",
    )

    mock_chunk = MagicMock()
    mock_chunk.type = "content_block_delta"
    mock_chunk.delta = MagicMock()
    mock_chunk.delta.type = "text_delta"
    mock_chunk.delta.text = "Hello"

    tool_call_index = {}
    result = model._convert_anthropic_stream_to_openai_chunk(
        mock_chunk, "claude-haiku-4-5", tool_call_index
    )

    assert result.choices[0].delta.content == "Hello"


def test_convert_stream_chunk_tool_use_start():
    """Test conversion of tool_use content_block_start chunk."""
    model = AnthropicModel(
        ModelType.CLAUDE_HAIKU_4_5,
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
        mock_chunk, "claude-haiku-4-5", tool_call_index
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
        ModelType.CLAUDE_HAIKU_4_5,
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
        mock_chunk, "claude-haiku-4-5", tool_call_index
    )

    assert result.choices[0].delta.tool_calls is not None
    tool_calls = result.choices[0].delta.tool_calls
    assert tool_calls[0].function.arguments == '{"query":'


def test_convert_stream_chunk_message_delta_stop():
    """Test conversion of message_delta chunk with stop reason."""
    model = AnthropicModel(
        ModelType.CLAUDE_HAIKU_4_5,
        api_key="dummy_api_key",
    )

    mock_chunk = MagicMock()
    mock_chunk.type = "message_delta"
    mock_chunk.delta = MagicMock()
    mock_chunk.delta.stop_reason = "end_turn"

    tool_call_index = {}
    result = model._convert_anthropic_stream_to_openai_chunk(
        mock_chunk, "claude-haiku-4-5", tool_call_index
    )

    assert result.choices[0].finish_reason == "stop"


def test_convert_stream_chunk_message_stop():
    """Test conversion of message_stop chunk."""
    model = AnthropicModel(
        ModelType.CLAUDE_HAIKU_4_5,
        api_key="dummy_api_key",
    )

    mock_chunk = MagicMock()
    mock_chunk.type = "message_stop"

    tool_call_index = {}
    result = model._convert_anthropic_stream_to_openai_chunk(
        mock_chunk, "claude-haiku-4-5", tool_call_index
    )

    assert result.choices[0].finish_reason == "stop"


def test_build_output_config():
    """Test output_config generation for structured outputs."""
    model = AnthropicModel(
        ModelType.CLAUDE_HAIKU_4_5,
        api_key="dummy_api_key",
    )

    output_config = model._build_output_config(TravelResponse)

    assert output_config["format"]["type"] == "json_schema"
    schema = output_config["format"]["schema"]
    assert schema["type"] == "object"
    assert "city" in schema["properties"]


def test_run_passes_output_config_tool_choice_and_extra_fields():
    """Test Anthropic request payload for structured outputs with tools."""
    mock_client = MagicMock()
    mock_async_client = MagicMock()

    mock_response = MagicMock()
    mock_response.content = [{"type": "text", "text": '{"city":"Kyoto"}'}]
    mock_response.stop_reason = "end_turn"
    mock_response.id = "msg_structured"
    mock_response.usage = MagicMock()
    mock_response.usage.input_tokens = 12
    mock_response.usage.output_tokens = 4
    mock_client.messages.create.return_value = mock_response

    config = AnthropicConfig(
        max_tokens=128,
        tool_choice={"type": "auto"},
        extra_headers={"x-test-header": "1"},
        extra_body={
            "existing": True,
            "output_config": {"format": {"type": "json_schema", "schema": {}}},
        },
    ).as_dict()

    model = AnthropicModel(
        ModelType.CLAUDE_HAIKU_4_5,
        model_config_dict=config,
        api_key="dummy_api_key",
        client=mock_client,
        async_client=mock_async_client,
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                    },
                    "required": ["location"],
                },
                "strict": True,
            },
        }
    ]

    result = model._run(
        messages=[{"role": "user", "content": "Plan a trip"}],
        response_format=TravelResponse,
        tools=tools,
    )

    request_kwargs = mock_client.messages.create.call_args.kwargs

    assert request_kwargs["tool_choice"] == {"type": "auto"}
    assert request_kwargs["extra_headers"] == {"x-test-header": "1"}
    assert request_kwargs["extra_body"]["existing"] is True
    assert "output_config" not in request_kwargs["extra_body"]
    assert request_kwargs["output_config"]["format"]["type"] == "json_schema"
    assert request_kwargs["tools"][0]["strict"] is True
    assert result.choices[0].message.content == '{"city":"Kyoto"}'


@pytest.mark.asyncio
async def test_arun_passes_output_config_tool_choice_and_extra_fields():
    """Test async Anthropic request payload for structured outputs."""
    mock_client = MagicMock()
    mock_async_client = MagicMock()

    mock_response = MagicMock()
    mock_response.content = [{"type": "text", "text": '{"city":"Kyoto"}'}]
    mock_response.stop_reason = "end_turn"
    mock_response.id = "msg_structured_async"
    mock_response.usage = MagicMock()
    mock_response.usage.input_tokens = 7
    mock_response.usage.output_tokens = 3
    mock_async_client.messages.create = AsyncMock(return_value=mock_response)

    config = AnthropicConfig(
        max_tokens=128,
        tool_choice={"type": "auto"},
        extra_headers={"x-test-header": "1"},
        extra_body={"existing": True},
    ).as_dict()

    model = AnthropicModel(
        ModelType.CLAUDE_HAIKU_4_5,
        model_config_dict=config,
        api_key="dummy_api_key",
        client=mock_client,
        async_client=mock_async_client,
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "minLength": 3,
                        },
                    },
                    "required": ["location"],
                },
                "strict": True,
            },
        }
    ]

    await model._arun(
        messages=[{"role": "user", "content": "Plan a trip"}],
        response_format=TravelResponse,
        tools=tools,
    )

    request_kwargs = mock_async_client.messages.create.call_args.kwargs

    assert request_kwargs["tool_choice"] == {"type": "auto"}
    assert request_kwargs["extra_headers"] == {"x-test-header": "1"}
    assert request_kwargs["extra_body"]["existing"] is True
    assert request_kwargs["output_config"]["format"]["type"] == "json_schema"
    output_schema = request_kwargs["output_config"]["format"]["schema"]
    assert output_schema["additionalProperties"] is False
    assert "city" in output_schema["properties"]
    assert (
        request_kwargs["tools"][0]["input_schema"]["properties"]["location"][
            "description"
        ]
        == "{minLength: 3}"
    )
