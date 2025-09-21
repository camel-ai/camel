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

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from camel.configs import CometAPIConfig
from camel.models import CometAPIModel
from camel.types import ChatCompletion, ModelType


@pytest.mark.model_backend
class TestCometAPIModel:
    @pytest.mark.parametrize(
        "model_type",
        [
            ModelType.COMETAPI_GPT_5_CHAT_LATEST,
            ModelType.COMETAPI_CLAUDE_OPUS_4_1_20250805,
            ModelType.COMETAPI_GEMINI_2_5_PRO,
            ModelType.COMETAPI_GROK_4_0709,
            ModelType.COMETAPI_DEEPSEEK_V3_1,
            ModelType.COMETAPI_QWEN3_30B_A3B,
            ModelType.COMETAPI_GPT_5,
            ModelType.COMETAPI_CLAUDE_3_7_SONNET_LATEST,
            ModelType.COMETAPI_GEMINI_2_5_FLASH,
            ModelType.COMETAPI_GROK_3,
        ],
    )
    def test_cometapi_model_create(self, model_type: ModelType):
        with patch.dict(os.environ, {"COMETAPI_KEY": "test_key"}):
            model = CometAPIModel(model_type)
            assert model.model_type == model_type

    def test_cometapi_model_create_with_config(self):
        config_dict = CometAPIConfig(
            temperature=0.5,
            top_p=1.0,
            max_tokens=100,
            stream=False,
        ).as_dict()

        with patch.dict(os.environ, {"COMETAPI_KEY": "test_key"}):
            model = CometAPIModel(
                model_type=ModelType.COMETAPI_GPT_5_CHAT_LATEST,
                model_config_dict=config_dict,
            )

            assert model.model_type == ModelType.COMETAPI_GPT_5_CHAT_LATEST
            assert model.model_config_dict == config_dict

    def test_cometapi_model_api_keys_required(self):
        # Test that the api_keys_required decorator is applied
        assert hasattr(CometAPIModel.__init__, "__wrapped__")

    def test_cometapi_model_default_url(self, monkeypatch):
        # Test default URL when no environment variable is set
        monkeypatch.delenv("COMETAPI_API_BASE_URL", raising=False)
        monkeypatch.setenv("COMETAPI_KEY", "test_key")

        model = CometAPIModel(ModelType.COMETAPI_GPT_5_CHAT_LATEST)
        assert model._url == "https://api.cometapi.com/v1"

    def test_cometapi_model_custom_url(self, monkeypatch):
        # Test custom URL from environment variable
        custom_url = "https://custom.cometapi.endpoint/v1"
        monkeypatch.setenv("COMETAPI_API_BASE_URL", custom_url)
        monkeypatch.setenv("COMETAPI_KEY", "test_key")

        model = CometAPIModel(ModelType.COMETAPI_GPT_5_CHAT_LATEST)
        assert model._url == custom_url

    def test_cometapi_model_extends_openai_compatible(self):
        # Test that CometAPIModel inherits from OpenAICompatibleModel
        from camel.models.openai_compatible_model import OpenAICompatibleModel

        with patch.dict(os.environ, {"COMETAPI_KEY": "test_key"}):
            model = CometAPIModel(ModelType.COMETAPI_GPT_5_CHAT_LATEST)
            assert isinstance(model, OpenAICompatibleModel)

    def test_cometapi_model_token_counter(self):
        with patch.dict(os.environ, {"COMETAPI_KEY": "test_key"}):
            model = CometAPIModel(ModelType.COMETAPI_GPT_5_CHAT_LATEST)
            # Should use the default OpenAI token counter
            assert model.token_counter is not None
            assert hasattr(model.token_counter, "count_tokens_from_messages")

    @pytest.mark.parametrize(
        "model_type",
        [
            ModelType.COMETAPI_GPT_5_CHAT_LATEST,
            ModelType.COMETAPI_CLAUDE_OPUS_4_1_20250805,
            ModelType.COMETAPI_GEMINI_2_5_PRO,
            ModelType.COMETAPI_GROK_4_0709,
            ModelType.COMETAPI_DEEPSEEK_V3_1,
            ModelType.COMETAPI_QWEN3_30B_A3B,
        ],
    )
    def test_cometapi_model_types_available(self, model_type: ModelType):
        # Test that all defined CometAPI model types are recognized
        assert model_type.is_cometapi
        with patch.dict(os.environ, {"COMETAPI_KEY": "test_key"}):
            model = CometAPIModel(model_type)
            assert isinstance(model.model_type, ModelType)

    def test_cometapi_model_token_limits(self):
        # Test that CometAPI models have proper token limits
        test_cases = [
            (ModelType.COMETAPI_GPT_5_CHAT_LATEST, 128_000),
            (ModelType.COMETAPI_CLAUDE_OPUS_4_1_20250805, 128_000),
            (ModelType.COMETAPI_GEMINI_2_5_PRO, 128_000),
            (ModelType.COMETAPI_GROK_4_0709, 128_000),
            (ModelType.COMETAPI_DEEPSEEK_V3_1, 128_000),
            (ModelType.COMETAPI_QWEN3_30B_A3B, 128_000),
        ]

        for model_type, expected_limit in test_cases:
            assert model_type.token_limit == expected_limit

    @patch("camel.models.openai_compatible_model.OpenAI")
    def test_cometapi_model_client_initialization(self, mock_openai):
        # Test that the OpenAI client is initialized with correct parameters
        with patch.dict(os.environ, {"COMETAPI_KEY": "test_api_key"}):
            CometAPIModel(ModelType.COMETAPI_GPT_5_CHAT_LATEST)

        mock_openai.assert_called_once()
        call_kwargs = mock_openai.call_args.kwargs

        assert call_kwargs["api_key"] == "test_api_key"
        assert call_kwargs["base_url"] == "https://api.cometapi.com/v1"
        assert call_kwargs["timeout"] == 180.0
        assert call_kwargs["max_retries"] == 3

    @patch("camel.models.openai_compatible_model.OpenAI")
    @patch("camel.models.openai_compatible_model.AsyncOpenAI")
    def test_cometapi_model_async_client_initialization(
        self, mock_async_openai, mock_openai
    ):
        # Test that both sync and async clients are initialized
        with patch.dict(os.environ, {"COMETAPI_KEY": "test_api_key"}):
            CometAPIModel(ModelType.COMETAPI_GPT_5_CHAT_LATEST)

        # Both clients should be initialized
        mock_openai.assert_called_once()
        mock_async_openai.assert_called_once()

    @patch("camel.models.openai_compatible_model.OpenAI")
    def test_cometapi_model_chat_completion(self, mock_openai):
        # Test chat completion functionality
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Mock response
        mock_response = Mock(spec=ChatCompletion)
        mock_client.chat.completions.create.return_value = mock_response

        with patch.dict(os.environ, {"COMETAPI_KEY": "test_api_key"}):
            model = CometAPIModel(ModelType.COMETAPI_GPT_5_CHAT_LATEST)

        messages = [{"role": "user", "content": "Hello, how are you?"}]

        # Call the _run method to test chat completion
        result = model._run(messages)

        # Verify the API call was made correctly
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs

        assert call_kwargs["messages"] == messages
        assert call_kwargs["model"] == ModelType.COMETAPI_GPT_5_CHAT_LATEST
        assert result == mock_response

    @patch("camel.models.openai_compatible_model.OpenAI")
    def test_cometapi_model_streaming(self, mock_openai):
        # Test streaming functionality
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Mock streaming response
        mock_stream = Mock()
        mock_client.chat.completions.create.return_value = mock_stream

        with patch.dict(os.environ, {"COMETAPI_KEY": "test_api_key"}):
            # Create model with streaming enabled
            config = CometAPIConfig(stream=True).as_dict()
            model = CometAPIModel(
                ModelType.COMETAPI_GPT_5_CHAT_LATEST,
                model_config_dict=config,
            )

        messages = [{"role": "user", "content": "Hello, how are you?"}]

        # Call the _run method to test streaming
        result = model._run(messages)

        # Verify the API call was made with streaming enabled
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs

        assert call_kwargs["stream"] is True
        assert result == mock_stream

    @patch("camel.models.openai_compatible_model.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_cometapi_model_async_chat_completion(
        self, mock_async_openai
    ):
        # Test async chat completion functionality
        mock_async_client = AsyncMock()
        mock_async_openai.return_value = mock_async_client

        # Mock async response
        mock_response = Mock(spec=ChatCompletion)
        mock_async_client.chat.completions.create.return_value = mock_response

        with patch.dict(os.environ, {"COMETAPI_KEY": "test_api_key"}):
            model = CometAPIModel(ModelType.COMETAPI_GPT_5_CHAT_LATEST)

        messages = [{"role": "user", "content": "Hello, how are you?"}]

        # Call the async _arun method
        result = await model._arun(messages)

        # Verify the async API call was made correctly
        mock_async_client.chat.completions.create.assert_called_once()
        call_kwargs = (
            mock_async_client.chat.completions.create.call_args.kwargs
        )

        assert call_kwargs["messages"] == messages
        assert call_kwargs["model"] == ModelType.COMETAPI_GPT_5_CHAT_LATEST
        assert result == mock_response

    def test_cometapi_model_custom_timeout_and_retries(self):
        # Test custom timeout and retry configuration
        with patch.dict(
            os.environ,
            {
                "COMETAPI_KEY": "test_key",
                "MODEL_TIMEOUT": "300",  # 5 minutes
            },
        ):
            with patch(
                "camel.models.openai_compatible_model.OpenAI"
            ) as mock_openai:
                CometAPIModel(
                    ModelType.COMETAPI_GPT_5_CHAT_LATEST,
                    timeout=120,  # Override with 2 minutes
                    max_retries=5,
                )

                call_kwargs = mock_openai.call_args.kwargs
                assert (
                    call_kwargs["timeout"] == 120
                )  # Should use explicit timeout
                assert call_kwargs["max_retries"] == 5

    def test_cometapi_model_missing_api_key(self):
        # Test error handling when API key is missing
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError):
                CometAPIModel(ModelType.COMETAPI_GPT_5_CHAT_LATEST)

    def test_cometapi_config_api_params(self):
        # Test that CometAPIConfig exports the correct API parameters
        from camel.configs.cometapi_config import COMETAPI_API_PARAMS

        expected_params = {
            "temperature",
            "top_p",
            "n",
            "stream",
            "stop",
            "max_tokens",
            "presence_penalty",
            "response_format",
            "frequency_penalty",
            "user",
            "tool_choice",
            "tools",
        }

        assert COMETAPI_API_PARAMS == expected_params

    def test_cometapi_config_default_values(self):
        # Test that CometAPIConfig has correct default values
        config = CometAPIConfig()

        assert config.temperature is None
        assert config.top_p is None
        assert config.n is None
        assert config.stream is None
        assert config.stop is None
        assert config.max_tokens is None
        assert config.presence_penalty is None
        assert config.response_format is None
        assert config.frequency_penalty is None
        assert config.user is None
        assert config.tool_choice is None

    def test_cometapi_config_custom_values(self):
        # Test that CometAPIConfig accepts custom values
        config = CometAPIConfig(
            temperature=0.7,
            top_p=0.9,
            max_tokens=1000,
            stream=True,
            stop=["<|end|>"],
            presence_penalty=0.5,
            frequency_penalty=0.3,
            user="test_user",
        )

        assert config.temperature == 0.7
        assert config.top_p == 0.9
        assert config.max_tokens == 1000
        assert config.stream is True
        assert config.stop == ["<|end|>"]
        assert config.presence_penalty == 0.5
        assert config.frequency_penalty == 0.3
        assert config.user == "test_user"
