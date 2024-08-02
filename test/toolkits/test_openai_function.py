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
import json
from datetime import datetime
from typing import List

import pytest
from jsonschema.exceptions import SchemaError

from camel.toolkits import OpenAIFunction, get_openai_tool_schema
from camel.types import RoleType
from camel.utils import get_pydantic_major_version


def test_get_openai_tool_schema():
    def test_all_parameters(
        any_para,
        str_para: str,
        int_para: int,
        list_para: List[int],
        float_para: float,
        datatime_para: datetime,
        *args,
        default_enum_para: RoleType = RoleType.CRITIC,
        **kwargs,
    ):
        """
        A function to test all parameter type.
        The parameters will be provided by user.
        Args:
            any_para: any_para desc. Type defaults to 'Any' if not specified.
            str_para (str) : str_para desc
            int_para (int): int_para desc
            list_para (List): list_para desc
            float_para (float): float_para desc
            datatime_para (datetime): datatime_para desc
            default_enum_para (RoleType): default_enum_para desc
        """

    # pydantic v1 follows JSON Schema Draft-07 and v2 now pin to 2020-12
    # ref: https://github.com/pydantic/pydantic/issues/4666
    expect_res_v1 = {
        'type': 'function',
        'function': {
            'name': 'test_all_parameters',
            'description': 'A function to test all parameter type.'
            '\nThe parameters will be provided by user.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'any_para': {
                        'description': "any_para desc. "
                        "Type defaults to 'Any' if not specified."
                    },
                    'str_para': {
                        'type': 'string',
                        'description': 'str_para desc',
                    },
                    'int_para': {
                        'type': 'integer',
                        'description': 'int_para desc',
                    },
                    'list_para': {
                        'type': 'array',
                        'items': {'type': 'integer'},
                        'description': 'list_para desc',
                    },
                    'float_para': {
                        'type': 'number',
                        'description': 'float_para desc',
                    },
                    'datatime_para': {
                        'type': 'string',
                        'format': 'date-time',
                        'description': 'datatime_para desc',
                    },
                    'default_enum_para': {
                        'default': 'critic',
                        'allOf': [{'$ref': '#/definitions/RoleType'}],
                        'description': 'default_enum_para desc',
                    },
                },
                'required': [
                    'str_para',
                    'int_para',
                    'list_para',
                    'float_para',
                    'datatime_para',
                ],
                'definitions': {
                    'RoleType': {
                        'description': 'An enumeration.',
                        'enum': [
                            'assistant',
                            'user',
                            'critic',
                            'embodiment',
                            'default',
                        ],
                    }
                },
            },
        },
    }
    expect_res_v2 = {
        'type': 'function',
        'function': {
            'name': 'test_all_parameters',
            'description': 'A function to test all parameter type.'
            '\nThe parameters will be provided by user.',
            'parameters': {
                '$defs': {
                    'RoleType': {
                        'enum': [
                            'assistant',
                            'user',
                            'critic',
                            'embodiment',
                            'default',
                        ],
                        'type': 'string',
                    }
                },
                'properties': {
                    'any_para': {
                        'description': "any_para desc. "
                        "Type defaults to 'Any' if not specified."
                    },
                    'str_para': {
                        'type': 'string',
                        'description': 'str_para desc',
                    },
                    'int_para': {
                        'type': 'integer',
                        'description': 'int_para desc',
                    },
                    'list_para': {
                        'items': {'type': 'integer'},
                        'type': 'array',
                        'description': 'list_para desc',
                    },
                    'float_para': {
                        'type': 'number',
                        'description': 'float_para desc',
                    },
                    'datatime_para': {
                        'format': 'date-time',
                        'type': 'string',
                        'description': 'datatime_para desc',
                    },
                    'default_enum_para': {
                        'allOf': [{'$ref': '#/$defs/RoleType'}],
                        'default': 'critic',
                        'description': 'default_enum_para desc',
                    },
                },
                'required': [
                    'any_para',
                    'str_para',
                    'int_para',
                    'list_para',
                    'float_para',
                    'datatime_para',
                ],
                'type': 'object',
            },
        },
    }

    openai_tool_schema = get_openai_tool_schema(test_all_parameters)
    pydantic_version = get_pydantic_major_version()

    if pydantic_version == 2:
        assert openai_tool_schema == expect_res_v2
    else:
        assert openai_tool_schema == expect_res_v1


