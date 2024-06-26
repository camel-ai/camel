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

from camel.toolkits.base import BaseToolkit
from camel.toolkits.openai_function import OpenAIFunction


class MathToolkit(BaseToolkit):
    r"""A class representing a toolkit for mathematical operations.

    This class provides methods for basic mathematical operations such as
    addition, subtraction, and multiplication.
    """

    def add(self, a: int, b: int) -> int:
        r"""Adds two numbers.

        Args:
            a (int): The first number to be added.
            b (int): The second number to be added.

        Returns:
            integer: The sum of the two numbers.
        """
        return a + b

    def sub(self, a: int, b: int) -> int:
        r"""Do subtraction between two numbers.

        Args:
            a (int): The minuend in subtraction.
            b (int): The subtrahend in subtraction.

        Returns:
            integer: The result of subtracting :obj:`b` from :obj:`a`.
        """
        return a - b

    def mul(self, a: int, b: int) -> int:
        r"""Multiplies two integers.

        Args:
            a (int): The multiplier in the multiplication.
            b (int): The multiplicand in the multiplication.

        Returns:
            integer: The product of the two numbers.
        """
        return a * b

    def get_tools(self) -> List[OpenAIFunction]:
        r"""Returns a list of OpenAIFunction objects representing the
        functions in the toolkit.

        Returns:
            List[OpenAIFunction]: A list of OpenAIFunction objects
                representing the functions in the toolkit.
        """
        return [
            OpenAIFunction(self.add),
            OpenAIFunction(self.sub),
            OpenAIFunction(self.mul),
        ]


MATH_FUNCS: List[OpenAIFunction] = MathToolkit().get_tools()
