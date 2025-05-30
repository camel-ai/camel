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
"""
Unified MCP Client

This module provides a unified interface for connecting to MCP servers
using different transport protocols (stdio, sse, streamable-http, websocket).
The client can automatically detect the transport type based on configuration.
"""

from contextlib import asynccontextmanager
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import httpx
import mcp.types as types
from pydantic import BaseModel, model_validator

try:
    from mcp.shared._httpx_utils import create_mcp_http_client
except ImportError:

    def create_mcp_http_client(
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[httpx.Timeout] = None,
        auth: Optional[httpx.Auth] = None,
    ) -> httpx.AsyncClient:
        """Fallback implementation if not available."""
        kwargs: Dict[str, Any] = {"follow_redirects": True}

        if timeout is None:
            kwargs["timeout"] = httpx.Timeout(30.0)
        else:
            kwargs["timeout"] = timeout

        if headers is not None:
            kwargs["headers"] = headers

        if auth is not None:
            kwargs["auth"] = auth

        return httpx.AsyncClient(**kwargs)


from mcp import ClientSession


class TransportType(str, Enum):
    """Supported transport types."""

    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable_http"
    WEBSOCKET = "websocket"


class ServerConfig(BaseModel):
    """
    Unified server configuration that automatically detects transport type.

    Examples:
        # STDIO server
        config = ServerConfig(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/path"]
        )

        # HTTP/SSE server
        config = ServerConfig(
            url="https://api.example.com/mcp",
            headers={"Authorization": "Bearer token"}
        )

        # WebSocket server
        config = ServerConfig(url="ws://localhost:8080/mcp")
    """

    # STDIO configuration
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    cwd: Optional[Union[str, Path]] = None

    # HTTP/WebSocket configuration
    url: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None

    # Common configuration
    timeout: float = 30.0
    encoding: str = "utf-8"

    # Advanced options
    sse_read_timeout: float = 300.0  # 5 minutes
    terminate_on_close: bool = True
    # For HTTP URLs, prefer SSE over StreamableHTTP
    prefer_sse: bool = False

    @model_validator(mode='after')
    def validate_config(self):
        """Validate that either command or url is provided."""
        if not self.command and not self.url:
            raise ValueError(
                "Either 'command' (for stdio) or 'url' "
                "(for http/websocket) must be provided"
            )

        if self.command and self.url:
            raise ValueError("Cannot specify both 'command' and 'url'")

        return self

    @property
    def transport_type(self) -> TransportType:
        """Automatically detect transport type based on configuration."""
        if self.command:
            return TransportType.STDIO
        elif self.url:
            if self.url.startswith(("ws://", "wss://")):
                return TransportType.WEBSOCKET
            elif self.url.startswith(("http://", "https://")):
                # Default to StreamableHTTP, unless user prefers SSE
                if self.prefer_sse:
                    return TransportType.SSE
                else:
                    return TransportType.STREAMABLE_HTTP
            else:
                raise ValueError(f"Unsupported URL scheme: {self.url}")
        else:
            raise ValueError("Cannot determine transport type")


