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
import pytest

from camel.toolkits import tool, FunctionTool


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
                    "b": {"type": "integer", "description": "Second number"}
                }
            }
        }
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