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

from camel.messages import BaseMessage, Content
from camel.prompts import CodePrompt, TextPrompt
from camel.types import OpenAIBackendRole, RoleType


@pytest.fixture
def base_message() -> BaseMessage:
    return BaseMessage(
        role_name="test_user",
        role_type=RoleType.USER,
        meta_dict={"key": "value"},
        content=Content(text="test content"),
    )


def test_base_message_addition_operator(base_message: BaseMessage):
    other_message = BaseMessage(
        role_name="test_user",
        role_type=RoleType.USER,
        content=Content(text="!"),
    )
    new_message = base_message + other_message
    assert new_message.content.text == "test content!"


def test_base_message_multiplication_operator(base_message: BaseMessage):
    new_message = base_message * 3
    assert new_message.content.text == "test content" * 3


def test_base_message_length_operator(base_message: BaseMessage):
    assert len(base_message) == 1


def test_base_message_contains_operator(base_message: BaseMessage):
    assert "test" in (base_message.content.text or "")
    assert "foo" not in (base_message.content.text or "")


def test_extract_text_and_code_prompts():
    base_message = BaseMessage(
        role_name="test_role_name",
        role_type=RoleType.USER,
        meta_dict=dict(),
        content=Content(
            text="This is a text prompt.\n\n"
            "```python\nprint('This is a code prompt')\n```\n"
            "This is another text prompt.\n\n"
            "```c\nprintf(\"This is another code prompt\");\n```"
        ),
    )
    text_prompts, code_prompts = base_message.extract_text_and_code_prompts()

    assert len(text_prompts) == 2
    assert isinstance(text_prompts[0], TextPrompt)
    assert isinstance(text_prompts[1], TextPrompt)
    assert text_prompts[0] == "This is a text prompt."
    assert text_prompts[1] == "This is another text prompt."

    assert len(code_prompts) == 2
    assert isinstance(code_prompts[0], CodePrompt)
    assert isinstance(code_prompts[1], CodePrompt)
    assert code_prompts[0] == "print('This is a code prompt')"
    assert code_prompts[1] == "printf(\"This is another code prompt\");"
    assert code_prompts[0].code_type == "python"
    assert code_prompts[1].code_type == "c"


def test_base_message_to_dict(base_message: BaseMessage) -> None:
    expected_dict = {
        "role_name": "test_user",
        "role_type": "user",
    }
    assert base_message.to_dict()["role_name"] == expected_dict["role_name"]
    assert (
        base_message.to_dict()["role_type"].value == expected_dict["role_type"]
    )


def test_base_message():
    role_name = "test_role_name"
    role_type = RoleType.USER
    meta_dict = {"key": "value"}
    backend_role = OpenAIBackendRole.USER
    content = "test_content"

    message = BaseMessage(
        role_name=role_name,
        role_type=role_type,
        meta_dict=meta_dict,
        content=Content(text=content),
    )

    assert message.role_name == role_name
    assert message.role_type == role_type
    assert message.meta_dict == meta_dict
    assert message.content.text == content

    openai_message = message.to_openai_message(backend_role)
    assert openai_message == {
        "role": backend_role.value,
        'content': [{'type': 'text', 'text': 'test_content'}],
    }

    openai_system_message = message.to_openai_system_message()
    assert openai_system_message == {"role": "system", "content": content}

    openai_user_message = message.to_openai_user_message()
    assert openai_user_message == {
        "role": "user",
        'content': [{'type': 'text', 'text': 'test_content'}],
    }

    openai_assistant_message = message.to_openai_assistant_message()
    assert openai_assistant_message == {
        "role": "assistant",
        'content': 'test_content',
    }

    dictionary = message.to_dict()
    assert dictionary["content"] == {
        'text': ['test_content'],
        'image_url': [],
        'image_detail': 'auto',
        'video_url': [],
        'video_detail': 'low',
        'audio_url': [],
    }
