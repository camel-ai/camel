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
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camel.configs import DeepSeekConfig
from camel.models import DeepSeekModel, ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.utils import OpenAITokenCounter


@pytest.fixture(autouse=True)
def mock_env_vars():
    r"""Provide mock environment variables for all tests in this module."""
    with patch.dict(
        os.environ,
        {"DEEPSEEK_API_KEY": "mock-api-key", "GET_REASONING_CONTENT": "True"},
    ):
        yield


@pytest.fixture
def mock_openai_client():
    with patch("camel.models.deepseek_model.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = (
            deepseek_model_response
        )
        yield mock_client


@pytest.fixture
def mock_async_openai_client():
    with patch("camel.models.deepseek_model.AsyncOpenAI") as mock_async_openai:
        mock_client = AsyncMock()
        mock_async_openai.return_value = mock_client

        # Create an AsyncMock that will be awaitable and have Mock
        # functionality
        mock_chat = AsyncMock()
        mock_chat.return_value = deepseek_model_response
        mock_client.chat.completions.create.return_value = mock_chat
        yield mock_client


model_types = [
    ModelType.DEEPSEEK_CHAT,
    ModelType.DEEPSEEK_REASONER,
]

user_role_message = {
    "role": "user",
    "content": "Why is the sky blue ?",
}

deepseek_model_response = SimpleNamespace(
    id="1",
    usage=SimpleNamespace(
        tokens=SimpleNamespace(input_tokens=100, output_tokens=100),
    ),
    model=ModelType.DEEPSEEK_CHAT,
    created=1,
    choices=[
        SimpleNamespace(
            index=1,
            message=SimpleNamespace(
                role="assistant",
                content="Because sunlight is scattered by the atmosphere, and blue waves are dispersed more than other colors.",
                reasoning_content="blue waves are dispersed more than other colors",
            ),
            finish_reason=None,
        )
    ],
)


@pytest.mark.model_backend
@pytest.mark.parametrize("model_type", model_types)
def test_deepseek_model(model_type):
    model_config_dict = DeepSeekConfig().as_dict()
    model = DeepSeekModel(model_type, model_config_dict)
    assert model.model_type == model_type
    assert model.model_config_dict == model_config_dict
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
@pytest.mark.parametrize("model_type", model_types)
def test_deepseek_model_create(model_type: ModelType):
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEEPSEEK,
        model_type=model_type,
        model_config_dict=DeepSeekConfig(temperature=1.3).as_dict(),
    )
    assert model.model_type == model_type


@pytest.mark.model_backend
@pytest.mark.parametrize("model_type", model_types)
def test_deepseek_run(mock_openai_client, model_type: ModelType):
    model = DeepSeekModel(model_type)
    model.run(messages=[user_role_message])  # type: ignore[list-item]
    # Verify the call arguments
    assert mock_openai_client.chat.completions.create.call_count == 1
    call_args = mock_openai_client.chat.completions.create.call_args
    kwargs = call_args[1]

    # Check that messages were passed correctly
    assert "messages" in kwargs
    assert len(kwargs["messages"]) == 1

    # Check message contents
    assert kwargs["messages"][0]["role"] == 'user'
    assert "Why is the sky blue ?" in kwargs["messages"][0]["content"]
    if model_type in [
        ModelType.DEEPSEEK_REASONER,
    ]:
        # Check that the reasoning message is parsed correctly
        # The expected content is the reasoning content wrapped in <think> tags
        # followed by the original content
        expected_content = (
            f"<think>\n{deepseek_model_response.choices[0].message.reasoning_content}\n</think>\n"
            + deepseek_model_response.choices[0].message.content
        )

        # Create a DeepSeekModel instance to test the _post_handle_response method
        with patch.dict(os.environ, {"GET_REASONING_CONTENT": "True"}):
            # Mock the response that would be returned after post-processing
            processed_response = model._post_handle_response(
                deepseek_model_response
            )
            # Verify the processed content matches our expectation
            assert (
                processed_response.choices[0].message.content
                == expected_content
            )


@pytest.mark.model_backend
@pytest.mark.parametrize("model_type", model_types)
@pytest.mark.asyncio
async def test_deepseek_arun(mock_async_openai_client, model_type: ModelType):
    model = DeepSeekModel(model_type)
    _ = await model.arun(messages=[user_role_message])  # type: ignore[list-item]
    # Verify the call arguments
    assert mock_async_openai_client.chat.completions.create.call_count == 1
    call_args = mock_async_openai_client.chat.completions.create.call_args
    kwargs = call_args[1]

    # Check that messages were passed correctly
    assert "messages" in kwargs
    assert len(kwargs["messages"]) == 1

    # Check message contents
    assert kwargs["messages"][0]["role"] == 'user'
    assert "Why is the sky blue ?" in kwargs["messages"][0]["content"]


@pytest.mark.model_backend
def test_deepseek_model_unexpected_argument():
    model_type = ModelType.DEEPSEEK_CHAT
    model_config_dict = {"model_path": "vicuna-7b-v1.5"}

    with pytest.raises(
        ValueError,
        # ruff: noqa: E501
        match=re.escape(
            (
                "Unexpected argument `model_path` is input into DeepSeek model backend."
            )
        ),
    ):
        _ = DeepSeekModel(model_type, model_config_dict)
