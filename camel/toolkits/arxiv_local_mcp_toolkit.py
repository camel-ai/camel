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

import os
from typing import Any, Dict, List, Optional

from camel.toolkits import BaseToolkit, FunctionTool

from .mcp_toolkit import MCPToolkit


class ArxivLocalMCPToolkit(BaseToolkit):
    r"""ArxivLocalMCPToolkit provides arXiv paper search, download, and
    local storage management via MCP server.

    This toolkit enables searching for arXiv papers, downloading them
    to local storage, and reading their content. Papers are stored
    locally for offline access.

    Uses the ``arxiv-mcp-server`` Python package.

    Example:
        async with ArxivLocalMCPToolkit(
            storage_path="/path/to/storage"
        ) as toolkit:
            tools = toolkit.get_tools()

        # Default storage path is ./arxiv_local_storage
        async with ArxivLocalMCPToolkit() as toolkit:
            tools = toolkit.get_tools()

    Attributes:
        timeout (Optional[float]): Connection timeout in seconds.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes the ArxivLocalMCPToolkit.

        Args:
            storage_path (Optional[str]): Local directory for storing
                downloaded papers. Defaults to ``./arxiv_local_storage``.
                (default: :obj:`None`)
            timeout (Optional[float]): Connection timeout in seconds.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

        if storage_path is None:
            storage_path = os.path.join(os.getcwd(), "arxiv_local_storage")

        self._mcp_toolkit = MCPToolkit(
            config_dict={
                "mcpServers": {
                    "arxiv-local": {
                        "command": "uvx",
                        "args": [
                            "arxiv-mcp-server",
                            "--storage-path",
                            storage_path,
                        ],
                    }
                }
            },
            timeout=timeout,
        )

    async def connect(self):
        r"""Explicitly connect to the arXiv Local MCP server."""
        await self._mcp_toolkit.connect()

    async def disconnect(self):
        r"""Explicitly disconnect from the arXiv Local MCP server."""
        await self._mcp_toolkit.disconnect()

    @property
    def is_connected(self) -> bool:
        r"""Check if the toolkit is connected to the MCP server."""
        return self._mcp_toolkit.is_connected

    async def __aenter__(self) -> "ArxivLocalMCPToolkit":
        r"""Async context manager entry point."""
        await self.connect()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        r"""Async context manager exit point."""
        await self.disconnect()

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of tools provided by the arXiv Local MCP server.

        Returns:
            List[FunctionTool]: List of available arXiv tools.
        """
        return self._mcp_toolkit.get_tools()

    async def call_tool(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Any:
        r"""Call an arXiv Local tool by name.

        Args:
            tool_name (str): Name of the tool to call.
            tool_args (Dict[str, Any]): Arguments to pass to the tool.

        Returns:
            Any: The result of the tool call.
        """
        return await self._mcp_toolkit.call_tool(tool_name, tool_args)
