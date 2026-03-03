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

from camel.configs import (
    SambaCloudAPIConfig,
)
from camel.models import SambaModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        "llama3-70b",
    ],
)
def test_samba_model(model_type: ModelType):
    model = SambaModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == SambaCloudAPIConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)


def _mock_chat_completion_response() -> MagicMock:
    response = MagicMock()
    response.id = "test-id"
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Hello"
    response.usage = MagicMock()
    response.usage.prompt_tokens = 10
    response.usage.completion_tokens = 5
    response.usage.total_tokens = 15
    return response


def test_samba_model_run_passes_tools_to_cloud_api(monkeypatch):
    monkeypatch.setenv("SAMBA_API_KEY", "test_key")
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = (
        _mock_chat_completion_response()
    )

    model = SambaModel(
        model_type="llama3-70b",
        client=mock_client,
        async_client=MagicMock(),
    )

    tools = [
        {
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
    ]
    messages = [{"role": "user", "content": "what's the weather?"}]

    model.run(messages=messages, tools=tools)

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["tools"] == tools


def test_samba_model_run_keeps_tools_in_model_config_dict(monkeypatch):
    monkeypatch.setenv("SAMBA_API_KEY", "test_key")
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = (
        _mock_chat_completion_response()
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "echo",
                "description": "Echo the input",
                "parameters": {
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                },
            },
        }
    ]
    model_config_dict = SambaCloudAPIConfig().as_dict()
    model_config_dict["tools"] = tools

    model = SambaModel(
        model_type="llama3-70b",
        model_config_dict=model_config_dict,
        client=mock_client,
        async_client=MagicMock(),
    )
    messages = [{"role": "user", "content": "echo hello"}]

    model.run(messages=messages)

    assert model.model_config_dict["tools"] == tools
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["tools"] == tools
