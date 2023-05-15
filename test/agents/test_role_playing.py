import typing

import pytest

from camel.agents import ChatAgent, RolePlaying
from camel.messages import AssistantChatMessage, ChatMessage, SystemMessageType
from camel.typing import ModelType, TaskType
from camel.utils import openai_api_key_required


def test_role_playing_init():
    role_playing = RolePlaying(
        assistant_role_name="assistant",
        user_role_name="user",
        task_prompt="Perform the task",
        with_task_specify=False,
        with_task_planner=False,
        with_critic_in_the_loop=False,
        mode_type=ModelType.GPT_3_5_TURBO,
        task_type=TaskType.AI_SOCIETY,
    )
    assert role_playing.with_task_specify is False
    assert role_playing.with_task_planner is False
    assert role_playing.with_critic_in_the_loop is False
    assert role_playing.mode_type == ModelType.GPT_3_5_TURBO
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


@openai_api_key_required
@pytest.mark.parametrize(
    "task_type, extend_sys_msg_meta_dicts, extend_task_specify_meta_dict",
    [(TaskType.AI_SOCIETY, None, None),
     (TaskType.CODE, [dict(domain="science", language="python")] * 2,
      dict(domain="science", language="python")),
     (TaskType.MISALIGNMENT, None, None)])
def test_role_playing_step(task_type, extend_sys_msg_meta_dicts,
                           extend_task_specify_meta_dict):
    role_playing = RolePlaying(
        assistant_role_name="assistant",
        user_role_name="user",
        task_prompt="Perform the task",
        task_type=task_type,
        extend_sys_msg_meta_dicts=extend_sys_msg_meta_dicts,
        extend_task_specify_meta_dict=extend_task_specify_meta_dict,
    )
    init_assistant_msg = AssistantChatMessage(role_name="assistant",
                                              content="Hello")
    print(role_playing.assistant_agent.system_message)
    print(role_playing.user_agent.system_message)

    (assistant_msg, assistant_terminated,
     assistant_info), (user_msg, user_terminated,
                       user_info) = role_playing.step(init_assistant_msg)
    assert isinstance(assistant_msg, ChatMessage)
    assert assistant_terminated is False
    assert assistant_info is not None
    assert isinstance(user_msg, ChatMessage)
    assert user_terminated is False
    assert user_info is not None
