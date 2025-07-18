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

from camel.toolkits import BaseToolkit, FunctionTool, MCPToolkit


class OrigeneToolkit(BaseToolkit):
    r"""OrigeneToolkit provides an interface for interacting with
    Origene MCP server.

    This toolkit can be used as an async context manager for automatic
    connection management:

        async with OrigeneToolkit(tool_packages=["chembl", "kegg"]) as toolkit:
            tools = toolkit.get_tools()
            # Toolkit is automatically disconnected when exiting

    Attributes:
        config_dict (Dict): Configuration dictionary for MCP servers.
        timeout (Optional[float]): Connection timeout in seconds.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        tool_packages: List[str] = [
            "chembl",
            "kegg",
            "string",
            "search",
            "pubchem",
            "ncbi",
            "uniprot",
            "tcga",
            "ensembl",
            "ucsc",
            "fda_drug",
            "pdb",
            "monarch",
            "clinicaltrials",
            "dbsearch",
            "opentargets",
        ],
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes the OrigeneToolkit.

        Args:
            tool_packages (Optional[Dict]): Configuration dictionary for MCP
                servers. If None, uses default configuration for chembl_mcp.
                (default: :obj:`None`)
            timeout (Optional[float]): Connection timeout in seconds.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

        self._mcp_toolkit = MCPToolkit(
            config_dict={
                "mcpServers": {
                package: {
                    "transport": "streamable_http",
                        "url": f"http://127.0.0.1:8788/{package}/mcp/",
                    }
                    for package in tool_packages
                }
            },
            timeout=timeout,
        )

    async def connect(self):
        r"""Explicitly connect to the Origene MCP server."""
        await self._mcp_toolkit.connect()

    async def disconnect(self):
        r"""Explicitly disconnect from the Origene MCP server."""
        await self._mcp_toolkit.disconnect()

    async def __aenter__(self) -> "OrigeneToolkit":
        r"""Async context manager entry point.

        Returns:
            OrigeneToolkit: The connected toolkit instance.

        Example:
            async with OrigeneToolkit(config_dict=config) as toolkit:
                tools = toolkit.get_tools()
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        r"""Async context manager exit point.

        Automatically disconnects from the Origene MCP server.
        """
        await self.disconnect()
        return None

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of tools provided by the Origene MCP server.

        Returns:
            List[FunctionTool]: List of available tools.
        """
        return self._mcp_toolkit.get_tools()