class MCPClient:
    """
    Unified MCP client that automatically detects and connects to servers
    using the appropriate transport protocol.
    """

    def __init__(
        self,
        config: Union[ServerConfig, Dict[str, Any]],
        client_info: Optional[types.Implementation] = None,
    ):
        """
        Initialize the unified MCP client.

        Args:
            config: Server configuration (ServerConfig object or dict)
            client_info: Client implementation information
        """
        # Convert dict config to ServerConfig if needed
        if isinstance(config, dict):
            config = ServerConfig(**config)

        self.config = config

        # Validate transport type early (this will raise ValueError if invalid)
        _ = self.config.transport_type

        self.client_info = client_info

        self._session: Optional[ClientSession] = None
        self._tools: List[types.Tool] = []

    @property
    def transport_type(self) -> TransportType:
        """Get the detected transport type."""
        return self.config.transport_type

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[ClientSession, None]:
        """
        Connect to the MCP server and yield a ClientSession.

        Returns:
            AsyncGenerator yielding a ClientSession instance
        """
        session = None
        self._session = None
        self._tools = []

        try:
            async with self._create_transport() as streams:
                # Handle extra returns safely
                read_stream, write_stream = streams[:2]

                session = ClientSession(
                    read_stream=read_stream,
                    write_stream=write_stream,
                    client_info=self.client_info,
                )

                # Start the session's message processing loop
                async with session:
                    self._session = session

                    # Initialize the session and load tools
                    await session.initialize()
                    tools_response = await session.list_tools()
                    self._tools = (
                        tools_response.tools if tools_response else []
                    )

                    yield session
        finally:
            # Ensure cleanup happens no matter what
            self._session = None
            self._tools = []

    @asynccontextmanager
    async def _create_transport(self):
        """Create the appropriate transport based on detected type."""
        transport_type = self.config.transport_type

        if transport_type == TransportType.STDIO:
            from mcp import StdioServerParameters
            from mcp.client.stdio import stdio_client

            # Ensure command is not None for STDIO
            if not self.config.command:
                raise ValueError("Command is required for STDIO transport")

            server_params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args or [],
                env=self.config.env,
                cwd=self.config.cwd,
                encoding=self.config.encoding,
            )

            async with stdio_client(server_params) as (
                read_stream,
                write_stream,
            ):
                yield read_stream, write_stream

        elif transport_type == TransportType.SSE:
            from mcp.client.sse import sse_client

            # Ensure URL is not None for SSE
            if not self.config.url:
                raise ValueError("URL is required for SSE transport")

            async with sse_client(
                url=self.config.url,
                headers=self.config.headers,
                timeout=self.config.timeout,
                sse_read_timeout=self.config.sse_read_timeout,
                httpx_client_factory=create_mcp_http_client,
            ) as (read_stream, write_stream):
                yield read_stream, write_stream

        elif transport_type == TransportType.STREAMABLE_HTTP:
            from mcp.client.streamable_http import streamablehttp_client

            # Ensure URL is not None for StreamableHTTP
            if not self.config.url:
                raise ValueError(
                    "URL is required for StreamableHTTP transport"
                )

            async with streamablehttp_client(
                url=self.config.url,
                headers=self.config.headers,
                timeout=timedelta(seconds=self.config.timeout),
                sse_read_timeout=timedelta(
                    seconds=self.config.sse_read_timeout
                ),
                terminate_on_close=self.config.terminate_on_close,
                httpx_client_factory=create_mcp_http_client,
            ) as (read_stream, write_stream, get_session_id):
                yield read_stream, write_stream, get_session_id

        elif transport_type == TransportType.WEBSOCKET:
            from mcp.client.websocket import websocket_client

            # Ensure URL is not None for WebSocket
            if not self.config.url:
                raise ValueError("URL is required for WebSocket transport")

            async with websocket_client(url=self.config.url) as (
                read_stream,
                write_stream,
            ):
                yield read_stream, write_stream

        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")

    @property
    def session(self) -> Optional[ClientSession]:
        """Get the current session if connected."""
        return self._session

    def is_connected(self) -> bool:
        """Check if the client is currently connected."""
        return self._session is not None

    def get_tools(self):
        """
        Get available tools as CAMEL FunctionTool objects.

        Returns:
            List[FunctionTool]: List of available tools
        """
        # Delayed import to avoid circular dependency

        if not self.is_connected():
            return []

        camel_tools = []
        for tool in self._tools:
            try:
                # Convert MCP tool to CAMEL FunctionTool
                camel_tool = self._convert_mcp_tool_to_camel(tool)
                camel_tools.append(camel_tool)
            except Exception as e:
                # Log error but continue with other tools
                from camel.logger import get_logger

                logger = get_logger(__name__)
                logger.warning(f"Failed to convert tool {tool.name}: {e}")

        return camel_tools

    def _convert_mcp_tool_to_camel(self, mcp_tool: types.Tool):
        """Convert an MCP tool to a CAMEL FunctionTool."""
        # Delayed import to avoid circular dependency
        from camel.toolkits import FunctionTool

        # Create a wrapper function that calls the MCP tool
        async def tool_wrapper(**kwargs):
            if not self.is_connected():
                raise RuntimeError("Client is not connected")

            if self._session is None:
                raise RuntimeError("Client session is not available")

            # Convert kwargs to the format expected by MCP
            arguments = kwargs

            # Call the MCP tool using the correct API
            result = await self._session.call_tool(
                name=mcp_tool.name, arguments=arguments
            )

            return result

        # Set the function name to match the tool name
        tool_wrapper.__name__ = mcp_tool.name

        # Set the function docstring to include description
        if mcp_tool.description:
            tool_wrapper.__doc__ = mcp_tool.description
        else:
            tool_wrapper.__doc__ = f"MCP tool: {mcp_tool.name}"

        # Create the FunctionTool with only the func parameter
        return FunctionTool(func=tool_wrapper)

    def get_text_tools(self) -> str:
        """
        Get a text description of available tools.

        Returns:
            str: Text description of tools
        """
        if not self.is_connected():
            return "Client not connected"

        if not self._tools:
            return "No tools available"

        tool_descriptions = []
        for tool in self._tools:
            desc = tool.description or 'No description'
            description = f"- {tool.name}: {desc}"
            tool_descriptions.append(description)

        return "\n".join(tool_descriptions)

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Any:
        """
        Call a tool by name.

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Tool execution result

        Raises:
            RuntimeError: If client is not connected
            ValueError: If tool is not found
        """
        if not self.is_connected():
            raise RuntimeError("Client is not connected")

        if self._session is None:
            raise RuntimeError("Client session is not available")

        # Check if tool exists
        tool_names = [tool.name for tool in self._tools]
        if tool_name not in tool_names:
            available_tools = ', '.join(tool_names)
            raise ValueError(
                f"Tool '{tool_name}' not found. "
                f"Available tools: {available_tools}"
            )

        # Call the tool using the correct API
        result = await self._session.call_tool(
            name=tool_name, arguments=arguments
        )

        return result


