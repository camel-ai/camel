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
from typing import Any, Dict

import pytest

from camel.messages import FunctionCallingMessage
from camel.types import RoleType


@pytest.fixture
def assistant_func_message() -> FunctionCallingMessage:
    role_name = "test_assistant"
    role_type = RoleType.ASSISTANT
    meta_dict = None
    content = "test function message"

    return FunctionCallingMessage(
        role_name=role_name,
        role_type=role_type,
        meta_dict=meta_dict,
        content=content,
        func_name="add",
        args={"a": "1", "b": "2"},
    )


@pytest.fixture
def function_func_message() -> FunctionCallingMessage:
    role_name = "test_function"
    role_type = RoleType.ASSISTANT
    meta_dict = None
    content = "test function message"

    return FunctionCallingMessage(
        role_name=role_name,
        role_type=role_type,
        meta_dict=meta_dict,
        content=content,
        func_name="add",
        result=3,
    )


def test_assistant_func_message(
    assistant_func_message: FunctionCallingMessage,
):
    content = "test function message"

    assert assistant_func_message.func_name == "add"
    assert assistant_func_message.args == {"a": "1", "b": "2"}

    msg_dict: Dict[str, Any]
    msg_dict = {
        "role": "assistant",
        "content": content,
        "function_call": {
            "name": "add",
            "arguments": str({"a": "1", "b": "2"}),
        },
    }
    assert assistant_func_message.to_openai_assistant_message() == msg_dict


def test_function_func_message(function_func_message: FunctionCallingMessage):
    assert function_func_message.func_name == "add"
    assert function_func_message.result == 3

    result_content = {"result": {str(3)}}
    msg_dict: Dict[str, str] = {
        "role": "function",
        "name": "add",
        "content": f'{result_content}',
    }
    assert function_func_message.to_openai_function_message() == msg_dict


def test_assistant_func_message_to_openai_function_message(
    assistant_func_message: FunctionCallingMessage,
):
    expected_msg_dict: Dict[str, str] = {
        "role": "function",
        "name": "add",
        "content": "{'result': {'None'}}",
    }

    assert (
        assistant_func_message.to_openai_function_message()
        == expected_msg_dict
    )


def test_function_func_message_to_openai_assistant_message(
    function_func_message: FunctionCallingMessage,
):
    with pytest.raises(
        ValueError,
        match=(
            "Invalid request for converting into assistant message"
            " due to missing function name or arguments."
        ),
    ):
        function_func_message.to_openai_assistant_message()
