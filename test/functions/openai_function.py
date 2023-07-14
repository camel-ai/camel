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
from jsonschema.exceptions import SchemaError

from camel.functions import OpenAIFunction


def add_with_doc(a, b):
    """Adds two numbers

    Args:
        a (integer): number to be added
        b (integer): number to be added

    Returns:
        integer: the sum of the two numbers
    """
    return a + b


def add_without_doc(a, b):
    return a + b


def add_with_wrong_doc(a, b):
    """Adds two numbers

    Args:
        a (integer): number to be added

    Returns:
        integer: the sum of the two numbers
    """
    return a + b


def test_openai_function0():
    add = OpenAIFunction(add_with_doc, name="add")
    assert add.as_dict() == {
        "name": "add",
        "description": "Adds two numbers",
        "parameters": {
            'type': 'object',
            'properties': {
                'a': {
                    'type': 'integer',
                    'description': 'number to be added'
                },
                'b': {
                    'type': 'integer',
                    'description': 'number to be added'
                }
            },
            'required': ['a', 'b']
        }
    }


def test_openai_function1():
    add = OpenAIFunction(add_without_doc, name="add")
    assert add.as_dict() == {
        "name": "add",
        "parameters": {
            'type': 'object',
            'properties': {}
        }
    }


def test_openai_function2():
    add = OpenAIFunction(add_with_wrong_doc, name="add")
    assert add.as_dict() == {
        "name": "add",
        "parameters": {
            'type': 'object',
            'properties': {}
        }
    }


def test_openai_function3():
    parameters = {
        'type': 'object',
        'properties': {
            'a': {
                'type': 'integer',
                'description': 'An addend.'
            },
            'b': {
                'type': 'integer',
                'description': 'Another addend.'
            }
        },
        'required': ['a', 'b']
    }
    add = OpenAIFunction(add_without_doc, name="add",
                         description="A function doing '+' operation.",
                         parameters=parameters)

    assert add.as_dict() == {
        "name": "add",
        "description": "A function doing '+' operation.",
        "parameters": {
            'type': 'object',
            'properties': {
                'a': {
                    'type': 'integer',
                    'description': 'An addend.'
                },
                'b': {
                    'type': 'integer',
                    'description': 'Another addend.'
                }
            },
            'required': ['a', 'b']
        }
    }


def test_openai_function4():
    wrong_parameters = {
        'type': 'object',
        'properties': {
            'a': {
                'type': 'int',
                'description': 'An addend.'
            },
            'b': {
                'type': 'int',
                'description': 'Another addend.'
            }
        },
        'required': ['a', 'b']
    }
    with pytest.raises(SchemaError):
        _ = OpenAIFunction(add_without_doc, name="add",
                           description="A function doing '+' operation.",
                           parameters=wrong_parameters)
