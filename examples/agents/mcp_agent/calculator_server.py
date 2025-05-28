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

from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Demo")


# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    r"""Add two numbers.

    Args:
        a (int): First number to add.
        b (int): Second number to add.

    Returns:
        int: The sum of a and b.
    """
    return a + b


@mcp.tool()
def multiply(a: int, b: int) -> int:
    r"""Multiply two numbers.

    Args:
        a (int): First number to multiply.
        b (int): Second number to multiply.

    Returns:
        int: The product of a and b.
    """
    return a * b


@mcp.tool()
def compare(a: float, b: float) -> str:
    r"""Compare two numbers and determine their relationship.

    Args:
        a (float): First number to compare.
        b (float): Second number to compare.

    Returns:
        str: 'equal' if a equals b, 'greater' if a is greater than b,
            'less' if a is less than b.
    """
    if a == b:
        return "equal"
    elif a > b:
        return "greater"
    else:
        return "less"


# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    r"""Get a personalized greeting message.

    Args:
        name (str): The name to include in the greeting.

    Returns:
        str: A personalized greeting string.
    """
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run()
