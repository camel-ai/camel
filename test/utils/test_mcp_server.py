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
import asyncio
import sys
from typing import Literal

import pytest
from mcp.server import FastMCP

from camel.toolkits.mcp_toolkit import MCPClient
from camel.utils import MCPServer


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
        await asyncio.sleep(0.01)
        return len(text.split())

    def run_mcp_server(
        self, mode: Literal["stdio", "sse", "streamable-http"]
    ) -> None:
        r"""Run the MCP server in the specified mode.

        Args:
            mode (Literal["stdio", "sse", "streamable-http"]): The mode to run
                the MCP server in.
        """
        self.mcp.run(mode)


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
    async with MCPClient(
        config={
            "command": sys.executable,
            "args": [__file__, "--server"],
        }
    ) as client:
        text = "hello world"
        result = await client.call_tool(
            tool_name="reverse_text",
            arguments={"text": text},
        )
        assert len(result.content) == 1
        assert result.content[0].text == processor.reverse_text(text)

        result = await client.call_tool(
            tool_name="async_word_count",
            arguments={"text": text},
        )
        assert len(result.content) == 1
        assert int(result.content[0].text) == await processor.async_word_count(
            text
        )


if __name__ == "__main__":
    if "--server" in sys.argv:
        processor = TextProcessorForMCP()
        processor.run_mcp_server("stdio")