def test_different_docstring_style():
    def rest_style(a: int, b: int):
        """
        Multiply two integers.

        :param int a: The multiplier in the multiplication.
        :param int b: The multiplicand in the multiplication.
        :return: The product of the two numbers.
        :rtype: int
        """
        return a * b

    def google_style(a: int, b: int):
        """
        Multiply two integers.

        Args:
            a (int): The multiplier in the multiplication.
            b (int): The multiplicand in the multiplication.

        Returns:
            int: The product of the two numbers.
        """
        return a * b

    def numpy_style(a: int, b: int):
        """
        Multiply two integers.

        Parameters
        ----------
        a : int
            The multiplier in the multiplication.
        b : int
            The multiplicand in the multiplication.

        Returns
        -------
        int
            The product of the two numbers.
        """
        return a * b

    def epydoc_style(a: int, b: int):
        """
        Multiply two integers.

        @param a: The multiplier in the multiplication.
        @type a: int
        @param b: The multiplicand in the multiplication.
        @type b: int
        @return: The product of the two numbers.
        @rtype: int
        """
        return a * b

    expect_res = json.loads("""{
        "type": "function",
        "function": {
            "name": "mul",
            "description": "Multiply two integers.",
            "parameters": {
                "properties": {
                    "a": {
                        "type": "integer",
                        "description": "The multiplier in the multiplication."
                    },
                    "b": {
                        "type": "integer",
                        "description":
                        "The multiplicand in the multiplication."
                    }
                },
                "required": ["a", "b"],
                "type": "object"
            }
        }
    }""")
    rest_style_schema = get_openai_tool_schema(rest_style)
    rest_style_schema["function"]["name"] = "mul"
    google_style_schema = get_openai_tool_schema(google_style)
    google_style_schema["function"]["name"] = "mul"
    numpy_style_schema = get_openai_tool_schema(numpy_style)
    numpy_style_schema["function"]["name"] = "mul"
    epydoc_style_schema = get_openai_tool_schema(epydoc_style)
    epydoc_style_schema["function"]["name"] = "mul"

    assert rest_style_schema == expect_res
    assert google_style_schema == expect_res
    assert numpy_style_schema == expect_res
    assert epydoc_style_schema == expect_res


def add_with_doc(a: int, b: int) -> int:
    r"""Adds two numbers.

    Args:
        a (int): The first number to be added.
        b (int): The second number to be added.

    Returns:
        integer: The sum of the two numbers.
    """
    return a + b


def add_without_doc(a: int, b: int) -> int:
    return a + b


def add_with_wrong_doc(a: int, b: int) -> int:
    r"""Adds two numbers.

    Args:
        a (int): The first number to be added.

    Returns:
        int: The sum of the two numbers.
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
                'description': 'The first number to be added.',
            },
            'b': {
                'type': 'integer',
                'description': 'The second number to be added.',
            },
        },
        'required': ['a', 'b'],
    },
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
    add = OpenAIFunction(add_with_wrong_doc)
    add.set_function_name("add")
    with pytest.raises(Exception, match="miss description of parameter \"b\""):
        _ = add.get_openai_function_schema()
    add.set_parameter("b", function_schema["parameters"]["properties"]["b"])
    assert add.get_openai_function_schema() == function_schema


def test_validate_openai_tool_schema_valid():
    OpenAIFunction.validate_openai_tool_schema(tool_schema)


def test_get_set_openai_tool_schema():
    add = OpenAIFunction(add_with_doc)
    assert add.get_openai_tool_schema() is not None
    new_schema = copy.deepcopy(tool_schema)
    new_schema["function"]["description"] = "New description"
    add.set_openai_tool_schema(new_schema)
    assert add.get_openai_tool_schema() == new_schema


def test_get_set_parameter_description():
    add = OpenAIFunction(add_with_doc)
    assert add.get_paramter_description("a") == "The first number to be added."
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
        "parameters": initial_schema["parameters"],
    }
    add.set_openai_function_schema(new_function_schema)
    assert add.get_openai_function_schema() == new_function_schema


def test_get_set_function_name():
    add = OpenAIFunction(add_with_doc)
    assert add.get_function_name() == "add_with_doc"

    add.set_function_name("new_add")
    assert add.get_function_name() == "new_add"


def test_get_set_function_description():
    add = OpenAIFunction(add_with_doc)
    initial_description = add.get_function_description()
    assert initial_description is not None

    new_description = "New description for adding numbers."
    add.set_function_description(new_description)
    assert add.get_function_description() == new_description


def test_get_set_parameter():
    add = OpenAIFunction(add_with_doc)
    initial_param_schema = add.get_parameter("a")
    assert initial_param_schema is not None

    new_param_schema = {"type": "integer", "description": "New first number"}
    add.set_parameter("a", new_param_schema)
    assert add.get_parameter("a") == new_param_schema

    with pytest.raises(KeyError):
        add.get_parameter("non_existing_param")


def test_parameters_getter_setter():
    add = OpenAIFunction(add_with_doc)
    initial_params = add.parameters
    assert initial_params is not None

    new_params = {
        "a": {"type": "integer", "description": "New first number"},
        "b": {"type": "integer", "description": "New second number"},
    }
    add.parameters = new_params
    assert add.parameters == new_params

    # Test setting invalid parameter schema
    with pytest.raises(SchemaError):
        invalid_params = {1, 2, 3}
        add.parameters = invalid_params
