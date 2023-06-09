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

from camel.messages import SystemMessage
from camel.typing import RoleType


@pytest.fixture
def system_message() -> SystemMessage:
    return SystemMessage(
        role_name="test_assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="test system message",
    )


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


def test_system_message_to_dict(system_message: SystemMessage) -> None:
    expected_dict = {
        "role_name": "test_assistant",
        "role_type": "ASSISTANT",
        "role": "system",
        "content": "test system message",
    }
    assert system_message.to_dict() == expected_dict
