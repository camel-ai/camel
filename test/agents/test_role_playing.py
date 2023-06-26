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
import typing

import pytest

from camel.agents import ChatAgent
from camel.messages import AssistantChatMessage, ChatMessage, SystemMessageType
from camel.societies import RolePlaying
from camel.typing import ModelType, TaskType


def test_role_playing_init():
    role_playing = RolePlaying(
        assistant_role_name="assistant",
        user_role_name="user",
        task_prompt="Perform the task",
        with_task_specify=False,
        with_task_planner=False,
        with_critic_in_the_loop=False,
        model_type=ModelType.GPT_3_5_TURBO,
        task_type=TaskType.AI_SOCIETY,
    )
    assert role_playing.with_task_specify is False
    assert role_playing.with_task_planner is False
    assert role_playing.with_critic_in_the_loop is False
    assert role_playing.model_type == ModelType.GPT_3_5_TURBO
    assert role_playing.task_type == TaskType.AI_SOCIETY
    assert role_playing.task_prompt == "Perform the task"
    assert role_playing.specified_task_prompt is None
    assert role_playing.planned_task_prompt is None

    assert (type(role_playing.assistant_sys_msg)
            in typing.get_args(SystemMessageType))
    assert (type(role_playing.user_sys_msg)
            in typing.get_args(SystemMessageType))

    assert isinstance(role_playing.assistant_agent, ChatAgent)
    assert isinstance(role_playing.user_agent, ChatAgent)

    assert role_playing.critic is None


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
        user_role_name="AI User",
        task_prompt="Perform the task",
        task_type=task_type,
        extend_sys_msg_meta_dicts=extend_sys_msg_meta_dicts,
        extend_task_specify_meta_dict=extend_task_specify_meta_dict,
    )
    init_assistant_msg = AssistantChatMessage(role_name="AI Assistant",
                                              role="assistant",
                                              content="Hello")
    print(role_playing.assistant_agent.system_message)
    print(role_playing.user_agent.system_message)

    assistant_response, user_response = role_playing.step(init_assistant_msg)

    for response in (assistant_response, user_response):
        assert isinstance(response.msgs, list)
        assert len(response.msgs) == 1
        assert isinstance(response.msgs[0], ChatMessage)
        assert isinstance(response.terminated, bool)
        assert response.terminated is False
        assert isinstance(response.info, dict)
