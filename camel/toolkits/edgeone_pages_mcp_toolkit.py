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

from typing import List, Optional

from camel.toolkits import BaseToolkit, FunctionTool

from .mcp_toolkit import MCPToolkit


class EdgeOnePagesMCPToolkit(BaseToolkit):
    r"""EdgeOnePagesMCPToolkit provides an interface for interacting with
    EdgeOne pages using the EdgeOne Pages MCP server.

    Attributes:
        timeout (Optional[float]): Connection timeout in seconds.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes the EdgeOnePagesMCPToolkit.

        Args:
            timeout (Optional[float]): Connection timeout in seconds.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

        self._mcp_toolkit = MCPToolkit(
            config_dict={
                "mcpServers": {
                    "edgeone-pages-mcp-server": {
                        "command": "npx",
                        "args": ["edgeone-pages-mcp"],
                    }
                }
            },
            timeout=timeout,
        )

    async def connect(self):
        r"""Explicitly connect to the EdgeOne Pages MCP server."""
        await self._mcp_toolkit.connect()

    async def disconnect(self):
        r"""Explicitly disconnect from the EdgeOne Pages MCP server."""
        await self._mcp_toolkit.disconnect()

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of tools provided by the EdgeOnePagesMCPToolkit.

        Returns:
            List[FunctionTool]: List of available tools.
        """
        return self._mcp_toolkit.get_tools()
