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


def test_correct_function():
    add = OpenAIFunction(add_with_doc, name="add")
    assert add.as_dict() == {
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


def test_function_without_doc():
    with pytest.raises(
            ValueError,
            match="Invalid function add_without_doc: no docstring provided."):
        _ = OpenAIFunction(add_without_doc, name="add")


def test_function_with_wrong_doc():
    with pytest.raises(
            ValueError,
            match=(r"Number of parameters in function signature \(2\)"
                   r" does not match that in docstring \(1\)")):
        _ = OpenAIFunction(add_with_wrong_doc, name="add")
