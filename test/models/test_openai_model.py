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

    # Compare config dicts, but exclude prompt_cache_key since it's
    # a unique UUID generated per instance via default_factory
    model_config = model.model_config_dict.copy()
    expected_config = ChatGPTConfig().as_dict()

    model_cache_key = model_config.pop("prompt_cache_key", None)
    expected_cache_key = expected_config.pop("prompt_cache_key", None)

    # Both should have a prompt_cache_key (UUID format)
    assert model_cache_key is not None
    assert expected_cache_key is not None

    # The rest of the config should match
    assert model_config == expected_config

    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


def test_prompt_cache_key_in_config():
    """Test that prompt_cache_key is properly set in ChatGPTConfig."""
    # Test default value - each instance should have a unique UUID
    config1 = ChatGPTConfig()
    config2 = ChatGPTConfig()

    assert config1.prompt_cache_key is not None
    assert config2.prompt_cache_key is not None
    # Each instance should have a unique default UUID
    assert config1.prompt_cache_key != config2.prompt_cache_key

    # Test custom prompt_cache_key
    custom_key = "my-custom-cache-key"
    config_custom = ChatGPTConfig(prompt_cache_key=custom_key)
    assert config_custom.prompt_cache_key == custom_key

    # Test that prompt_cache_key is included in as_dict()
    config_dict = config_custom.as_dict()
    assert "prompt_cache_key" in config_dict
    assert config_dict["prompt_cache_key"] == custom_key

    # Test None value - should not be included in as_dict()
    config_none = ChatGPTConfig(prompt_cache_key=None)
    config_dict_none = config_none.as_dict()
    assert "prompt_cache_key" not in config_dict_none


def test_prompt_cache_key_passed_to_api():
    """Test that prompt_cache_key is passed to the OpenAI API."""

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

        model = OpenAIModel(
            model_type=ModelType.GPT_4O_MINI,
        )
        messages = [{"role": "user", "content": "Hello"}]
        model.run(messages)

        # Verify that prompt_cache_key was passed to the API
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert "prompt_cache_key" in call_kwargs
        assert call_kwargs["prompt_cache_key"] is not None
