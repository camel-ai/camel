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


class WandBMCPToolkit(BaseToolkit):
    r"""WandBMCPToolkit provides Weights & Biases experiment tracking
    and visualization via MCP server.

    This toolkit enables querying W&B runs, metrics, sweeps, and
    experiment metadata for ML experiment management.

    Uses the ``wandb-mcp-server`` Python package.

    Example:
        async with WandBMCPToolkit(api_key="your-key") as toolkit:
            tools = toolkit.get_tools()

        # Or using environment variable
        # Set WANDB_API_KEY=your-key
        async with WandBMCPToolkit() as toolkit:
            tools = toolkit.get_tools()

    Environment Variables:
        WANDB_API_KEY: Weights & Biases API key for authentication.

    Attributes:
        timeout (Optional[float]): Connection timeout in seconds.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes the WandBMCPToolkit.

        Args:
            api_key (Optional[str]): W&B API key. If None, reads from
                WANDB_API_KEY environment variable.
                (default: :obj:`None`)
            timeout (Optional[float]): Connection timeout in seconds.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

        if api_key is None:
            api_key = os.getenv("WANDB_API_KEY")

        if not api_key:
            raise ValueError(
                "api_key must be provided either as a parameter or through "
                "the WANDB_API_KEY environment variable"
            )

        self._mcp_toolkit = MCPToolkit(
            config_dict={
                "mcpServers": {
                    "wandb": {
                        "command": "uvx",
                        "args": ["wandb-mcp-server"],
                        "env": {
                            "WANDB_API_KEY": api_key,
                        },
                    }
                }
            },
            timeout=timeout,
        )

    async def connect(self):
        r"""Explicitly connect to the W&B MCP server."""
        await self._mcp_toolkit.connect()

    async def disconnect(self):
        r"""Explicitly disconnect from the W&B MCP server."""
        await self._mcp_toolkit.disconnect()

    @property
    def is_connected(self) -> bool:
        r"""Check if the toolkit is connected to the MCP server."""
        return self._mcp_toolkit.is_connected

    async def __aenter__(self) -> "WandBMCPToolkit":
        r"""Async context manager entry point."""
        await self.connect()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        r"""Async context manager exit point."""
        await self.disconnect()

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of tools provided by the W&B MCP server.

        Returns:
            List[FunctionTool]: List of available W&B tools.
        """
        return self._mcp_toolkit.get_tools()

    async def call_tool(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Any:
        r"""Call a W&B tool by name.

        Args:
            tool_name (str): Name of the tool to call.
            tool_args (Dict[str, Any]): Arguments to pass to the tool.

        Returns:
            Any: The result of the tool call.
        """
        return await self._mcp_toolkit.call_tool(tool_name, tool_args)
