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

import re
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from cohere.types.chat_message_v2 import (
    AssistantChatMessageV2,
    SystemChatMessageV2,
    UserChatMessageV2,
)
from pydantic import BaseModel

from camel.configs import CohereConfig
from camel.models import CohereModel
from camel.types import ChatCompletion, ModelType
from camel.utils import OpenAITokenCounter

cohere_model_response = SimpleNamespace(
    id="1",
    usage=SimpleNamespace(
        tokens=SimpleNamespace(input_tokens=100, output_tokens=100)
    ),
    finish_reason="finish reason",
    message=SimpleNamespace(
        content=[SimpleNamespace(text="The capital of Morocco is Rabat")],
        tool_plan="The capital of Morocco is Rabat",
        tool_calls=[
            SimpleNamespace(
                id=1,
                function=SimpleNamespace(
                    name="my_function",
                    arguments=["arg1", "arg2"],
                    type="my_type",
                ),
                type="my_type",
            )
        ],
    ),
)

system_role_message = {
    "role": "system",
    "content": "Answer the user's question with 6 words maximum",
}
user_role_message = {
    "role": "user",
    "content": "What is the capital of Morocco ?",
}

assistant_role_message = {
    "role": "assistant",
    "content": "Morocco is a country in North Africa",
}

unsupported_role_message = {
    "role": "unsupported_role",
    "content": "Hello World",
}

model_types = [
    ModelType.COHERE_COMMAND_R,
    ModelType.COHERE_COMMAND_LIGHT,
    ModelType.COHERE_COMMAND,
    ModelType.COHERE_COMMAND_NIGHTLY,
    ModelType.COHERE_COMMAND_R_PLUS,
]


class ResponseFormat(BaseModel):
    short_response: str
    explaining: str
    example: str


@pytest.fixture
def mock_cohere_client():
    with patch("cohere.ClientV2") as mock_cohere:
        mock_client = MagicMock()
        mock_cohere.return_value = mock_client
        mock_client.chat.return_value = cohere_model_response
        yield mock_client


@pytest.fixture
def mock_async_cohere_client():
    with patch("cohere.AsyncClientV2") as mock_async_cohere:
        mock_client = MagicMock()
        mock_async_cohere.return_value = mock_client

        async def async_get_cohere_model_response():
            return cohere_model_response

        mock_client.chat.return_value = async_get_cohere_model_response
        yield mock_client


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    model_types,
)
def test_cohere_model(model_type):
    model_config_dict = CohereConfig().as_dict()
    model = CohereModel(model_type, model_config_dict)
    assert model.model_type == model_type
    assert model.model_config_dict == model_config_dict
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
def test_cohere_model_unexpected_argument():
    model_type = ModelType.COHERE_COMMAND_R
    model_config_dict = {"model_path": "vicuna-7b-v1.5"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Unexpected argument `model_path` is "
                "input into Cohere model backend."
            )
        ),
    ):
        _ = CohereModel(model_type, model_config_dict)


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    model_types,
)
def test_cohere_model_run(mock_cohere_client, model_type):
    model_config_dict = CohereConfig().as_dict()
    model_config_dict.update(
        {"tools": [{"function": {"strict": True, "another_function": True}}]}
    )
    mock_record = patch("camel.models.cohere_model.record").start()
    model = CohereModel(model_type, model_config_dict)
    model_inference = model.run(
        [system_role_message, user_role_message, assistant_role_message]
    )
    mock_cohere_client.chat.assert_called_once_with(
        messages=[
            SystemChatMessageV2(
                role='system',
                content="Answer the user's question with 6 words maximum",
            ),
            UserChatMessageV2(
                role='user', content='What is the capital of Morocco ?'
            ),
            AssistantChatMessageV2(
                role='assistant',
                tool_calls=None,
                tool_plan=None,
                content='Morocco is a country in North Africa',
                citations=None,
            ),
        ],
        model=model_type,
        tools=[{'function': {'another_function': True}}],
        temperature=0.2,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        k=0,
        p=0.75,
    )
    assert isinstance(model_inference, ChatCompletion)
    assert (
        model_inference.choices[0].message.content
        == "The capital of Morocco is Rabat"
    )
    mock_record.assert_called()


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    model_types,
)
def test_cohere_model_run_with_response_format(mock_cohere_client, model_type):
    model_config_dict = CohereConfig().as_dict()
    model = CohereModel(model_type, model_config_dict)
    model_inference = model.run(
        messages=[
            system_role_message,
            assistant_role_message,
            user_role_message,
        ],
        response_format=ResponseFormat,
    )
    mock_cohere_client.chat.assert_called_once_with(
        messages=[
            SystemChatMessageV2(
                role='system',
                content="Answer the user's question with 6 words maximum",
            ),
            AssistantChatMessageV2(
                role='assistant',
                tool_calls=None,
                tool_plan=None,
                content='Morocco is a country in North Africa',
                citations=None,
            ),
            UserChatMessageV2(
                role='user',
                content="What is the capital of Morocco ?\n\nPlease generate a JSON response adhering to the following JSON schema:\n{'properties': {'short_response': {'title': 'Short Response', 'type': 'string'}, 'explaining': {'title': 'Explaining', 'type': 'string'}, 'example': {'title': 'Example', 'type': 'string'}}, 'required': ['short_response', 'explaining', 'example'], 'title': 'ResponseFormat', 'type': 'object'}\nMake sure the JSON response is valid and matches the EXACT structure defined in the schema.Your result should ONLY be a valid json object, WITHOUT ANY OTHER TEXT OR COMMENTS.\n",  # noqa: E501
            ),
        ],
        model=model_type,
        temperature=0.2,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        k=0,
        p=0.75,
        response_format={'type': 'json_object'},
    )
    assert isinstance(model_inference, ChatCompletion)
    assert (
        model_inference.choices[0].message.content
        == "The capital of Morocco is Rabat"
    )


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    model_types,
)
@pytest.mark.asyncio
async def test_cohere_model_arun(mock_async_cohere_client, model_type):
    model_config_dict = CohereConfig().as_dict()
    model = CohereModel(model_type, model_config_dict)
    model_inference = await model.arun(
        [system_role_message, user_role_message, assistant_role_message]
    )
    mock_async_cohere_client.chat.assert_called_once_with(
        messages=[
            SystemChatMessageV2(
                role='system',
                content="Answer the user's question with 6 words maximum",
            ),
            UserChatMessageV2(
                role='user', content='What is the capital of Morocco ?'
            ),
            AssistantChatMessageV2(
                role='assistant',
                tool_calls=None,
                tool_plan=None,
                content='Morocco is a country in North Africa',
                citations=None,
            ),
        ],
        model=model_type,
        tools=[{'function': {'another_function': True}}],
        temperature=0.2,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        k=0,
        p=0.75,
    )
    assert isinstance(model_inference, ChatCompletion)
    assert (
        model_inference.choices[0].message.content
        == "The capital of Morocco is Rabat"
    )


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    model_types,
)
def test_cohere_model_run_unsupported_role(mock_cohere_client, model_type):
    model = CohereModel(model_type)
    with pytest.raises(
        ValueError,
        match=re.escape(("Unsupported message role: unsupported_role")),
    ):
        _ = model.run([unsupported_role_message])
