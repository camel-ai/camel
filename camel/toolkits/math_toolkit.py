# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import warnings
from typing import List

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer


@MCPServer()
class MathToolkit(BaseToolkit):
    r"""A class representing a toolkit for mathematical operations.

    This class provides methods for basic mathematical operations such as
    addition, subtraction, multiplication, division, and rounding.
    """

    def math_add(self, a: float, b: float) -> float:
        r"""Adds two numbers.

        Args:
            a (float): The first number to be added.
            b (float): The second number to be added.

        Returns:
            float: The sum of the two numbers.
        """
        return a + b

    def math_subtract(self, a: float, b: float) -> float:
        r"""Do subtraction between two numbers.

        Args:
            a (float): The minuend in subtraction.
            b (float): The subtrahend in subtraction.

        Returns:
            float: The result of subtracting :obj:`b` from :obj:`a`.
        """
        return a - b

    def math_multiply(
        self, a: float, b: float, decimal_places: int = 2
    ) -> float:
        r"""Multiplies two numbers.

        Args:
            a (float): The multiplier in the multiplication.
            b (float): The multiplicand in the multiplication.
            decimal_places (int, optional): The number of decimal
                places to round to. Defaults to 2.

        Returns:
            float: The product of the two numbers.
        """
        return round(a * b, decimal_places)

    def math_divide(
        self, a: float, b: float, decimal_places: int = 2
    ) -> float:
        r"""Divides two numbers.

        Args:
            a (float): The dividend in the division.
            b (float): The divisor in the division.
            decimal_places (int, optional): The number of
                decimal places to round to. Defaults to 2.

        Returns:
            float: The result of dividing :obj:`a` by :obj:`b`.
        """
        return round(a / b, decimal_places)

    def math_round(self, a: float, decimal_places: int = 0) -> float:
        r"""Rounds a number to a specified number of decimal places.

        Args:
            a (float): The number to be rounded.
            decimal_places (int, optional): The number of decimal places
                to round to. Defaults to 0.

        Returns:
            float: The rounded number.
        """
        return round(a, decimal_places)

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.math_add),
            FunctionTool(self.math_subtract),
            FunctionTool(self.math_multiply),
            FunctionTool(self.math_divide),
            FunctionTool(self.math_round),
        ]

    # Deprecated method aliases for backward compatibility
    def add(self, *args, **kwargs):
        r"""Deprecated: Use math_add instead."""
        warnings.warn(
            "add is deprecated. Use math_add instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.math_add(*args, **kwargs)

    def sub(self, *args, **kwargs):
        r"""Deprecated: Use math_subtract instead."""
        warnings.warn(
            "sub is deprecated. Use math_subtract instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.math_subtract(*args, **kwargs)

    def multiply(self, *args, **kwargs):
        r"""Deprecated: Use math_multiply instead."""
        warnings.warn(
            "multiply is deprecated. Use math_multiply instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.math_multiply(*args, **kwargs)

    def divide(self, *args, **kwargs):
        r"""Deprecated: Use math_divide instead."""
        warnings.warn(
            "divide is deprecated. Use math_divide instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.math_divide(*args, **kwargs)

    def round(self, *args, **kwargs):
        r"""Deprecated: Use math_round instead. Note: This was shadowing
        Python's built-in round().
        """
        warnings.warn(
            "round is deprecated. Use math_round instead. This was "
            "shadowing Python's built-in round().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.math_round(*args, **kwargs)
