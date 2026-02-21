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

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from camel.configs import ChatGPTConfig
from camel.models import OpenAIModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.GPT_3_5_TURBO,
        ModelType.GPT_4,
        ModelType.GPT_4_TURBO,
        ModelType.GPT_4O,
        ModelType.GPT_4O_MINI,
        ModelType.O1,
        ModelType.O1_PREVIEW,
        ModelType.O1_MINI,
        ModelType.GPT_4_5_PREVIEW,
        ModelType.GPT_5,
        ModelType.O3,
        ModelType.O3_PRO,
        ModelType.O3_MINI,
        ModelType.O4_MINI,
        ModelType.GPT_4_1,
        ModelType.GPT_4_1_MINI,
        ModelType.GPT_4_1_NANO,
    ],
)
def test_openai_model(model_type: ModelType):
    model = OpenAIModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == ChatGPTConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


def test_prompt_cache_key_passed_to_api():
    """Test that prompt_cache_key is passed to the OpenAI API when set."""
    with patch("camel.models.openai_model.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Create mock response
        mock_response = MagicMock()
        mock_response.id = "test-id"
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client.chat.completions.create.return_value = mock_response

        # Test with explicit prompt_cache_key
        config = ChatGPTConfig(prompt_cache_key="my-cache-key").as_dict()
        model = OpenAIModel(
            model_type=ModelType.GPT_4O_MINI,
            model_config_dict=config,
        )
        messages = [{"role": "user", "content": "Hello"}]
        model.run(messages)

        # Verify that prompt_cache_key was passed to the API
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "prompt_cache_key" in call_kwargs
        assert call_kwargs["prompt_cache_key"] == "my-cache-key"


def test_prompt_cache_key_not_passed_when_none():
    """Test that prompt_cache_key is not passed when not set (default None)."""
    with patch("camel.models.openai_model.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Create mock response
        mock_response = MagicMock()
        mock_response.id = "test-id"
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_client.chat.completions.create.return_value = mock_response

        # Test with default config (no prompt_cache_key)
        model = OpenAIModel(model_type=ModelType.GPT_4O_MINI)
        messages = [{"role": "user", "content": "Hello"}]
        model.run(messages)

        # Verify that prompt_cache_key is NOT in the call kwargs
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "prompt_cache_key" not in call_kwargs


def test_openai_model_invalid_api_mode():
    with pytest.raises(ValueError, match="api_mode must be"):
        OpenAIModel(
            model_type=ModelType.GPT_4O_MINI,
            api_mode="invalid_mode",
        )


def test_responses_mode_non_stream_response_mapping():
    with patch("camel.models.openai_model.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        responses_payload = {
            "id": "resp_1",
            "created_at": 1741294021,
            "usage": {
                "input_tokens": 10,
                "output_tokens": 6,
                "total_tokens": 16,
            },
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Hello from responses",
                        }
                    ],
                }
            ],
        }
        mock_client.responses.create.return_value = responses_payload

        model = OpenAIModel(
            model_type=ModelType.GPT_4O_MINI,
            api_mode="responses",
        )
        messages = [{"role": "user", "content": "Hello"}]
        response = model.run(messages)

        assert response.choices[0].message.content == "Hello from responses"
        assert response.choices[0].finish_reason == "stop"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 6
        assert response.usage.total_tokens == 16
        assert mock_client.responses.create.called


def test_responses_mode_stream_mapping():
    with patch("camel.models.openai_model.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        stream_events = [
            {
                "type": "response.created",
                "response": {"id": "resp_stream"},
            },
            {
                "type": "response.output_text.delta",
                "item_id": "msg_1",
                "delta": "Hi",
            },
            {
                "type": "response.output_text.delta",
                "item_id": "msg_1",
                "delta": "!",
            },
            {
                "type": "response.completed",
                "response": {
                    "id": "resp_stream",
                    "usage": {
                        "input_tokens": 3,
                        "output_tokens": 2,
                        "total_tokens": 5,
                    },
                },
            },
        ]

        mock_client.responses.create.return_value = stream_events

        model = OpenAIModel(
            model_type=ModelType.GPT_4O_MINI,
            model_config_dict={"stream": True},
            api_mode="responses",
        )
        messages = [{"role": "user", "content": "Hello"}]
        chunks = list(model.run(messages))

        assert len(chunks) >= 3
        assert chunks[0].choices[0].delta.content == "Hi"
        assert chunks[1].choices[0].delta.content == "!"
        assert chunks[-1].choices[0].finish_reason == "stop"
        assert chunks[-1].usage.total_tokens == 5


