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


import pytest

from camel.configs import DeepSeekConfig
from camel.models import DeepSeekModel, ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.DEEPSEEK_CHAT,
        ModelType.DEEPSEEK_REASONER,
    ],
)
def test_deepseek_model(model_type):
    model_config_dict = DeepSeekConfig().as_dict()
    model = DeepSeekModel(model_type, model_config_dict)
    assert model.model_type == model_type
    assert model.model_config_dict == model_config_dict
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.DEEPSEEK_CHAT,
        ModelType.DEEPSEEK_REASONER,
    ],
)
def test_deepseek_model_create(model_type: ModelType):
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEEPSEEK,
        model_type=model_type,
        model_config_dict=DeepSeekConfig(temperature=1.3).as_dict(),
    )
    assert model.model_type == model_type


@pytest.mark.model_backend
def test_deepseek_reasoner_prepare_request_filters_params():
    r"""Test that reasoner model filters unsupported parameters."""
    model_config_dict = DeepSeekConfig(temperature=0.5, top_p=0.9).as_dict()
    model = DeepSeekModel(ModelType.DEEPSEEK_REASONER, model_config_dict)
    messages = [{"role": "user", "content": "Hello"}]
    request_config = model._prepare_request(messages)
    assert "temperature" not in request_config
    assert "top_p" not in request_config


@pytest.mark.model_backend
def test_deepseek_reasoner_allows_tools():
    r"""Test that reasoner model supports tool calls (V3.2+)."""
    model_config_dict = DeepSeekConfig().as_dict()
    model = DeepSeekModel(ModelType.DEEPSEEK_REASONER, model_config_dict)
    messages = [{"role": "user", "content": "Hello"}]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the weather",
                "parameters": {"type": "object", "properties": {}},
                "strict": True,
            },
        }
    ]
    request_config = model._prepare_request(messages, tools=tools)
    assert "tools" in request_config
    # Verify strict is removed from function parameters
    assert "strict" not in request_config["tools"][0]["function"]


@pytest.mark.model_backend
def test_deepseek_chat_prepare_request_keeps_params():
    r"""Test that chat model keeps all parameters."""
    model_config_dict = DeepSeekConfig(temperature=0.5, top_p=0.9).as_dict()
    model = DeepSeekModel(ModelType.DEEPSEEK_CHAT, model_config_dict)
    messages = [{"role": "user", "content": "Hello"}]
    request_config = model._prepare_request(messages)
    assert request_config.get("temperature") == 0.5
    assert request_config.get("top_p") == 0.9


@pytest.mark.model_backend
def test_deepseek_reasoning_content_injection():
    r"""Test reasoning_content injection for tool call continuations."""
    model_config_dict = DeepSeekConfig().as_dict()
    model = DeepSeekModel(ModelType.DEEPSEEK_REASONER, model_config_dict)

    # Simulate stored reasoning_content from a previous response
    model._last_reasoning_content = "Let me think about this..."

    messages = [
        {"role": "user", "content": "What's the weather?"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"city": "Beijing"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "content": "Sunny, 25°C",
            "tool_call_id": "call_1",
        },
    ]

    processed = model._inject_reasoning_content(messages)

    # reasoning_content should be injected into the assistant message
    assert processed[1]["reasoning_content"] == "Let me think about this..."
    # Should be cleared after injection
    assert model._last_reasoning_content is None


@pytest.mark.model_backend
def test_deepseek_no_injection_without_reasoning_content():
    r"""Test that no injection happens when there's no reasoning_content."""
    model_config_dict = DeepSeekConfig().as_dict()
    model = DeepSeekModel(ModelType.DEEPSEEK_REASONER, model_config_dict)

    messages = [{"role": "user", "content": "Hello"}]
    processed = model._inject_reasoning_content(messages)
    assert processed == messages
