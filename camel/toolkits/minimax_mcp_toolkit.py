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

import os
from typing import Any, Dict, List, Optional

from camel.toolkits import BaseToolkit, FunctionTool

from .mcp_toolkit import MCPToolkit


class MinimaxMCPToolkit(BaseToolkit):
    r"""MinimaxMCPToolkit provides an interface for interacting with
    MiniMax AI services using the MiniMax MCP server.

    This toolkit enables access to MiniMax's multimedia generation
    capabilities including text-to-audio, voice cloning, video generation,
    image generation, music generation, and voice design.

    This toolkit can be used as an async context manager for automatic
    connection management:

        # Using explicit API key
        async with MinimaxMCPToolkit(api_key="your-key") as toolkit:
            tools = toolkit.get_tools()
            # Toolkit is automatically disconnected when exiting

        # Using environment variables (recommended for security)
        # Set MINIMAX_API_KEY=your-key in environment
        async with MinimaxMCPToolkit() as toolkit:
            tools = toolkit.get_tools()

    Environment Variables:
        MINIMAX_API_KEY: MiniMax API key for authentication
        MINIMAX_API_HOST: API host URL (default: https://api.minimax.io)
        MINIMAX_MCP_BASE_PATH: Base path for output files

    Attributes:
        timeout (Optional[float]): Connection timeout in seconds.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_host: str = "https://api.minimax.io",
        base_path: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes the MinimaxMCPToolkit.

        Args:
            api_key (Optional[str]): MiniMax API key for authentication.
                If None, will attempt to read from MINIMAX_API_KEY
                environment variable. (default: :obj:`None`)
            api_host (str): MiniMax API host URL. Can be either
                "https://api.minimax.io" (global) or
                "https://api.minimaxi.com" (mainland China).
                Can also be read from MINIMAX_API_HOST environment variable.
                (default: :obj:`"https://api.minimax.io"`)
            base_path (Optional[str]): Base path for output files.
                If None, uses current working directory. Can also be read
                from MINIMAX_MCP_BASE_PATH environment variable.
                (default: :obj:`None`)
            timeout (Optional[float]): Connection timeout in seconds.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

        # Read API key from parameter or environment variable
        if api_key is None:
            api_key = os.getenv("MINIMAX_API_KEY")

        if not api_key:
            raise ValueError(
                "api_key must be provided either as a parameter or through "
                "the MINIMAX_API_KEY environment variable"
            )

        # Read API host from environment variable if not overridden
        env_api_host = os.getenv("MINIMAX_API_HOST")
        if env_api_host:
            api_host = env_api_host

        # Read base path from environment variable if not provided
        if base_path is None:
            base_path = os.getenv("MINIMAX_MCP_BASE_PATH")

        # Set up environment variables for the MCP server
        env = {
            "MINIMAX_API_KEY": api_key,
            "MINIMAX_API_HOST": api_host,
        }

        if base_path:
            env["MINIMAX_MCP_BASE_PATH"] = base_path

        self._mcp_toolkit = MCPToolkit(
            config_dict={
                "mcpServers": {
                    "minimax": {
                        "command": "uvx",
                        "args": ["minimax-mcp", "-y"],
                        "env": env,
                    }
                }
            },
            timeout=timeout,
        )

    async def connect(self):
        r"""Explicitly connect to the MiniMax MCP server."""
        await self._mcp_toolkit.connect()

    async def disconnect(self):
        r"""Explicitly disconnect from the MiniMax MCP server."""
        await self._mcp_toolkit.disconnect()

    @property
    def is_connected(self) -> bool:
        r"""Check if the toolkit is connected to the MCP server.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self._mcp_toolkit.is_connected

    async def __aenter__(self) -> "MinimaxMCPToolkit":
        r"""Async context manager entry point.

        Returns:
            MinimaxMCPToolkit: The connected toolkit instance.

        Example:
            async with MinimaxMCPToolkit(api_key="your-key") as toolkit:
                tools = toolkit.get_tools()
        """
        await self.connect()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        r"""Async context manager exit point.

        Automatically disconnects from the MiniMax MCP server.
        """
        await self.disconnect()

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of tools provided by the MiniMax MCP server.

        This includes tools for:
        - Text-to-audio conversion
        - Voice cloning
        - Video generation
        - Image generation
        - Music generation
        - Voice design

        Returns:
            List[FunctionTool]: List of available MiniMax AI tools.
        """
        return self._mcp_toolkit.get_tools()

    def get_text_tools(self) -> str:
        r"""Returns a string containing the descriptions of the tools.

        Returns:
            str: A string containing the descriptions of all MiniMax tools.
        """
        return self._mcp_toolkit.get_text_tools()

    async def call_tool(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Any:
        r"""Call a MiniMax tool by name.

        Args:
            tool_name (str): Name of the tool to call.
            tool_args (Dict[str, Any]): Arguments to pass to the tool.

        Returns:
            Any: The result of the tool call.
        """
        return await self._mcp_toolkit.call_tool(tool_name, tool_args)