def test_responses_stream_tool_call_arguments_not_duplicated():
    with patch("camel.models.openai_model.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        stream_events = [
            {
                "type": "response.created",
                "response": {"id": "resp_stream"},
            },
            {
                "type": "response.output_item.added",
                "output_index": 0,
                "item": {
                    "type": "function_call",
                    "id": "fc_1",
                    "call_id": "call_1",
                    "name": "get_weather",
                    "arguments": '{"city":"Beijing"}',
                },
            },
            {
                "type": "response.function_call_arguments.delta",
                "output_index": 0,
                "item_id": "fc_1",
                "delta": '{"city":"Beijing"}',
            },
            {
                "type": "response.output_item.done",
                "output_index": 0,
                "item": {
                    "type": "function_call",
                    "id": "fc_1",
                    "call_id": "call_1",
                    "name": "get_weather",
                    "arguments": '{"city":"Beijing"}',
                },
            },
            {
                "type": "response.completed",
                "response": {
                    "id": "resp_stream",
                    "usage": {
                        "input_tokens": 3,
                        "output_tokens": 2,
                        "total_tokens": 5,
                    },
                },
            },
        ]
        mock_client.responses.create.return_value = stream_events

        model = OpenAIModel(
            model_type=ModelType.GPT_4O_MINI,
            model_config_dict={"stream": True},
            api_mode="responses",
        )
        chunks = list(model.run([{"role": "user", "content": "weather?"}]))

        arg_fragments = []
        for chunk in chunks:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if not delta or not getattr(delta, "tool_calls", None):
                continue
            for tc in delta.tool_calls:
                if tc.function and tc.function.arguments:
                    arg_fragments.append(tc.function.arguments)

        assert "".join(arg_fragments) == '{"city":"Beijing"}'
        assert chunks[-1].choices[0].finish_reason == "tool_calls"


def test_responses_mode_uses_previous_response_id_and_delta_input():
    with patch("camel.models.openai_model.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        first_response = {
            "id": "resp_first",
            "created_at": 1741294021,
            "usage": {
                "input_tokens": 10,
                "output_tokens": 6,
                "total_tokens": 16,
            },
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "First turn"}],
                }
            ],
        }
        second_response = {
            "id": "resp_second",
            "created_at": 1741294022,
            "usage": {
                "input_tokens": 11,
                "output_tokens": 5,
                "total_tokens": 16,
            },
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": "Second turn"}
                    ],
                }
            ],
        }
        mock_client.responses.create.side_effect = [
            first_response,
            second_response,
        ]

        model = OpenAIModel(
            model_type=ModelType.GPT_4O_MINI,
            api_mode="responses",
        )

        # First call sends full context
        model.run(
            [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello"},
            ]
        )
        first_call_kwargs = mock_client.responses.create.call_args_list[
            0
        ].kwargs
        assert "previous_response_id" not in first_call_kwargs
        assert len(first_call_kwargs["input"]) == 2

        # Second call sends delta context + previous_response_id
        model.run(
            [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "First turn"},
                {"role": "user", "content": "Continue"},
            ]
        )
        second_call_kwargs = mock_client.responses.create.call_args_list[
            1
        ].kwargs
        assert second_call_kwargs["previous_response_id"] == "resp_first"
        assert len(second_call_kwargs["input"]) == 2
        assert second_call_kwargs["input"][-1]["content"] == "Continue"


def test_responses_mode_normalizes_function_tools_schema():
    with patch("camel.models.openai_model.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_client.responses.create.return_value = {
            "id": "resp_1",
            "created_at": 1741294021,
            "usage": {
                "input_tokens": 1,
                "output_tokens": 1,
                "total_tokens": 2,
            },
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "ok"}],
                }
            ],
        }

        chat_style_tool = {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather by city",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
        }

        model = OpenAIModel(
            model_type=ModelType.GPT_4O_MINI,
            api_mode="responses",
            model_config_dict={"tools": [chat_style_tool]},
        )
        model.run([{"role": "user", "content": "weather?"}])

        call_kwargs = mock_client.responses.create.call_args.kwargs
        assert "tools" in call_kwargs
        assert call_kwargs["tools"][0]["type"] == "function"
        assert call_kwargs["tools"][0]["name"] == "get_weather"
        assert "function" not in call_kwargs["tools"][0]


def test_responses_mode_structured_output_enforces_additional_properties():
    class Destination(BaseModel):
        city: str

    class TravelAdvice(BaseModel):
        destination: Destination
        clothing: str

    with patch("camel.models.openai_model.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_client.responses.create.return_value = {
            "id": "resp_1",
            "created_at": 1741294021,
            "usage": {
                "input_tokens": 1,
                "output_tokens": 1,
                "total_tokens": 2,
            },
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"destination":{"city":"NYC"},'
                            '"clothing":"coat"}',
                        }
                    ],
                }
            ],
        }

        model = OpenAIModel(
            model_type=ModelType.GPT_4O_MINI,
            api_mode="responses",
        )
        model.run(
            [{"role": "user", "content": "travel advice"}],
            response_format=TravelAdvice,
        )

        schema = mock_client.responses.create.call_args.kwargs["text"][
            "format"
        ]["schema"]
        assert schema["additionalProperties"] is False
        assert schema["$defs"]["Destination"]["additionalProperties"] is False


def test_responses_mode_converts_tool_call_history_to_input_items():
    with patch("camel.models.openai_model.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_client.responses.create.return_value = {
            "id": "resp_1",
            "created_at": 1741294021,
            "usage": {
                "input_tokens": 1,
                "output_tokens": 1,
                "total_tokens": 2,
            },
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "ok"}],
                }
            ],
        }

        model = OpenAIModel(
            model_type=ModelType.GPT_4O_MINI,
            api_mode="responses",
        )
        model.run(
            [
                {"role": "user", "content": "How is weather?"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city":"Beijing"}',
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_1",
                    "content": "sunny, 28C",
                },
            ]
        )

        input_items = mock_client.responses.create.call_args.kwargs["input"]
        assert input_items[1]["type"] == "function_call"
        assert input_items[1]["call_id"] == "call_1"
        assert input_items[1]["name"] == "get_weather"
        assert input_items[2]["type"] == "function_call_output"
        assert input_items[2]["call_id"] == "call_1"
        assert "tool_calls" not in input_items[1]
