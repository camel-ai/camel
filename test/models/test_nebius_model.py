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
from httpx import URL

from camel.configs import NebiusConfig
from camel.models import NebiusModel
from camel.types import ModelType


@pytest.mark.model_backend
class TestNebiusModel:
    @pytest.mark.parametrize(
        "model_type",
        [
            ModelType.NEBIUS_GPT_OSS_120B,
            ModelType.NEBIUS_GPT_OSS_20B,
            ModelType.NEBIUS_GLM_4_5,
        ],
    )
    def test_nebius_model_create(self, model_type: ModelType):
        model = NebiusModel(model_type)
        assert model.model_type == model_type

    def test_nebius_model_create_with_config(self):
        config_dict = NebiusConfig(
            temperature=0.5,
            top_p=1.0,
            max_tokens=100,
        ).as_dict()

        model = NebiusModel(
            model_type=ModelType.NEBIUS_GPT_OSS_120B,
            model_config_dict=config_dict,
        )

        assert model.model_type == ModelType.NEBIUS_GPT_OSS_120B
        assert model.model_config_dict == config_dict

    def test_nebius_model_api_keys_required(self):
        # Test that the api_keys_required decorator is applied
        assert hasattr(NebiusModel.__init__, "__wrapped__")

    def test_nebius_model_default_url(self, monkeypatch):
        # Test default URL when no environment variable is set
        monkeypatch.delenv("NEBIUS_API_BASE_URL", raising=False)
        monkeypatch.setenv("NEBIUS_API_KEY", "test_key")

        model = NebiusModel(ModelType.NEBIUS_GPT_OSS_120B)
        assert model._url == URL("https://api.tokenfactory.nebius.com/v1")

    def test_nebius_model_custom_url(self, monkeypatch):
        # Test custom URL from environment variable
        custom_url = "https://custom.nebius.endpoint/v1"
        monkeypatch.setenv("NEBIUS_API_BASE_URL", custom_url)
        monkeypatch.setenv("NEBIUS_API_KEY", "test_key")

        model = NebiusModel(ModelType.NEBIUS_GPT_OSS_120B)
        assert model._url == custom_url

    def test_nebius_model_extends_openai_compatible(self):
        # Test that NebiusModel inherits from OpenAICompatibleModel
        from camel.models.openai_compatible_model import OpenAICompatibleModel

        model = NebiusModel(ModelType.NEBIUS_GPT_OSS_120B)
        assert isinstance(model, OpenAICompatibleModel)

    def test_nebius_model_token_counter(self):
        model = NebiusModel(ModelType.NEBIUS_GPT_OSS_120B)
        # Should use the default OpenAI token counter
        assert model.token_counter is not None
        assert hasattr(model.token_counter, "count_tokens_from_messages")


class TestNebiusModelRequests:
    @pytest.mark.parametrize("stream", [False, True])
    def test_nebius_chat_completion_request(self, stream: bool):
        client = MagicMock()
        async_client = MagicMock()
        expected_response = MagicMock()
        client.chat.completions.create.return_value = expected_response
        model = NebiusModel(
            model_type=ModelType.NEBIUS_GPT_OSS_120B,
            model_config_dict=NebiusConfig(stream=stream).as_dict(),
            api_key="test-key",
            client=client,
            async_client=async_client,
        )
        messages = [{"role": "user", "content": "Hello"}]

        result = model._run(messages)

        client.chat.completions.create.assert_called_once_with(
            messages=messages,
            model="openai/gpt-oss-120b",
            stream=stream,
        )
        assert result is expected_response

    def test_nebius_tool_request(self):
        client = MagicMock()
        async_client = MagicMock()
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the weather",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    },
                },
            }
        ]
        model = NebiusModel(
            model_type=ModelType.NEBIUS_GPT_OSS_120B,
            model_config_dict=NebiusConfig(tool_choice="auto").as_dict(),
            api_key="test-key",
            client=client,
            async_client=async_client,
        )
        messages = [{"role": "user", "content": "Weather in Paris?"}]

        model._run(messages, tools=tools)

        client.chat.completions.create.assert_called_once_with(
            messages=messages,
            model="openai/gpt-oss-120b",
            tool_choice="auto",
            tools=tools,
        )


@pytest.mark.model_backend
class TestNebiusModelTypes:
    @pytest.mark.parametrize(
        "model_type",
        [
            ModelType.NEBIUS_GPT_OSS_120B,
            ModelType.NEBIUS_GPT_OSS_20B,
            ModelType.NEBIUS_GLM_4_5,
            ModelType.NEBIUS_DEEPSEEK_V3,
            ModelType.NEBIUS_DEEPSEEK_R1,
            ModelType.NEBIUS_LLAMA_3_1_70B,
            ModelType.NEBIUS_MISTRAL_7B_INSTRUCT,
        ],
    )
    def test_nebius_model_types_available(self, model_type: ModelType):
        # Test that all defined Nebius model types are recognized
        assert model_type.is_nebius
        model = NebiusModel(model_type)
        assert isinstance(model.model_type, ModelType)
