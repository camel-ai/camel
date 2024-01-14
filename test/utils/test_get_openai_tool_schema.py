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
import json
from datetime import datetime
from typing import List

from camel.types import RoleType
from camel.utils import get_openai_tool_schema


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

    expect_res = {
        'type': 'function',
        'function': {
            'name': 'test_all_parameters',
            'description': 'A function to test all parameter type.'
            '\nThe parameters will be provided by user.',
            'parameters': {
                '$defs': {
                    'RoleType': {
                        'enum': [
                            'assistant', 'user', 'critic', 'embodiment',
                            'default'
                        ],
                        'type':
                        'string'
                    }
                },
                'properties': {
                    'any_para': {
                        'description':
                        "any_para desc. "
                        "Type defaults to 'Any' if not specified."
                    },
                    'str_para': {
                        'type': 'string',
                        'description': 'str_para desc'
                    },
                    'int_para': {
                        'type': 'integer',
                        'description': 'int_para desc'
                    },
                    'list_para': {
                        'items': {
                            'type': 'integer'
                        },
                        'type': 'array',
                        'description': 'list_para desc'
                    },
                    'float_para': {
                        'type': 'number',
                        'description': 'float_para desc'
                    },
                    'datatime_para': {
                        'format': 'date-time',
                        'type': 'string',
                        'description': 'datatime_para desc'
                    },
                    'default_enum_para': {
                        'allOf': [{
                            '$ref': '#/$defs/RoleType'
                        }],
                        'default': 'critic',
                        'description': 'default_enum_para desc'
                    }
                },
                'required': [
                    'any_para', 'str_para', 'int_para', 'list_para',
                    'float_para', 'datatime_para'
                ],
                'type':
                'object'
            }
        }
    }

    openai_tool_schema = get_openai_tool_schema(test_all_parameters)

    assert openai_tool_schema == expect_res


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
