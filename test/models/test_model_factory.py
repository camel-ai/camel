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
from pathlib import Path
from unittest.mock import patch

import pytest

from camel.configs import (
    AnthropicConfig,
    ChatGPTConfig,
    GeminiConfig,
    OllamaConfig,
)
from camel.models import ModelFactory
from camel.models.stub_model import StubTokenCounter
from camel.types import ModelPlatformType, ModelType
from camel.utils import (
    AnthropicTokenCounter,
    OpenAITokenCounter,
)

parametrize = pytest.mark.parametrize(
    'model_platform, model_type',
    [
        (ModelPlatformType.OPENAI, ModelType.GPT_4O),
        (ModelPlatformType.OPENAI, ModelType.GPT_4O_MINI),
    ],
)

parameterize_token_counter = pytest.mark.parametrize(
    'model_platform, model_type, model_config_dict, token_counter,'
    ' expected_counter_type, expected_model_type',
    [
        # Test OpenAI model
        (
            ModelPlatformType.OPENAI,
            ModelType.GPT_3_5_TURBO,
            ChatGPTConfig().as_dict(),
            None,
            OpenAITokenCounter,
            ModelType.GPT_3_5_TURBO,
        ),
        (
            ModelPlatformType.OPENAI,
            ModelType.GPT_4O_MINI,
            ChatGPTConfig().as_dict(),
            None,
            OpenAITokenCounter,
            ModelType.GPT_4O_MINI,
        ),
        # Test Stub model
        # Stub model uses StubTokenCounter as default
        (
            ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            ModelType.STUB,
            ChatGPTConfig().as_dict(),
            None,
            StubTokenCounter,
            None,
        ),
        (
            ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            ModelType.STUB,
            ChatGPTConfig().as_dict(),
            OpenAITokenCounter(ModelType.GPT_4O_MINI),
            OpenAITokenCounter,
            ModelType.GPT_4O_MINI,
        ),
        # Test Anthropic model
        # Anthropic model uses AnthropicTokenCounter as default
        (
            ModelPlatformType.ANTHROPIC,
            ModelType.CLAUDE_2_0,
            AnthropicConfig().as_dict(),
            None,
            AnthropicTokenCounter,
            ModelType.CLAUDE_2_0,
        ),
        (
            ModelPlatformType.ANTHROPIC,
            ModelType.CLAUDE_2_0,
            AnthropicConfig().as_dict(),
            OpenAITokenCounter(ModelType.GPT_3_5_TURBO),
            OpenAITokenCounter,
            ModelType.GPT_3_5_TURBO,
        ),
        # Test GEMINI model
        (
            ModelPlatformType.GEMINI,
            ModelType.GEMINI_1_5_FLASH,
            GeminiConfig().as_dict(),
            OpenAITokenCounter(ModelType.GPT_4O_MINI),
            OpenAITokenCounter,
            ModelType.GPT_4O_MINI,
        ),
        # Test Ollama model
        (
            ModelPlatformType.OLLAMA,
            "gpt-3.5-turbo",
            OllamaConfig().as_dict(),
            None,
            OpenAITokenCounter,
            ModelType.GPT_3_5_TURBO,
        ),
        (
            ModelPlatformType.OLLAMA,
            "gpt-3.5-turbo",
            OllamaConfig().as_dict(),
            OpenAITokenCounter(ModelType.GPT_4O_MINI),
            OpenAITokenCounter,
            ModelType.GPT_4O_MINI,
        ),
    ],
)


