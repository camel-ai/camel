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
def test_deepseek_config_thinking_parameter():
    """Test DeepSeekConfig accepts thinking parameter."""
    config = DeepSeekConfig(thinking={"type": "enabled"})
    assert config.as_dict()["thinking"] == {"type": "enabled"}


@pytest.mark.model_backend
def test_is_thinking_enabled():
    """Test _is_thinking_enabled for different configurations."""
    model_reasoner = DeepSeekModel(ModelType.DEEPSEEK_REASONER)
    assert model_reasoner._is_thinking_enabled() is True

    model_chat = DeepSeekModel(ModelType.DEEPSEEK_CHAT)
    assert model_chat._is_thinking_enabled() is False

    config = DeepSeekConfig(thinking={"type": "enabled"}).as_dict()
    model_chat_thinking = DeepSeekModel(ModelType.DEEPSEEK_CHAT, config)
    assert model_chat_thinking._is_thinking_enabled() is True


@pytest.mark.model_backend
def test_inject_and_store_reasoning_content():
    """Test reasoning_content injection and storage."""
    model = DeepSeekModel(ModelType.DEEPSEEK_REASONER)

    mock_tool_call = MagicMock()
    mock_tool_call.id = "tc_123"
    mock_message = MagicMock()
    mock_message.reasoning_content = "My reasoning..."
    mock_message.tool_calls = [mock_tool_call]
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=mock_message)]

    model._store_reasoning_content(mock_response)
    assert model._reasoning_content_map == {"tc_123": "My reasoning..."}

    messages = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "tc_123"}],
        },
        {"role": "tool", "tool_call_id": "tc_123", "content": "result"},
    ]
    result = model._inject_reasoning_content(messages)
    assert result[0]["reasoning_content"] == "My reasoning..."

    model._inject_reasoning_content([{"role": "user", "content": "new"}])
    assert model._reasoning_content_map == {}


@pytest.mark.model_backend
def test_prepare_request_thinking_in_extra_body():
    """Test thinking parameter is moved to extra_body."""
    config = DeepSeekConfig(thinking={"type": "enabled"}).as_dict()
    model = DeepSeekModel(ModelType.DEEPSEEK_CHAT, model_config_dict=config)

    request_config = model._prepare_request(
        [{"role": "user", "content": "Hi"}]
    )

    assert "thinking" not in request_config
    assert request_config["extra_body"]["thinking"] == {"type": "enabled"}
