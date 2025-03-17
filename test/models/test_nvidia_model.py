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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camel.configs import NvidiaConfig
from camel.models import NvidiaModel
from camel.types import ModelType

user_role_message = {
    "role": "user",
    "content": "How fast can you solve a math problem?",
}

model_types = [
    ModelType.NVIDIA_NEMOTRON_340B_INSTRUCT,
    ModelType.NVIDIA_NEMOTRON_340B_REWARD,
    ModelType.NVIDIA_YI_LARGE,
    ModelType.NVIDIA_MISTRAL_LARGE,
    ModelType.NVIDIA_LLAMA3_70B,
    ModelType.NVIDIA_MIXTRAL_8X7B,
    ModelType.NVIDIA_LLAMA3_1_8B_INSTRUCT,
    ModelType.NVIDIA_LLAMA3_1_70B_INSTRUCT,
    ModelType.NVIDIA_LLAMA3_1_405B_INSTRUCT,
    ModelType.NVIDIA_LLAMA3_2_1B_INSTRUCT,
    ModelType.NVIDIA_LLAMA3_2_3B_INSTRUCT,
    ModelType.NVIDIA_LLAMA3_3_70B_INSTRUCT,
]


@pytest.fixture(autouse=True)
def mock_env_vars():
    r"""Provide mock environment variables for all tests in this module."""
    with patch.dict(os.environ, {"NVIDIA_API_KEY": "mock-api-key"}):
        yield


@pytest.fixture
def mock_openai_client():
    with patch("camel.models.nvidia_model.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = None
        yield mock_client


@pytest.fixture
def mock_async_openai_client():
    with patch("camel.models.nvidia_model.AsyncOpenAI") as mock_async_openai:
        mock_client = AsyncMock()
        mock_async_openai.return_value = mock_client

        # Create an AsyncMock that will be awaitable and have Mock
        # functionality
        mock_chat = AsyncMock()
        mock_chat.return_value = None
        mock_client.chat.completions.create.return_value = mock_chat
        yield mock_client


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    model_types,
)
def test_nvidia_model(model_type: ModelType):
    model = NvidiaModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == NvidiaConfig().as_dict()
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    model_types,
)
def test_nvidia_model_run(mock_openai_client, model_type: ModelType):
    config = NvidiaConfig().as_dict()
    config["tool_choice"] = "google"
    config["tools"] = None
    model = NvidiaModel(model_type, config)
    model.run([user_role_message])  # type: ignore[list-item]

    # Verify the call arguments
    assert mock_openai_client.chat.completions.create.call_count == 1
    call_args = mock_openai_client.chat.completions.create.call_args
    kwargs = call_args[1]

    # Check that messages were passed correctly
    assert "messages" in kwargs
    assert len(kwargs["messages"]) == 1

    # Check message contents
    assert kwargs["messages"][0]["role"] == 'user'
    assert (
        kwargs["messages"][0]["content"]
        == "How fast can you solve a math problem?"
    )


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    model_types,
)
@pytest.mark.asyncio
async def test_nvidia_model_arun(
    mock_async_openai_client, model_type: ModelType
):
    config = NvidiaConfig().as_dict()
    config["tool_choice"] = "google"
    config["tools"] = None
    model = NvidiaModel(model_type, config)
    _ = await model.arun([user_role_message])  # type: ignore[list-item]

    # Verify the call arguments
    assert mock_async_openai_client.chat.completions.create.call_count == 1
    call_args = mock_async_openai_client.chat.completions.create.call_args
    kwargs = call_args[1]

    # Check that messages were passed correctly
    assert "messages" in kwargs
    assert len(kwargs["messages"]) == 1

    # Check message contents
    assert kwargs["messages"][0]["role"] == 'user'
    assert (
        kwargs["messages"][0]["content"]
        == "How fast can you solve a math problem?"
    )


@pytest.mark.model_backend
def test_nvidia_model_unexpected_argument():
    model_type = ModelType.NVIDIA_LLAMA3_70B
    model_config_dict = {"model_path": "nvidia-llama3"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Unexpected argument `model_path` is "
                "input into NVIDIA model backend."
            )
        ),
    ):
        _ = NvidiaModel(model_type, model_config_dict)
