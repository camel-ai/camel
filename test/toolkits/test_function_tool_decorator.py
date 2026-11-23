# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
import pytest

from camel.toolkits import FunctionTool, tool
from camel.toolkits.function_tool import _coerce_arg


@tool()
def add(
    a: int,
    b: int = 0,
) -> int:
    r"""Add two numbers and return their sum.

    Args:
        a (int): The first number to add.
        b (int, optional): The second number to add.
            (default: :obj:`0`)

    Returns:
        int: The sum of the two numbers.
    """
    return a + b


@tool(synthesize_output=True)
def format_result(
    result: int,
) -> str:
    r"""Format the calculation result.

    Args:
        result (int): The number to format.

    Returns:
        str: A formatted string.
    """
    return f"Result: {result}"


def test_basic_tool_decorator():
    r"""Test basic functionality of the tool decorator."""
    assert isinstance(add, FunctionTool)

    assert add(1, 2) == 3
    assert add(5) == 5


def test_tool_schema_generation():
    r"""Test schema generation of the decorated function."""
    schema = add.get_openai_tool_schema()

    assert schema["type"] == "function"
    assert "function" in schema

    func_schema = schema["function"]
    assert func_schema["name"] == "add"
    assert "description" in func_schema
    assert "parameters" in func_schema

    params = func_schema["parameters"]
    assert "properties" in params
    assert "a" in params["properties"]
    assert "b" in params["properties"]
    assert params["properties"]["a"]["type"] == "integer"
    assert "description" in params["properties"]["a"]


def test_tool_with_synthesis():
    r"""Test the tool decorator with output synthesis enabled."""
    assert format_result.synthesize_output is True

    result = format_result(42)
    assert isinstance(result, str)
    assert "42" in result


def test_tool_without_parentheses():
    r"""Test the tool decorator without parentheses (@tool instead of
    @tool()).
    """

    @tool
    def subtract(a: int, b: int = 0) -> int:
        r"""Subtract two numbers.

        Args:
            a (int): The first number.
            b (int, optional): The number to subtract. (default: :obj:`0`)

        Returns:
            int: The difference.
        """
        return a - b

    assert isinstance(subtract, FunctionTool)
    assert subtract(5, 3) == 2
    assert subtract(10) == 10

    schema = subtract.get_openai_tool_schema()
    assert schema["function"]["name"] == "subtract"


def test_coerce_scalar_string_arguments():
    r"""Test that string arguments are coerced to scalar annotations.

    LLM providers may emit numeric/boolean tool-call arguments as JSON
    strings (e.g. ``"42"``, ``"true"``) even when the declared schema says
    ``integer``/``boolean``. Those parseable strings should be coerced to
    the annotated scalar type so downstream arithmetic works.
    """
    assert _coerce_arg("42", int) == 42
    assert _coerce_arg("3.14", float) == 3.14
    assert _coerce_arg("true", bool) is True
    assert _coerce_arg("false", bool) is False
    assert _coerce_arg("TRUE", bool) is True
    assert _coerce_arg("1", bool) is True
    assert _coerce_arg("0", bool) is False


def test_coerce_scalar_unparsable_passes_through():
    r"""Test that unparsable or already-typed values pass through
    unchanged.
    """
    # Unparsable string forms stay as strings (preserving error surfacing).
    assert _coerce_arg("abc", int) == "abc"
    assert _coerce_arg("not-a-number", float) == "not-a-number"
    # Already correctly typed values are left untouched.
    assert _coerce_arg(42, int) == 42
    assert _coerce_arg(42.0, float) == 42.0
    assert _coerce_arg(True, bool) is True
    # Non-scalar annotations (e.g. str) are unaffected.
    assert _coerce_arg("hello", str) == "hello"


def test_tool_scalar_string_arguments_execute():
    r"""Test end-to-end scalar coercion through a decorated FunctionTool."""

    @tool
    def compute_total(
        quantity: int, price: float, tax_included: bool
    ) -> float:
        r"""Compute a total, multiplying quantity and price.

        Args:
            quantity (int): The number of items.
            price (float): The unit price.
            tax_included (bool): Whether tax is already included.

        Returns:
            float: The computed total.
        """
        if tax_included:
            return quantity * price
        return quantity * price * 1.1

    assert compute_total("42", "10.5", "true") == 441.0


def test_custom_schema():
    r"""Test the tool decorator with custom schema."""
    custom_schema = {
        "type": "function",
        "function": {
            "name": "custom_add",
            "description": "Custom add function",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "integer", "description": "First number"},
                    "b": {"type": "integer", "description": "Second number"},
                },
            },
        },
    }

    @tool(openai_tool_schema=custom_schema)
    def custom_add(a: int, b: int = 0) -> int:
        r"""Custom add function."""
        return a + b

    schema = custom_add.get_openai_tool_schema()
    assert schema["function"]["name"] == "custom_add"
    assert schema["function"]["description"] == "Custom add function"


if __name__ == "__main__":
    pytest.main([__file__])
