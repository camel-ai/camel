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
"""
please set the below os environment:
export AZURE_OPENAI_BASE_URL=""

# if `AZURE_API_VERSION` is not set, the api_version parameter must be provided
export AZURE_API_VERSION=""
export AZURE_OPENAI_API_KEY=""
"""

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from camel.configs import ChatGPTConfig
from camel.models import AzureOpenAIModel, ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.utils import OpenAITokenCounter

AZURE_INIT_KWARGS = dict(
    api_version="2024-02-15-preview",
    api_key="test-key",
    url="https://test.openai.azure.com/",
)


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.GPT_3_5_TURBO,
        ModelType.GPT_4,
        ModelType.GPT_4_TURBO,
        ModelType.GPT_4O,
        ModelType.GPT_4O_MINI,
    ],
)
def test_openai_model(model_type):
    model_config_dict = ChatGPTConfig().as_dict()
    model = AzureOpenAIModel(
        model_type,
        model_config_dict,
        **AZURE_INIT_KWARGS,
    )
    assert model.model_type == model_type
    assert model.model_config_dict == model_config_dict
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.GPT_3_5_TURBO,
        ModelType.GPT_4,
        ModelType.GPT_4_TURBO,
        ModelType.GPT_4O,
        ModelType.GPT_4O_MINI,
    ],
)
def test_openai_model_create(model_type: ModelType):
    model = ModelFactory.create(
        model_platform=ModelPlatformType.AZURE,
        model_type=model_type,
        model_config_dict=ChatGPTConfig(temperature=0.8, n=3).as_dict(),
        api_version="2024-02-15-preview",
        api_key="test-key",
        url="https://test.openai.azure.com/",
    )
    assert model.model_type == model_type


def test_api_mode_default_is_chat_completions():
    model = AzureOpenAIModel(ModelType.GPT_4O, **AZURE_INIT_KWARGS)
    assert model._api_mode == "chat_completions"


def test_api_mode_responses_sets_mode():
    model = AzureOpenAIModel(
        ModelType.GPT_4O, **AZURE_INIT_KWARGS, api_mode="responses"
    )
    assert model._api_mode == "responses"
    assert model._responses_previous_response_id_by_session == {}
    assert model._responses_last_message_count_by_session == {}


def test_api_mode_invalid_raises():
    with pytest.raises(ValueError, match="api_mode must be"):
        AzureOpenAIModel(
            ModelType.GPT_4O, **AZURE_INIT_KWARGS, api_mode="invalid"
        )


def test_normalize_tools_for_responses_api():
    tools = [
        {
            "type": "function",
            "function": {"name": "get_weather", "parameters": {}},
        }
    ]
    result = AzureOpenAIModel._normalize_tools_for_responses_api(tools)
    assert result == [
        {"type": "function", "name": "get_weather", "parameters": {}}
    ]


def test_convert_messages_tool_call_history():
    messages = [
        {"role": "user", "content": "What is the weather?"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_abc",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"city": "London"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_abc",
            "content": "Sunny, 20C",
        },
    ]
    result = AzureOpenAIModel._convert_messages_to_responses_input(messages)
    assert result[0] == {"role": "user", "content": "What is the weather?"}
    assert result[1] == {
        "type": "function_call",
        "call_id": "call_abc",
        "name": "get_weather",
        "arguments": '{"city": "London"}',
    }
    assert result[2] == {
        "type": "function_call_output",
        "call_id": "call_abc",
        "output": "Sunny, 20C",
    }


def test_run_routes_to_responses_api():
    r"""Test that _run calls responses.create when api_mode='responses'."""
    model = AzureOpenAIModel(
        ModelType.GPT_4O, **AZURE_INIT_KWARGS, api_mode="responses"
    )

    fake_response = MagicMock()
    fake_response.id = "resp_123"
    fake_response.output = []
    fake_response.usage = None
    fake_response.created_at = 0

    model._client = MagicMock()
    model._client.responses.create.return_value = fake_response

    messages = [{"role": "user", "content": "Hello"}]
    model._run(messages)

    model._client.responses.create.assert_called_once()
    call_kwargs = model._client.responses.create.call_args.kwargs
    assert str(call_kwargs["model"]) == str(ModelType.GPT_4O)
    assert call_kwargs["stream"] is False


def test_run_chat_completions_mode_does_not_call_responses():
    r"""Test that _run does not call responses.create in default mode."""
    model = AzureOpenAIModel(ModelType.GPT_4O, **AZURE_INIT_KWARGS)

    fake_completion = MagicMock()
    model._client = MagicMock()
    model._client.chat.completions.create.return_value = fake_completion

    messages = [{"role": "user", "content": "Hello"}]
    model._run(messages)

    model._client.chat.completions.create.assert_called_once()
    model._client.responses.create.assert_not_called()


def test_responses_chain_state_saved_after_run():
    r"""Test that response ID is saved for chaining after a successful call."""
    model = AzureOpenAIModel(
        ModelType.GPT_4O, **AZURE_INIT_KWARGS, api_mode="responses"
    )

    fake_response = MagicMock()
    fake_response.id = "resp_chain_001"
    fake_response.output = []
    fake_response.usage = None
    fake_response.created_at = 0

    model._client = MagicMock()
    model._client.responses.create.return_value = fake_response

    messages = [{"role": "user", "content": "Hello"}]
    model._run(messages)

    assert (
        "resp_chain_001"
        in model._responses_previous_response_id_by_session.values()
    )


def test_prepare_responses_request_config_structured_output():
    r"""Test that a JSON schema is attached when response_format is given."""

    class MySchema(BaseModel):
        answer: str

    model = AzureOpenAIModel(
        ModelType.GPT_4O, **AZURE_INIT_KWARGS, api_mode="responses"
    )
    config = model._prepare_responses_request_config(
        response_format=MySchema, stream=False
    )
    assert "text" in config
    assert config["text"]["format"]["type"] == "json_schema"
    assert config["text"]["format"]["name"] == "MySchema"


def test_prepare_responses_request_config_n_warning():
    r"""Test that a warning is emitted when n > 1 in responses mode."""
    model = AzureOpenAIModel(
        ModelType.GPT_4O,
        model_config_dict=ChatGPTConfig(n=3).as_dict(),
        **AZURE_INIT_KWARGS,
        api_mode="responses",
    )
    with pytest.warns(UserWarning, match="does not support `n`"):
        config = model._prepare_responses_request_config()
    assert "n" not in config
