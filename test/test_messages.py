import pytest

from camel.messages import BaseMessage, SystemMessage
from camel.typing import RoleType


@pytest.fixture
def base_message() -> BaseMessage:
    return BaseMessage(
        role_name="test_user",
        role_type=RoleType.USER,
        meta_dict={"key": "value"},
        role="user",
        content="test content",
    )


@pytest.fixture
def system_message() -> SystemMessage:
    return SystemMessage(
        role_name="test_assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="test system message",
    )


def test_base_message():
    role_name = "test_role_name"
    role_type = RoleType.USER
    meta_dict = {"key": "value"}
    role = "user"
    content = "test_content"

    message = BaseMessage(role_name=role_name, role_type=role_type,
                          meta_dict=meta_dict, role=role, content=content)

    assert message.role_name == role_name
    assert message.role_type == role_type
    assert message.meta_dict == meta_dict
    assert message.role == role
    assert message.content == content

    user_message = message.to_user_chat_message()
    assert user_message.role_name == role_name
    assert user_message.role_type == role_type
    assert user_message.meta_dict == meta_dict
    assert user_message.role == "user"
    assert user_message.content == content

    assistant_message = message.to_assistant_chat_message()
    assert assistant_message.role_name == role_name
    assert assistant_message.role_type == role_type
    assert assistant_message.meta_dict == meta_dict
    assert assistant_message.role == "assistant"
    assert assistant_message.content == content

    openai_message = message.to_openai_message()
    assert openai_message == {"role": role, "content": content}

    openai_chat_message = message.to_openai_chat_message()
    assert openai_chat_message == {"role": role, "content": content}

    openai_system_message = message.to_openai_system_message()
    assert openai_system_message == {"role": "system", "content": content}

    openai_user_message = message.to_openai_user_message()
    assert openai_user_message == {"role": "user", "content": content}

    openai_assistant_message = message.to_openai_assistant_message()
    assert openai_assistant_message == {
        "role": "assistant",
        "content": content
    }

    dictionary = message.to_dict()
    assert dictionary == {
        "role_name": role_name,
        "role_type": role_type.name,
        **(meta_dict or {}), "role": role,
        "content": content
    }


def test_system_message():
    role_name = "test_role_name"
    role_type = RoleType.USER
    meta_dict = {"key": "value"}
    content = "test_content"

    message = SystemMessage(role_name=role_name, role_type=role_type,
                            meta_dict=meta_dict, content=content)

    assert message.role_name == role_name
    assert message.role_type == role_type
    assert message.meta_dict == meta_dict
    assert message.role == "system"
    assert message.content == content

    dictionary = message.to_dict()
    assert dictionary == {
        "role_name": role_name,
        "role_type": role_type.name,
        **(meta_dict or {}), "role": "system",
        "content": content
    }


def test_base_message_to_dict(base_message: BaseMessage) -> None:
    expected_dict = {
        "role_name": "test_user",
        "role_type": "USER",
        "key": "value",
        "role": "user",
        "content": "test content",
    }
    assert base_message.to_dict() == expected_dict


def test_system_message_to_dict(system_message: SystemMessage) -> None:
    expected_dict = {
        "role_name": "test_assistant",
        "role_type": "ASSISTANT",
        "role": "system",
        "content": "test system message",
    }
    assert system_message.to_dict() == expected_dict
