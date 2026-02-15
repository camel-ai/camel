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

from typing import Any, Dict, List, Optional

from camel.toolkits import BaseToolkit, FunctionTool

from .mcp_toolkit import MCPToolkit


class Rail12306MCPToolkit(BaseToolkit):
    r"""Rail12306MCPToolkit provides China Railway 12306 ticket query
    operations via MCP server.

    This toolkit enables querying train schedules, ticket availability,
    and station information from the China Railway 12306 system.

    Uses the ``12306-mcp`` npm package.

    Example:
        async with Rail12306MCPToolkit() as toolkit:
            tools = toolkit.get_tools()

    Attributes:
        timeout (Optional[float]): Connection timeout in seconds.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes the Rail12306MCPToolkit.

        Args:
            timeout (Optional[float]): Connection timeout in seconds.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

        self._mcp_toolkit = MCPToolkit(
            config_dict={
                "mcpServers": {
                    "12306": {
                        "command": "npx",
                        "args": ["-y", "12306-mcp"],
                    }
                }
            },
            timeout=timeout,
        )

    async def connect(self):
        r"""Explicitly connect to the 12306 MCP server."""
        await self._mcp_toolkit.connect()

    async def disconnect(self):
        r"""Explicitly disconnect from the 12306 MCP server."""
        await self._mcp_toolkit.disconnect()

    @property
    def is_connected(self) -> bool:
        r"""Check if the toolkit is connected to the MCP server."""
        return self._mcp_toolkit.is_connected

    async def __aenter__(self) -> "Rail12306MCPToolkit":
        r"""Async context manager entry point."""
        await self.connect()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        r"""Async context manager exit point."""
        await self.disconnect()

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of tools provided by the 12306 MCP server.

        Returns:
            List[FunctionTool]: List of available railway ticket tools.
        """
        return self._mcp_toolkit.get_tools()

    async def call_tool(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Any:
        r"""Call a 12306 tool by name.

        Args:
            tool_name (str): Name of the tool to call.
            tool_args (Dict[str, Any]): Arguments to pass to the tool.

        Returns:
            Any: The result of the tool call.
        """
        return await self._mcp_toolkit.call_tool(tool_name, tool_args)
