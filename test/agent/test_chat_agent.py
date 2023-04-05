import os

from camel.agent import ChatAgent
from camel.configs import ChatGPTConfig
from camel.generator import SystemMessageGenerator
from camel.message import ChatMessage
from camel.typing import ModeType, RoleType, TaskType

assert os.environ.get("OPENAI_API_KEY") is not None, "Missing OPENAI_API_KEY"


def test_chat_agent():
    chat_gpt_args = ChatGPTConfig()
    system_message = SystemMessageGenerator(
        task_type=TaskType.AI_SOCIETY).from_dict(
            {"<ASSISTANT_ROLE>": "doctor"},
            role_tuple=("doctor", RoleType.ASSISTANT),
        )
    assistant = ChatAgent(
        system_message,
        ModeType.GPT_3_5_TURBO,
        chat_gpt_args,
    )

    assert str(assistant) == ("ChatAgent(doctor, "
                              "RoleType.ASSISTANT, ModeType.GPT_3_5_TURBO)")

    assistant.reset()
    user_msg = ChatMessage(role_name="Patient", role_type=RoleType.USER,
                           meta_dict=dict(), role="user", content="Hello!")
    messages, terminated, info = assistant.step(user_msg)

    assert terminated is False
    assert messages != []
    assert info['id'] is not None

    assistant.reset()
    user_msg = ChatMessage(role_name="Patient", role_type=RoleType.USER,
                           meta_dict=dict(), role="user",
                           content="Hello!" * 4096)
    messages, terminated, info = assistant.step(user_msg)

    assert terminated is True
    assert messages == []
    assert info['finish_reasons'][0] == "max_tokens_exceeded"
