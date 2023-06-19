# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import pytest

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.generators import SystemMessageGenerator
from camel.messages import ChatMessage, SystemMessage
from camel.typing import ModelType, RoleType, TaskType

parametrize = pytest.mark.parametrize('model', [
    ModelType.STUB,
    pytest.param(ModelType.GPT_3_5_TURBO, marks=pytest.mark.model_backend),
    pytest.param(ModelType.GPT_4, marks=pytest.mark.model_backend),
])


@parametrize
def test_chat_agent(model: ModelType):

    model_config = ChatGPTConfig()
    system_msg = SystemMessageGenerator(
        task_type=TaskType.AI_SOCIETY).from_dict(
            dict(assistant_role="doctor"),
            role_tuple=("doctor", RoleType.ASSISTANT),
        )
    assistant = ChatAgent(system_msg, model=model, model_config=model_config)

    assert str(assistant) == ("ChatAgent(doctor, "
                              f"RoleType.ASSISTANT, {str(model)})")

    assistant.reset()
    user_msg = ChatMessage(role_name="Patient", role_type=RoleType.USER,
                           meta_dict=dict(), role="user", content="Hello!")
    assistant_response = assistant.step(user_msg)

    assert isinstance(assistant_response.msgs, list)
    assert len(assistant_response.msgs) > 0
    assert isinstance(assistant_response.terminated, bool)
    assert assistant_response.terminated is False
    assert isinstance(assistant_response.info, dict)
    assert assistant_response.info['id'] is not None

    assistant.reset()
    token_limit = assistant.model_token_limit
    user_msg = ChatMessage(role_name="Patient", role_type=RoleType.USER,
                           meta_dict=dict(), role="user",
                           content="token" * (token_limit + 1))
    assistant_response = assistant.step(user_msg)

    assert isinstance(assistant_response.msgs, list)
    assert len(assistant_response.msgs) == 0
    assert isinstance(assistant_response.terminated, bool)
    assert assistant_response.terminated is True
    assert isinstance(assistant_response.info, dict)
    assert (assistant_response.info['termination_reasons'][0] ==
            "max_tokens_exceeded")


@pytest.mark.model_backend
@pytest.mark.parametrize('n', [1, 2, 3])
def test_chat_agent_multiple_return_messages(n):
    model_config = ChatGPTConfig(temperature=1.4, n=n)
    system_msg = SystemMessage("Assistant", RoleType.ASSISTANT,
                               content="You are a helpful assistant.")
    assistant = ChatAgent(system_msg, model_config=model_config)
    assistant.reset()
    user_msg = ChatMessage(role_name="User", role_type=RoleType.USER,
                           meta_dict=dict(), role="user",
                           content="Tell me a joke.")
    assistant_response = assistant.step(user_msg)
    assert assistant_response.msgs is not None
    assert len(assistant_response.msgs) == n