@parametrize
def test_model_factory(model_platform, model_type):
    model_config_dict = ChatGPTConfig().as_dict()
    model_inst = ModelFactory.create(
        model_platform, model_type, model_config_dict
    )
    messages = [
        {
            "role": "system",
            "content": "Initialize system",
        },
        {
            "role": "user",
            "content": "Hello",
        },
    ]
    response = model_inst.run(messages).model_dump()
    assert isinstance(response, dict)
    assert 'id' in response
    assert isinstance(response['id'], str)
    assert 'usage' in response
    assert isinstance(response['usage'], dict)
    assert 'choices' in response
    assert isinstance(response['choices'], list)
    assert len(response['choices']) == 1
    choice = response['choices'][0]
    assert 'finish_reason' in choice
    assert isinstance(choice['finish_reason'], str)
    assert 'message' in choice
    message = choice['message']
    assert isinstance(message, dict)
    assert 'content' in message
    assert isinstance(message['content'], str)
    assert 'role' in message
    assert isinstance(message['role'], str)
    assert message['role'] == 'assistant'


json_config_files = [
    "test_config_file/json_configs/claude2_config.json",
    "test_config_file/json_configs/claude2_openai_token_counter.json",
    "test_config_file/json_configs/gemini_1.5_flash_config.json",
    "test_config_file/json_configs/ollama_config.json",
    "test_config_file/json_configs/ollama_openai_token_counter.json",
    "test_config_file/json_configs/openai3.5_turbo_config.json",
    "test_config_file/json_configs/openai4o_config.json",
]


@pytest.mark.parametrize("config_file", json_config_files)
@patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
@patch("camel.models.base_model.BaseModelBackend.run")
def test_model_factory_json(mock_run, config_file):
    r"""Test ModelFactory with JSON files without actual API calls."""

    # Get the directory of the current test file
    test_dir = Path(__file__).parent
    json_path = test_dir / config_file
    if not json_path.exists():
        pytest.skip(f"Skipping file {json_path}")

    mock_run.return_value = {
        "id": "test_response",
        "usage": {"total_tokens": 10},
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "Hello, test!"},
            }
        ],
    }

    model_inst = ModelFactory.create_from_json(str(json_path))

    messages = [
        {"role": "system", "content": "Initialize system"},
        {"role": "user", "content": "Hello"},
    ]

    response = model_inst.run(messages)

    assert isinstance(response, dict)
    assert response["id"] == "test_response"
    assert "usage" in response
    assert "choices" in response
    assert response["choices"][0]["message"]["role"] == "assistant"
    assert response["choices"][0]["message"]["content"] == "Hello, test!"

    print(f"JSON file {config_file} loaded successfully.")


yaml_config_files = [
    "test_config_file/yaml_configs/claude2_config.yaml",
    "test_config_file/yaml_configs/claude2_openai_config.yaml",
    "test_config_file/yaml_configs/gemini_1.5_flash_config.yaml",
    "test_config_file/yaml_configs/ollama_config.yaml",
    "test_config_file/yaml_configs/ollama_openai_config.yaml",
    "test_config_file/yaml_configs/openai3.5_turbo_config.yaml",
    "test_config_file/yaml_configs/openai4o_config.yaml",
]


@pytest.mark.parametrize("config_file", yaml_config_files)
@patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"})
@patch("camel.models.base_model.BaseModelBackend.run")
def test_model_factory_yaml(mock_run, config_file):
    r"""Test ModelFactory with YAML files without real API calls."""

    # Get the directory of the current test file
    test_dir = Path(__file__).parent
    yaml_path = test_dir / config_file
    if not yaml_path.exists():
        pytest.skip(f"Skipping file {yaml_path}")

    mock_run.return_value = {
        "id": "test_response",
        "usage": {"total_tokens": 10},
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "Hello, test!"},
            }
        ],
    }

    model_inst = ModelFactory.create_from_yaml(str(yaml_path))

    messages = [
        {"role": "system", "content": "Initialize system"},
        {"role": "user", "content": "Hello"},
    ]

    response = model_inst.run(messages)

    assert isinstance(response, dict)
    assert response["id"] == "test_response"
    assert "usage" in response
    assert "choices" in response
    assert response["choices"][0]["message"]["role"] == "assistant"
    assert response["choices"][0]["message"]["content"] == "Hello, test!"

    print(f" YAML file {config_file} loaded successfully.")
