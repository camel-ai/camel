import os

import pytest

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.generators import SystemMessageGenerator
from camel.messages import ChatMessage
from camel.typing import ModelType, RoleType, TaskType
from camel.utils import get_model_token_limit


# TODO: add ModelType.GPT_4_32k to parametrization
@pytest.mark.parametrize(
    'model', [ModelType.GPT_3_5_TURBO, ModelType.GPT_4])
def test_chat_agent(model):
    assert os.environ.get(
        "OPENAI_API_KEY") is not None, "Missing OPENAI_API_KEY"

    model_config = ChatGPTConfig()
    system_message = SystemMessageGenerator(
        task_type=TaskType.AI_SOCIETY).from_dict(
            {"<ASSISTANT_ROLE>": "doctor"},
            role_tuple=("doctor", RoleType.ASSISTANT),
        )
    assistant = ChatAgent(system_message, model=model,
                          model_config=model_config)

    assert str(assistant) == ("ChatAgent(doctor, "
                              f"RoleType.ASSISTANT, {str(model)})")

    assistant.reset()
    user_msg = ChatMessage(role_name="Patient", role_type=RoleType.USER,
                           meta_dict=dict(), role="user", content="Hello!")
    messages, terminated, info = assistant.step(user_msg)

    assert terminated is False
    assert messages != []
    assert info['id'] is not None

    assistant.reset()
    token_limit = get_model_token_limit(model)
    user_msg = ChatMessage(role_name="Patient", role_type=RoleType.USER,
                           meta_dict=dict(), role="user",
                           content="token" * (token_limit + 1))
    messages, terminated, info = assistant.step(user_msg)

    assert terminated is True
    assert messages == []
    assert info['finish_reasons'][0] == "max_tokens_exceeded"
