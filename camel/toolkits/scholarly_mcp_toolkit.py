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


class ScholarlyMCPToolkit(BaseToolkit):
    r"""ScholarlyMCPToolkit provides academic paper search across arXiv
    and Google Scholar via MCP server.

    This toolkit enables searching for academic articles, retrieving
    paper metadata, and finding scholarly publications.

    Uses the ``mcp-scholarly`` Python package.

    Example:
        async with ScholarlyMCPToolkit() as toolkit:
            tools = toolkit.get_tools()

    Attributes:
        timeout (Optional[float]): Connection timeout in seconds.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes the ScholarlyMCPToolkit.

        Args:
            timeout (Optional[float]): Connection timeout in seconds.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

        self._mcp_toolkit = MCPToolkit(
            config_dict={
                "mcpServers": {
                    "scholarly": {
                        "command": "uvx",
                        "args": ["mcp-scholarly"],
                    }
                }
            },
            timeout=timeout,
        )

    async def connect(self):
        r"""Explicitly connect to the Scholarly MCP server."""
        await self._mcp_toolkit.connect()

    async def disconnect(self):
        r"""Explicitly disconnect from the Scholarly MCP server."""
        await self._mcp_toolkit.disconnect()

    @property
    def is_connected(self) -> bool:
        r"""Check if the toolkit is connected to the MCP server."""
        return self._mcp_toolkit.is_connected

    async def __aenter__(self) -> "ScholarlyMCPToolkit":
        r"""Async context manager entry point."""
        await self.connect()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        r"""Async context manager exit point."""
        await self.disconnect()

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of tools provided by the Scholarly MCP server.

        Returns:
            List[FunctionTool]: List of available scholarly search tools.
        """
        return self._mcp_toolkit.get_tools()

    async def call_tool(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Any:
        r"""Call a Scholarly tool by name.

        Args:
            tool_name (str): Name of the tool to call.
            tool_args (Dict[str, Any]): Arguments to pass to the tool.

        Returns:
            Any: The result of the tool call.
        """
        return await self._mcp_toolkit.call_tool(tool_name, tool_args)
