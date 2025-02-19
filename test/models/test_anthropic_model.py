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
"""
please set the below os environment variable:
export ANTHROPIC_API_KEY="xxx"
"""

import re
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from anthropic import NOT_GIVEN

from camel.configs import AnthropicConfig
from camel.models import AnthropicModel
from camel.types import ChatCompletion, ModelType
from camel.utils import AnthropicTokenCounter

anthropic_model_response = SimpleNamespace(
    id="msg_123456",
    type="message",
    role="assistant",
    model="claude-2.1",
    content=[SimpleNamespace(text="The capital city of Morocco is Rabat")],
    stop_reason="stop reason",
)
system_role_message = {
    "role": "system",
    "content": "Answer the user's question with 6 words maximum",
}
user_role_message = {
    "role": "user",
    "content": "What is the capital city of Morocco ?",
}
model_types = [
    ModelType.CLAUDE_INSTANT_1_2,
    ModelType.CLAUDE_2_0,
    ModelType.CLAUDE_2_1,
    ModelType.CLAUDE_3_OPUS,
    ModelType.CLAUDE_3_SONNET,
    ModelType.CLAUDE_3_HAIKU,
    ModelType.CLAUDE_3_5_SONNET,
    ModelType.CLAUDE_3_5_HAIKU,
]


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    model_types,
)
def test_anthropic_model(model_type: ModelType):
    model = AnthropicModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == AnthropicConfig().as_dict()
    assert isinstance(model.token_counter, AnthropicTokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
def test_anthropic_model_unexpected_argument():
    model_type = ModelType.CLAUDE_2_0
    model_config_dict = {"model_path": "vicuna-7b-v1.5"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Unexpected argument `model_path` is "
                "input into Anthropic model backend."
            )
        ),
    ):
        _ = AnthropicModel(model_type, model_config_dict)


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    model_types,
)
@patch("anthropic.Anthropic")
def test_anthropic_run(mock_anthropic, model_type: ModelType):
    # Mock the Anthropic create client function
    mock_anthropic_client = MagicMock()
    mock_anthropic.return_value = mock_anthropic_client
    mock_anthropic_client.messages.create.return_value = (
        anthropic_model_response
    )

    model = AnthropicModel(model_type)
    model_inference = model.run(
        messages=[system_role_message, user_role_message]  # type: ignore[list-item]
    )
    mock_anthropic_client.messages.create.assert_called_once_with(
        model=model_type,
        system=system_role_message["content"],
        messages=[user_role_message],
        max_tokens=8192,
        temperature=1,
        top_p=0.7,
        top_k=5,
        stream=False,
    )
    assert isinstance(model_inference, ChatCompletion)
    assert model_inference.choices[0].message.role == "assistant"
    assert (
        model_inference.choices[0].message.content
        == anthropic_model_response.content[0].text
    )


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    model_types,
)
@patch("anthropic.Anthropic")
def test_anthropic_run_without_sys_msg(mock_anthropic, model_type: ModelType):
    # Mock the Anthropic create client function
    mock_anthropic_client = MagicMock()
    mock_anthropic.return_value = mock_anthropic_client
    mock_anthropic_client.messages.create.return_value = (
        anthropic_model_response
    )

    model = AnthropicModel(model_type)
    model_inference = model.run(messages=[user_role_message])  # type: ignore[list-item]
    mock_anthropic_client.messages.create.assert_called_once_with(
        model=model_type,
        system=NOT_GIVEN,
        messages=[user_role_message],
        max_tokens=8192,
        temperature=1,
        top_p=0.7,
        top_k=5,
        stream=False,
    )
    assert isinstance(model_inference, ChatCompletion)
    assert model_inference.choices[0].message.role == "assistant"
    assert (
        model_inference.choices[0].message.content
        == anthropic_model_response.content[0].text
    )
