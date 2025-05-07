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
import sys
from typing import TYPE_CHECKING

import pytest
from mcp.server import FastMCP

from camel.utils import MCPServer

if TYPE_CHECKING:
    pass


@MCPServer(
    server_name="TextProcessorForMCP",
    function_names=["reverse_text", "async_word_count"],
)
class TextProcessorForMCP:
    mcp: FastMCP

    def __init__(self):
        pass

    def reverse_text(self, text: str) -> str:
        r"""reverse the text. the function is a synchronous function.

        Args:
            text (str): the text to reverse
        """
        return text[::-1]

    async def async_word_count(self, text: str) -> int:
        r"""count the number of words in the text. the function is an
        asynchronous function.

        Args:
            text (str): the text to count the number of words
        """
        return len(text.split())


def test_tool_schema():
    processor = TextProcessorForMCP()
    tools = processor.mcp._tool_manager.list_tools()
    tool_functions = {tool.name: tool for tool in tools}

    assert "reverse_text" in tool_functions
    tool1 = tool_functions["reverse_text"]
    assert tool1.name == "reverse_text"
    assert tool1.description.startswith(
        "reverse the text. the function is a synchronous function."
    )
    assert "text" in tool1.parameters.get("properties", {})
    assert "text" in tool1.parameters.get("required", [])
    assert not tool1.is_async

    assert "async_word_count" in tool_functions
    tool2 = tool_functions["async_word_count"]
    assert tool2.name == "async_word_count"
    assert tool2.description.startswith(
        "count the number of words in the text. the function is an"
    )
    assert "text" in tool2.parameters.get("properties", {})
    assert "text" in tool2.parameters.get("required", [])
    assert tool2.is_async


@pytest.mark.asyncio
async def test_async_word_count():
    processor = TextProcessorForMCP()

    text = "hello world"

    # Access tools via the tool_manager
    tool_manager = processor.mcp._tool_manager
    reverse_text_tool = tool_manager.get_tool("reverse_text")
    async_word_count_tool = tool_manager.get_tool("async_word_count")

    # Call reverse_text directly via its .fn attribute
    # The .fn attribute on ToolDefinition holds the actual callable
    reversed_text_output = reverse_text_tool.fn(text=text)
    assert reversed_text_output == processor.reverse_text(text)

    # Call async_word_count directly via its .fn attribute
    word_count_output = await async_word_count_tool.fn(text=text)
    assert word_count_output == await processor.async_word_count(text)


if __name__ == "__main__":
    if "--server" in sys.argv:
        processor = TextProcessorForMCP()
        processor.mcp.run("stdio")