def create_mcp_client(
    config: Union[Dict[str, Any], ServerConfig], **kwargs: Any
) -> MCPClient:
    """
    Create an MCP client from configuration.

    Args:
        config: Server configuration as dict or ServerConfig object
        **kwargs: Additional arguments passed to MCPClient constructor

    Returns:
        MCPClient instance

    Examples:
        # STDIO server
        client = create_mcp_client({
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
        })

        # HTTP server
        client = create_mcp_client({
            "url": "https://api.example.com/mcp",
            "headers": {"Authorization": "Bearer token"}
        })

        # WebSocket server
        client = create_mcp_client({"url": "ws://localhost:8080/mcp"})
    """
    return MCPClient(config, **kwargs)


def create_mcp_client_from_config_file(
    config_path: Union[str, Path], server_name: str, **kwargs: Any
) -> MCPClient:
    """
    Create an MCP client from a configuration file.

    Args:
        config_path: Path to configuration file (JSON)
        server_name: Name of the server in the config
        **kwargs: Additional arguments passed to MCPClient constructor

    Returns:
        MCPClient instance

    Example config file:
        {
          "mcpServers": {
            "filesystem": {
              "command": "npx",
              "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                "/path"
              ]
            },
            "remote-server": {
              "url": "https://api.example.com/mcp",
              "headers": {"Authorization": "Bearer token"}
            }
          }
        }

    Usage:
        client = create_mcp_client_from_config_file(
            "config.json", "filesystem"
        )
    """
    import json

    config_path = Path(config_path)
    with open(config_path, 'r') as f:
        config_data = json.load(f)

    servers = config_data.get("mcpServers", {})
    if server_name not in servers:
        available = list(servers.keys())
        raise ValueError(
            f"Server '{server_name}' not found in config. "
            f"Available: {available}"
        )

    server_config = servers[server_name]
    return create_mcp_client(server_config, **kwargs)
