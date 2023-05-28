import pytest

from camel.agents import EmbodiedAgent, HuggingFaceToolAgent
from camel.generators import SystemMessageGenerator
from camel.messages import ChatMessage, UserChatMessage
from camel.typing import RoleType
from camel.utils import openai_api_key_required


@openai_api_key_required
def test_get_action_space_prompt():
    role_name = "Artist"
    meta_dict = dict(role=role_name, task="Drawing")
    sys_msg = SystemMessageGenerator().from_dict(
        meta_dict=meta_dict,
        role_tuple=(f"{role_name}'s Embodiment", RoleType.EMBODIMENT))
    agent = EmbodiedAgent(
        sys_msg,
        action_space=[HuggingFaceToolAgent('hugging_face_tool_agent')])
    expected_prompt = "*** hugging_face_tool_agent ***:\n"
    assert agent.get_action_space_prompt().startswith(expected_prompt)


def test_execute_code():
    code_string = "print('Hello, world!')"
    expected_output = (
        "- Python standard output:\nHello, world!\n\n- Local variables:\n{}")
    assert EmbodiedAgent.execute_code(code_string) == expected_output


def test_get_explanation_and_code():
    text_prompt = (
        "This is an explanation.\n\n```python\nprint('Hello, world!')\n```")
    expected_explanation = "This is an explanation."
    expected_code = "print('Hello, world!')"
    assert EmbodiedAgent.get_explanation_and_code(text_prompt) == (
        expected_explanation, expected_code)


@pytest.mark.slow
@pytest.mark.full_test_only
@openai_api_key_required
def test_step():
    # Create an embodied agent
    role_name = "Artist"
    meta_dict = dict(role=role_name, task="Drawing")
    sys_msg = SystemMessageGenerator().from_dict(
        meta_dict=meta_dict,
        role_tuple=(f"{role_name}'s Embodiment", RoleType.EMBODIMENT))
    embodied_agent = EmbodiedAgent(sys_msg, verbose=True)
    print(embodied_agent.system_message)
    user_msg = UserChatMessage(
        role_name=role_name,
        content="Draw all the Camelidae species.",
    )
    output_message, terminated, info = embodied_agent.step(user_msg)
    assert isinstance(output_message, ChatMessage)
    assert not terminated
    assert isinstance(info, dict)
