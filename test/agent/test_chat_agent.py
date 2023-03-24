import os

from camel.agent import ChatAgent
from camel.configs import ChatGPTConfig
from camel.generator import SystemMessageGenerator
from camel.message import ChatMessage
from camel.typing import ModeType, RoleType

assert os.environ.get("OPENAI_API_KEY") is not None, "Missing OPENAI_API_KEY"


def test_chat_agent():
    chat_gpt_args = ChatGPTConfig()
    system_message = SystemMessageGenerator(with_task=False).from_role(
        "doctor", RoleType.ASSISTANT)
    assistant = ChatAgent(
        system_message,
        ModeType.GPT_3_5_TURBO,
        chat_gpt_args,
    )

    assert str(assistant) == (
        "ChatAgent(doctor, RoleType.ASSISTANT, ModeType.GPT_3_5_TURBO)")

    assistant.reset()
    messages, terminated, info = assistant.step(
        ChatMessage("patient", RoleType.USER, "user", "Hello!"))

    assert terminated is False
    assert messages != []
    assert info['id'] is not None

    assistant.reset()
    messages, terminated, info = assistant.step(
        ChatMessage("patient", RoleType.USER, "user", "Hello!" * 4096))

    assert terminated is True
    assert messages == []
    assert info['finish_reasons'][0] == "max_tokens_exceeded"
