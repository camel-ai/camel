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
