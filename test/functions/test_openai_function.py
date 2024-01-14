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
import copy

import pytest

from camel.functions import OpenAIFunction


def add_with_doc(a: int, b: int) -> int:
    r"""Adds two numbers.

    Args:
        a (integer): The first number to be added.
        b (integer): The second number to be added.

    Returns:
        integer: The sum of the two numbers.
    """
    return a + b


def add_without_doc(a: int, b: int) -> int:
    return a + b


def add_with_wrong_doc(a: int, b: int) -> int:
    r"""Adds two numbers.

    Args:
        a (integer): The first number to be added.

    Returns:
        integer: The sum of the two numbers.
    """
    return a + b


function_schema = {
    "name": "add",
    "description": "Adds two numbers.",
    "parameters": {
        'type': 'object',
        'properties': {
            'a': {
                'type': 'integer',
                'description': 'The first number to be added.'
            },
            'b': {
                'type': 'integer',
                'description': 'The second number to be added.'
            }
        },
        'required': ['a', 'b']
    }
}

tool_schema = {
    "type": "function",
    "function": function_schema,
}


def test_correct_function():
    add = OpenAIFunction(add_with_doc)
    add.set_function_name("add")
    assert add.get_openai_function_schema() == function_schema


def test_function_without_doc():
    add = OpenAIFunction(add_without_doc)
    add.set_function_name("add")
    with pytest.raises(Exception, match="miss function description"):
        _ = add.get_openai_function_schema()
    add.set_openai_function_schema(function_schema)
    assert add.get_openai_function_schema() == function_schema


def test_function_with_wrong_doc():
    from pydantic import ValidationError
    add = OpenAIFunction(add_with_wrong_doc)
    add.set_function_name("add")
    with pytest.raises(Exception, match="miss description of parameter \"b\""):
        _ = add.get_openai_function_schema()
    add.set_parameter("b", function_schema["parameters"]["properties"]["b"])
    assert add.get_openai_function_schema() == function_schema
    with pytest.raises(ValidationError):
        add.openai_tool_schema[
            "type"] = "other"  # should be defined as "function"
        _ = add.get_openai_function_schema()


def test_validate_openai_tool_schema_valid():
    OpenAIFunction.validate_openai_tool_schema(tool_schema)


def test_validate_openai_tool_schema_invalid():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        invalid_schema = copy.deepcopy(tool_schema)
        invalid_schema["function"]["name"] = 123  # Invalid type for name
        OpenAIFunction.validate_openai_tool_schema(invalid_schema)


def test_get_set_openai_tool_schema():
    add = OpenAIFunction(add_with_doc)
    assert add.get_openai_tool_schema() is not None
    new_schema = copy.deepcopy(tool_schema)
    new_schema["function"]["description"] = "New description"
    add.set_openai_tool_schema(new_schema)
    assert add.get_openai_tool_schema() == new_schema


def test_get_set_parameter_description():
    add = OpenAIFunction(add_with_doc)
    assert (
        add.get_paramter_description("a") == "The first number to be added.")
    add.set_paramter_description("a", "New description for a.")
    assert add.get_paramter_description("a") == "New description for a."


def test_get_set_parameter_description_non_existing():
    add = OpenAIFunction(add_with_doc)
    with pytest.raises(KeyError):
        add.get_paramter_description("non_existing")


def test_get_set_openai_function_schema():
    add = OpenAIFunction(add_with_doc)
    initial_schema = add.get_openai_function_schema()
    assert initial_schema is not None

    new_function_schema = {
        "name": "new_add",
        "description": "Adds two numbers in a new way.",
        "parameters": initial_schema["parameters"]
    }
    add.set_openai_function_schema(new_function_schema)
    assert add.get_openai_function_schema() == new_function_schema


def test_get_set_function_name():
    add = OpenAIFunction(add_with_doc)
    assert add.get_function_name() == "add_with_doc"

    add.set_function_name("new_add")
    assert add.get_function_name() == "new_add"
