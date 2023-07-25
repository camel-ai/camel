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

from typing import List

from .openai_function import OpenAIFunction


def add(a, b):
    r"""Adds two numbers

    Args:
        a (integer): number to be added
        b (integer): number to be added

    Returns:
        integer: the sum of the two numbers
    """
    return a + b


def sub(a, b):
    r"""Do subtraction between two numbers

    Args:
        a (integer): the minuend in subtraction
        b (integer): the subtrahend in subtraction

    Returns:
        integer: the result of subtracting b from a
    """
    return a - b


def mul(a, b):
    r"""Multiplies two integers

    Args:
        a (integer): the multiplier in the multiplication
        b (integer): the multiplicand in the multiplication

    Returns:
        integer: the product of the two numbers
    """
    return a * b


MATH_FUNCS: List[OpenAIFunction] = [
    OpenAIFunction(func) for func in [add, sub, mul]
]
