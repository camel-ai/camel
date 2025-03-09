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
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from camel.configs import GeminiConfig
from camel.models import GeminiModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter

model_types = [
    ModelType.GEMINI_2_0_FLASH,
    ModelType.GEMINI_1_5_FLASH,
    ModelType.GEMINI_1_5_PRO,
    ModelType.GEMINI_2_0_FLASH_THINKING,
    ModelType.GEMINI_2_0_FLASH_LITE_PREVIEW,
    ModelType.GEMINI_2_0_PRO_EXP,
]

user_role_message = {
    "role": "user",
    "content": "Is cloud run a good solution for a web app ?",
}

empty_content_message = {"role": "user", "content": ""}


class ResponseFormat(BaseModel):
    short_response: str
    explaining: str
    example: str


@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key"}):
        yield


@pytest.fixture
def mock_openai_client():
    with patch("camel.models.gemini_model.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value = SimpleNamespace()
        mock_client.beta.chat.completions.parse.return_value = None
        yield mock_client


@pytest.fixture
def mock_async_client_openai():
    with patch(
        "camel.models.gemini_model.AsyncOpenAI"
    ) as mock_async_client_openai:
        mock_client = MagicMock()
        mock_async_client_openai.return_value = mock_client

        async def async_create(*args, **kwargs):
            return None

        mock_client.chat.completions.create.return_value = async_create()
        mock_client.beta.chat.completions.parse.return_value = async_create()
        yield mock_client


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    model_types,
)
def test_gemini_model(model_type: ModelType):
    model_config_dict = GeminiConfig().as_dict()
    model = GeminiModel(model_type, model_config_dict)
    assert model.model_type == model_type
    assert model.model_config_dict == model_config_dict
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    model_types,
)
def test_gemini_run(mock_openai_client, model_type: ModelType):
    model = GeminiModel(model_type)
    model.run([user_role_message, empty_content_message])  # type: ignore[list-item]
    # Verify the call arguments
    assert mock_openai_client.chat.completions.create.call_count == 1
    call_args = mock_openai_client.chat.completions.create.call_args
    kwargs = call_args[1]

    # Check that messages were passed correctly
    assert "messages" in kwargs
    assert len(kwargs["messages"]) == 2

    # Check the model type
    assert "model" in kwargs
    assert kwargs["model"] == model_type

    # Check that there are no empty messages
    assert kwargs["messages"][1]["content"] == "null"


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    model_types,
)
def test_gemini_run_with_response_format(
    mock_openai_client, model_type: ModelType
):
    model = GeminiModel(model_type)
    model.run(messages=[user_role_message], response_format=ResponseFormat)  # type: ignore[list-item]
    # Verify the call arguments
    assert mock_openai_client.beta.chat.completions.parse.call_count == 1
    call_args = mock_openai_client.beta.chat.completions.parse.call_args
    kwargs = call_args[1]

    # Check that messages were passed correctly
    assert "messages" in kwargs
    assert len(kwargs["messages"]) == 1

    # Check the model type
    assert "model" in kwargs
    assert kwargs["model"] == model_type

    # Check that we pass a response format
    assert "response_format" in kwargs


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    model_types,
)
@pytest.mark.asyncio
async def test_gemini_arun(mock_async_client_openai, model_type: ModelType):
    model = GeminiModel(model_type)
    _ = await model.arun([user_role_message, empty_content_message])  # type: ignore[list-item]
    # Verify the call arguments
    assert mock_async_client_openai.chat.completions.create.call_count == 1
    call_args = mock_async_client_openai.chat.completions.create.call_args
    kwargs = call_args[1]

    # Check that messages were passed correctly
    assert "messages" in kwargs
    assert len(kwargs["messages"]) == 2

    # Check the model type
    assert "model" in kwargs
    assert kwargs["model"] == model_type

    # Check that there are no empty messages
    assert kwargs["messages"][1]["content"] == "null"


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    model_types,
)
@pytest.mark.asyncio
async def test_gemini_arun_with_response_format(
    mock_async_client_openai, model_type: ModelType
):
    model = GeminiModel(model_type)
    _ = await model.arun([user_role_message], response_format=ResponseFormat)  # type: ignore[list-item]
    # Verify the call arguments
    assert mock_async_client_openai.beta.chat.completions.parse.call_count == 1
    call_args = mock_async_client_openai.beta.chat.completions.parse.call_args
    kwargs = call_args[1]

    # Check that messages were passed correctly
    assert "messages" in kwargs
    assert len(kwargs["messages"]) == 1

    # Check the model type
    assert "model" in kwargs
    assert kwargs["model"] == model_type

    # Check that we pass a response format
    assert "response_format" in kwargs


@pytest.mark.model_backend
def test_gemini_model_unexpected_argument():
    model_type = ModelType.GEMINI_1_5_FLASH
    model_config_dict = {"model_path": "vicuna-7b-v1.5"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Unexpected argument `model_path` is "
                "input into Gemini model backend."
            )
        ),
    ):
        _ = GeminiModel(model_type, model_config_dict)
