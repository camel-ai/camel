import pytest

from camel.agents import CriticAgent
from camel.messages import ChatMessage, SystemMessage
from camel.typing import RoleType
from camel.utils import openai_api_key_required


@pytest.fixture
def critic_agent() -> CriticAgent:
    return CriticAgent(
        SystemMessage(
            "critic",
            RoleType.CRITIC,
            content=("You are a critic who assists in selecting an option "
                     "and provides explanations. "
                     "Your favorite fruit is Apple. "
                     "You always have to choose an option."),
        ))


def test_flatten_options(critic_agent: CriticAgent):
    messages = [
        ChatMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=dict(),
            role="user",
            content="Apple",
        ),
        ChatMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=dict(),
            role="user",
            content="Banana",
        ),
    ]
    expected_output = (f"> Proposals from user ({str(RoleType.USER)}). "
                       "Please choose an option:\n"
                       "Option 1:\nApple\n\n"
                       "Option 2:\nBanana\n\n"
                       f"Please first enter your choice ([1-{len(messages)}]) "
                       "and then your explanation and comparison: ")
    assert critic_agent.flatten_options(messages) == expected_output


@openai_api_key_required
def test_get_option(critic_agent: CriticAgent):
    messages = [
        ChatMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=dict(),
            role="user",
            content="Apple",
        ),
        ChatMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=dict(),
            role="user",
            content="Banana",
        ),
    ]
    flatten_options = critic_agent.flatten_options(messages)
    input_message = ChatMessage(
        role_name="user",
        role_type=RoleType.USER,
        meta_dict=dict(),
        role="user",
        content=flatten_options,
    )
    assert critic_agent.options_dict == {"1": "Apple", "2": "Banana"}
    assert critic_agent.get_option(
        input_message) in critic_agent.options_dict.values()


def test_parse_critic(critic_agent: CriticAgent):
    critic_msg = ChatMessage(
        role_name="critic",
        role_type=RoleType.CRITIC,
        meta_dict=dict(),
        role="assistant",
        content="I choose option 1",
    )
    expected_output = "1"
    assert critic_agent.parse_critic(critic_msg) == expected_output


@openai_api_key_required
def test_step(critic_agent: CriticAgent):
    messages = [
        ChatMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=dict(),
            role="user",
            content="Apple",
        ),
        ChatMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=dict(),
            role="user",
            content="Banana",
        ),
    ]

    assert (critic_agent.step(messages)
            == messages[0]) or (critic_agent.step(messages) == messages[1])
