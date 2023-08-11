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

from camel.agents import ChatAgent, CriticAgent
from camel.human import Human
from camel.messages import BaseMessage
from camel.societies import RolePlaying
from camel.typing import ModelType, RoleType, TaskType


@pytest.mark.parametrize("model_type", [None, ModelType.GPT_4])
@pytest.mark.parametrize("critic_role_name", ["human", "critic agent"])
@pytest.mark.parametrize("with_critic_in_the_loop", [True, False])
def test_role_playing_init(model_type, critic_role_name,
                           with_critic_in_the_loop):
    role_playing = RolePlaying(
        assistant_role_name="assistant",
        assistant_agent_kwargs=dict(model=ModelType.GPT_3_5_TURBO_16K),
        user_role_name="user",
        user_agent_kwargs=dict(model=ModelType.GPT_3_5_TURBO_16K),
        model_type=model_type,
        critic_role_name=critic_role_name,
        task_prompt="Perform the task",
        with_task_specify=False,
        task_specify_agent_kwargs=dict(model=ModelType.GPT_4),
        with_task_planner=False,
        task_planner_agent_kwargs=dict(model=ModelType.GPT_4),
        with_critic_in_the_loop=with_critic_in_the_loop,
        task_type=TaskType.AI_SOCIETY,
    )
    assert role_playing.with_task_specify is False
    assert role_playing.with_task_planner is False
    assert role_playing.with_critic_in_the_loop is with_critic_in_the_loop
    assert role_playing.task_type == TaskType.AI_SOCIETY
    assert role_playing.task_prompt == "Perform the task"
    assert role_playing.specified_task_prompt is None
    assert role_playing.planned_task_prompt is None

    assert isinstance(role_playing.assistant_sys_msg, BaseMessage)
    assert role_playing.assistant_sys_msg.role_type == RoleType.ASSISTANT
    assert isinstance(role_playing.user_sys_msg, BaseMessage)
    assert role_playing.user_sys_msg.role_type == RoleType.USER

    assistant_agent = role_playing.assistant_agent
    user_agent = role_playing.user_agent
    critic = role_playing.critic

    assert isinstance(assistant_agent, ChatAgent)
    assert isinstance(user_agent, ChatAgent)
    if model_type is None:
        assert assistant_agent.model == ModelType.GPT_3_5_TURBO_16K
        assert user_agent.model == ModelType.GPT_3_5_TURBO_16K
    else:
        assert assistant_agent.model == ModelType.GPT_4
        assert user_agent.model == ModelType.GPT_4

    if not with_critic_in_the_loop:
        assert critic is None
    else:
        assert critic is not None
        if critic_role_name == "human":
            assert isinstance(critic, Human)
        else:
            assert isinstance(critic, CriticAgent)
            assert role_playing.critic_sys_msg is not None
            if model_type is None:
                assert critic.model == ModelType.GPT_3_5_TURBO
            else:
                assert critic.model == ModelType.GPT_4


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "task_type, extend_sys_msg_meta_dicts, extend_task_specify_meta_dict",
    [(TaskType.AI_SOCIETY, None, None),
     (TaskType.CODE, [dict(domain="science", language="python")] * 2,
      dict(domain="science", language="python")),
     (TaskType.MISALIGNMENT, None, None)])
def test_role_playing_step(task_type, extend_sys_msg_meta_dicts,
                           extend_task_specify_meta_dict):
    role_playing = RolePlaying(
        assistant_role_name="AI Assistant",
        assistant_agent_kwargs=dict(model=ModelType.GPT_3_5_TURBO),
        user_role_name="AI User",
        user_agent_kwargs=dict(model=ModelType.GPT_3_5_TURBO),
        task_prompt="Perform the task",
        task_specify_agent_kwargs=dict(model=ModelType.GPT_3_5_TURBO),
        task_type=task_type,
        extend_sys_msg_meta_dicts=extend_sys_msg_meta_dicts,
        extend_task_specify_meta_dict=extend_task_specify_meta_dict,
    )
    init_assistant_msg = BaseMessage.make_assistant_message(
        role_name="AI Assistant", content="Hello")
    print(role_playing.assistant_agent.system_message)
    print(role_playing.user_agent.system_message)

    assistant_response, user_response = role_playing.step(init_assistant_msg)

    for response in (assistant_response, user_response):
        assert isinstance(response.msgs, list)
        assert len(response.msgs) == 1
        assert isinstance(response.msgs[0], BaseMessage)
        assert isinstance(response.terminated, bool)
        assert response.terminated is False
        assert isinstance(response.info, dict)
