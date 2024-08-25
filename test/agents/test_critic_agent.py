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

from camel.agents import CriticAgent
from camel.messages import BaseMessage, Content
from camel.types import RoleType


@pytest.fixture
def critic_agent() -> CriticAgent:
    return CriticAgent(
        BaseMessage(
            role_name="critic",
            role_type=RoleType.CRITIC,
            meta_dict=None,
            content=Content(
                text="You are a critic who assists in selecting an option "
                "and provides explanations. "
                "Your favorite fruit is Apple. "
                "You always have to choose an option."
            ),
        )
    )


def test_flatten_options(critic_agent: CriticAgent):
    messages = [
        BaseMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=dict(),
            content=Content(text="Apple"),
        ),
        BaseMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=dict(),
            content=Content(text="Banana"),
        ),
    ]
    expected_output = (
        f"> Proposals from user ({RoleType.USER!s}). "
        "Please choose an option:\n"
        "Option 1:\nApple\n\n"
        "Option 2:\nBanana\n\n"
        f"Please first enter your choice ([1-{len(messages)}]) "
        "and then your explanation and comparison: "
    )
    assert critic_agent.flatten_options(messages) == expected_output


@pytest.mark.model_backend
def test_get_option(critic_agent: CriticAgent):
    messages = [
        BaseMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=dict(),
            content=Content(text="Apple"),
        ),
        BaseMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=dict(),
            content=Content(text="Banana"),
        ),
    ]
    flatten_options = critic_agent.flatten_options(messages)
    input_message = BaseMessage(
        role_name="user",
        role_type=RoleType.USER,
        meta_dict=dict(),
        content=Content(text=flatten_options),
    )
    assert critic_agent.options_dict == {"1": "Apple", "2": "Banana"}
    assert (
        critic_agent.get_option(input_message)
        in critic_agent.options_dict.values()
    )


def test_parse_critic(critic_agent: CriticAgent):
    critic_msg = BaseMessage(
        role_name="critic",
        role_type=RoleType.CRITIC,
        meta_dict=dict(),
        content=Content(text="I choose option 1"),
    )
    expected_output = "1"
    assert critic_agent.parse_critic(critic_msg) == expected_output


@pytest.mark.model_backend
def test_reduce_step(critic_agent: CriticAgent):
    messages = [
        BaseMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=dict(),
            content=Content(text="Apple"),
        ),
        BaseMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=dict(),
            content=Content(text="Banana"),
        ),
    ]

    critic_response = critic_agent.reduce_step(messages)
    assert (critic_response.msg.content == messages[0].content) or (
        critic_response.msg.content == messages[1].content
    )
