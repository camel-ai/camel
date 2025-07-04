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

import json
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits import BaseToolkit, FunctionTool
from camel.utils.commons import run_async
from camel.utils.mcp_client import MCPClient, create_mcp_client

logger = get_logger(__name__)


class MCPConnectionError(Exception):
    r"""Raised when MCP connection fails."""

    pass


class MCPToolError(Exception):
    r"""Raised when MCP tool execution fails."""

    pass


class MCPToolkit(BaseToolkit):
    r"""MCPToolkit provides a unified interface for managing multiple
    MCP server connections and their tools.

    This class handles the lifecycle of multiple MCP server connections and
    offers a centralized configuration mechanism for both local and remote
    MCP services. The toolkit manages multiple :obj:`MCPClient` instances and
    aggregates their tools into a unified interface compatible with the CAMEL
    framework.

    Connection Lifecycle:
        There are three ways to manage the connection lifecycle:

        1. Using the async context manager (recommended):

           .. code-block:: python

               async with MCPToolkit(config_path="config.json") as toolkit:
                   # Toolkit is connected here
                   tools = toolkit.get_tools()
               # Toolkit is automatically disconnected here

        2. Using the factory method:

           .. code-block:: python

               toolkit = await MCPToolkit.create(config_path="config.json")
               # Toolkit is connected here
               tools = toolkit.get_tools()
               # Don't forget to disconnect when done!
               await toolkit.disconnect()

        3. Using explicit connect/disconnect:

           .. code-block:: python

               toolkit = MCPToolkit(config_path="config.json")
               await toolkit.connect()
               # Toolkit is connected here
               tools = toolkit.get_tools()
               # Don't forget to disconnect when done!
               await toolkit.disconnect()

    Note:
        Both MCPClient and MCPToolkit now use the same async context manager
        pattern for consistent connection management. MCPToolkit automatically
        manages multiple MCPClient instances using AsyncExitStack.

    Args:
        clients (Optional[List[MCPClient]], optional): List of :obj:`MCPClient`
            instances to manage. (default: :obj:`None`)
        config_path (Optional[str], optional): Path to a JSON configuration
            file defining MCP servers. The file should contain server
            configurations in the standard MCP format. (default: :obj:`None`)
        config_dict (Optional[Dict[str, Any]], optional): Dictionary containing
            MCP server configurations in the same format as the config file.
            This allows for programmatic configuration without file I/O.
            (default: :obj:`None`)
        timeout (Optional[float], optional): Timeout for connection attempts
            in seconds. This timeout applies to individual client connections.
            (default: :obj:`None`)

    Note:
        At least one of :obj:`clients`, :obj:`config_path`, or
        :obj:`config_dict` must be provided. If multiple sources are provided,
        clients from all sources will be combined.

        For web servers in the config, you can specify authorization headers
        using the "headers" field to connect to protected MCP server endpoints.

        Example configuration:

        .. code-block:: json

            {
              "mcpServers": {
                "filesystem": {
                  "command": "npx",
                  "args": ["-y", "@modelcontextprotocol/server-filesystem",
                           "/path"]
                },
                "protected-server": {
                  "url": "https://example.com/mcp",
                  "timeout": 30,
                  "headers": {
                    "Authorization": "Bearer YOUR_TOKEN",
                    "X-API-Key": "YOUR_API_KEY"
                  }
                }
              }
            }

    Attributes:
        clients (List[MCPClient]): List of :obj:`MCPClient` instances being
            managed by this toolkit.

    Raises:
        ValueError: If no configuration sources are provided or if the
            configuration is invalid.
        MCPConnectionError: If connection to any MCP server fails during
            initialization.
    """

    def __init__(
        self,
        clients: Optional[List[MCPClient]] = None,
        config_path: Optional[str] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ):
        # Call parent constructor first
        super().__init__(timeout=timeout)

        # Validate input parameters
        sources_provided = sum(
            1 for src in [clients, config_path, config_dict] if src is not None
        )
        if sources_provided == 0:
            error_msg = (
                "At least one of clients, config_path, or "
                "config_dict must be provided"
            )
            raise ValueError(error_msg)

        self.clients: List[MCPClient] = clients or []
        self._is_connected = False
        self._exit_stack: Optional[AsyncExitStack] = None

        # Load clients from config sources
        if config_path:
            self.clients.extend(self._load_clients_from_config(config_path))

        if config_dict:
            self.clients.extend(self._load_clients_from_dict(config_dict))

        if not self.clients:
            raise ValueError("No valid MCP clients could be created")

    async def connect(self) -> "MCPToolkit":
        r"""Connect to all MCP servers using AsyncExitStack.

        Establishes connections to all configured MCP servers sequentially.
        Uses :obj:`AsyncExitStack` to manage the lifecycle of all connections,
        ensuring proper cleanup on exit or error.

        Returns:
            MCPToolkit: Returns :obj:`self` for method chaining, allowing for
                fluent interface usage.

        Raises:
            MCPConnectionError: If connection to any MCP server fails. The
                error message will include details about which client failed
                to connect and the underlying error reason.

        Warning:
            If any client fails to connect, all previously established
            connections will be automatically cleaned up before raising
            the exception.

        Example:
            .. code-block:: python

                toolkit = MCPToolkit(config_dict=config)
                try:
                    await toolkit.connect()
                    # Use the toolkit
                    tools = toolkit.get_tools()
                finally:
                    await toolkit.disconnect()
        """
        if self._is_connected:
            logger.warning("MCPToolkit is already connected")
            return self

        self._exit_stack = AsyncExitStack()

        try:
            # Connect to all clients using AsyncExitStack
            for i, client in enumerate(self.clients):
                try:
                    # Use MCPClient directly as async context manager
                    await self._exit_stack.enter_async_context(client)
                    msg = f"Connected to client {i+1}/{len(self.clients)}"
                    logger.debug(msg)
                except Exception as e:
                    logger.error(f"Failed to connect to client {i+1}: {e}")
                    # AsyncExitStack will handle cleanup of already connected
                    await self._exit_stack.aclose()
                    self._exit_stack = None
                    error_msg = f"Failed to connect to client {i+1}: {e}"
                    raise MCPConnectionError(error_msg) from e

            self._is_connected = True
            msg = f"Successfully connected to {len(self.clients)} MCP servers"
            logger.info(msg)
            return self

        except Exception:
            self._is_connected = False
            if self._exit_stack:
                await self._exit_stack.aclose()
                self._exit_stack = None
            raise

    async def disconnect(self):
        r"""Disconnect from all MCP servers."""
        if not self._is_connected:
            return

        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._exit_stack = None

        self._is_connected = False
        logger.debug("Disconnected from all MCP servers")

    @property
    def is_connected(self) -> bool:
        r"""Check if toolkit is connected.

        Returns:
            bool: True if the toolkit is connected to all MCP servers,
                False otherwise.
        """
        if not self._is_connected:
            return False

        # Check if all clients are connected
        return all(client.is_connected() for client in self.clients)

    def connect_sync(self):
        r"""Synchronously connect to all MCP servers."""
        return run_async(self.connect)()

    def disconnect_sync(self):
        r"""Synchronously disconnect from all MCP servers."""
        return run_async(self.disconnect)()

    async def __aenter__(self) -> "MCPToolkit":
        r"""Async context manager entry point.

        Usage:
            async with MCPToolkit(config_dict=config) as toolkit:
                tools = toolkit.get_tools()
        """
        await self.connect()
        return self

    def __enter__(self) -> "MCPToolkit":
        r"""Synchronously enter the async context manager."""
        return run_async(self.__aenter__)()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        r"""Async context manager exit point."""
        await self.disconnect()
        return None

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        r"""Synchronously exit the async context manager."""
        return run_async(self.__aexit__)(exc_type, exc_val, exc_tb)

    @classmethod
    async def create(
        cls,
        clients: Optional[List[MCPClient]] = None,
        config_path: Optional[str] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> "MCPToolkit":
        r"""Factory method that creates and connects to all MCP servers.

        Creates a new :obj:`MCPToolkit` instance and automatically establishes
        connections to all configured MCP servers. This is a convenience method
        that combines instantiation and connection in a single call.

        Args:
            clients (Optional[List[MCPClient]], optional): List of
                :obj:`MCPClient` instances to manage. (default: :obj:`None`)
            config_path (Optional[str], optional): Path to a JSON configuration
                file defining MCP servers. (default: :obj:`None`)
            config_dict (Optional[Dict[str, Any]], optional): Dictionary
                containing MCP server configurations in the same format as the
                config file. (default: :obj:`None`)
            timeout (Optional[float], optional): Timeout for connection
                attempts in seconds. (default: :obj:`None`)

        Returns:
            MCPToolkit: A fully initialized and connected :obj:`MCPToolkit`
                instance with all servers ready for use.

        Raises:
            MCPConnectionError: If connection to any MCP server fails during
                initialization. All successfully connected servers will be
                properly disconnected before raising the exception.
            ValueError: If no configuration sources are provided or if the
                configuration is invalid.

        Example:
            .. code-block:: python

                # Create and connect in one step
                toolkit = await MCPToolkit.create(config_path="servers.json")
                try:
                    tools = toolkit.get_tools()
                    # Use the toolkit...
                finally:
                    await toolkit.disconnect()
        """
        toolkit = cls(
            clients=clients,
            config_path=config_path,
            config_dict=config_dict,
            timeout=timeout,
        )
        try:
            await toolkit.connect()
            return toolkit
        except Exception as e:
            # Ensure cleanup on initialization failure
            await toolkit.disconnect()
            logger.error(f"Failed to initialize MCPToolkit: {e}")
            raise MCPConnectionError(
                f"Failed to initialize MCPToolkit: {e}"
            ) from e

    @classmethod
    def create_sync(
        cls,
        clients: Optional[List[MCPClient]] = None,
        config_path: Optional[str] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> "MCPToolkit":
        r"""Synchronously create and connect to all MCP servers."""
        return run_async(cls.create)(
            clients, config_path, config_dict, timeout
        )

    def _load_clients_from_config(self, config_path: str) -> List[MCPClient]:
        r"""Load clients from configuration file."""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: '{config_path}'")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in config file '{config_path}': {e}"
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = f"Error reading config file '{config_path}': {e}"
            raise IOError(error_msg) from e

        return self._load_clients_from_dict(data)

    def _load_clients_from_dict(
        self, config: Dict[str, Any]
    ) -> List[MCPClient]:
        r"""Load clients from configuration dictionary."""
        if not isinstance(config, dict):
            raise ValueError("Config must be a dictionary")

        mcp_servers = config.get("mcpServers", {})
        if not isinstance(mcp_servers, dict):
            raise ValueError("'mcpServers' must be a dictionary")

        clients = []

        for name, cfg in mcp_servers.items():
            try:
                if "timeout" not in cfg and self.timeout is not None:
                    cfg["timeout"] = self.timeout

                client = self._create_client_from_config(name, cfg)
                clients.append(client)
            except Exception as e:
                logger.error(f"Failed to create client for '{name}': {e}")
                error_msg = f"Invalid configuration for server '{name}': {e}"
                raise ValueError(error_msg) from e

        return clients

    def _create_client_from_config(
        self, name: str, cfg: Dict[str, Any]
    ) -> MCPClient:
        r"""Create a single MCP client from configuration."""
        if not isinstance(cfg, dict):
            error_msg = f"Configuration for server '{name}' must be a dict"
            raise ValueError(error_msg)

        try:
            # Use the new mcp_client factory function
            # Pass timeout from toolkit if available
            kwargs = {}
            if hasattr(self, "timeout") and self.timeout is not None:
                kwargs["timeout"] = self.timeout

            client = create_mcp_client(cfg, **kwargs)
            return client
        except Exception as e:
            error_msg = f"Failed to create client for server '{name}': {e}"
            raise ValueError(error_msg) from e

    def _ensure_strict_tool_schema(self, tool: FunctionTool) -> FunctionTool:
        r"""Ensure a tool has a strict schema compatible with OpenAI's
        requirements.

        Args:
            tool (FunctionTool): The tool to check and update if necessary.

        Returns:
            FunctionTool: The tool with a strict schema.
        """
        try:
            schema = tool.get_openai_tool_schema()

            # Check if any object in the schema has additionalProperties: true
            def _has_additional_properties_true(obj):
                r"""Recursively check if any object has additionalProperties: true"""  # noqa: E501
                if isinstance(obj, dict):
                    if obj.get("additionalProperties") is True:
                        return True
                    for value in obj.values():
                        if _has_additional_properties_true(value):
                            return True
                elif isinstance(obj, list):
                    for item in obj:
                        if _has_additional_properties_true(item):
                            return True
                return False

            # FIRST: Check if the schema contains additionalProperties: true
            # This must be checked before strict mode validation
            if _has_additional_properties_true(schema):
                # Force strict mode to False and log warning
                if "function" in schema:
                    schema["function"]["strict"] = False
                tool.set_openai_tool_schema(schema)
                logger.warning(
                    f"Tool '{tool.get_function_name()}' contains "
                    f"additionalProperties: true which is incompatible with "
                    f"OpenAI strict mode. Setting strict=False for this tool."
                )
                return tool

            # SECOND: Check if the tool already has strict mode enabled
            # Only do this if there are no additionalProperties conflicts
            if schema.get("function", {}).get("strict") is True:
                return tool

            # Update the schema to be strict
            if "function" in schema:
                schema["function"]["strict"] = True

                # Ensure parameters have proper strict mode configuration
                parameters = schema["function"].get("parameters", {})
                if parameters:
                    # Ensure additionalProperties is false
                    parameters["additionalProperties"] = False

                    # Process properties to handle optional fields
                    properties = parameters.get("properties", {})
                    parameters["required"] = list(properties.keys())

                    # Apply the sanitization function from function_tool
                    from camel.toolkits.function_tool import (
                        sanitize_and_enforce_required,
                    )

                    schema = sanitize_and_enforce_required(schema)

            tool.set_openai_tool_schema(schema)
            logger.debug(
                f"Updated tool '{tool.get_function_name()}' to strict mode"
            )

        except Exception as e:
            logger.warning(f"Failed to ensure strict schema for tool: {e}")

        return tool

    def get_tools(self) -> List[FunctionTool]:
        r"""Aggregates all tools from the managed MCP client instances.

        Collects and combines tools from all connected MCP clients into a
        single unified list. Each tool is converted to a CAMEL-compatible
        :obj:`FunctionTool` that can be used with CAMEL agents. All tools
        are ensured to have strict schemas compatible with OpenAI's
        requirements.

        Returns:
            List[FunctionTool]: Combined list of all available function tools
                from all connected MCP servers with strict schemas. Returns an
                empty list if no clients are connected or if no tools are
                available.

        Note:
            This method can be called even when the toolkit is not connected,
            but it will log a warning and may return incomplete results.
            For best results, ensure the toolkit is connected before calling
            this method.

        Example:
            .. code-block:: python

                async with MCPToolkit(config_dict=config) as toolkit:
                    tools = toolkit.get_tools()
                    print(f"Available tools: {len(tools)}")
                    for tool in tools:
                        print(f"  - {tool.func.__name__}")
        """
        if not self.is_connected:
            logger.warning(
                "MCPToolkit is not connected. "
                "Tools may not be available until connected."
            )

        all_tools = []
        for i, client in enumerate(self.clients):
            try:
                client_tools = client.get_tools()

                # Ensure all tools have strict schemas
                strict_tools = []
                for tool in client_tools:
                    strict_tool = self._ensure_strict_tool_schema(tool)
                    strict_tools.append(strict_tool)

                all_tools.extend(strict_tools)
                logger.debug(
                    f"Client {i+1} contributed {len(strict_tools)} "
                    f"tools (strict mode enabled)"
                )
            except Exception as e:
                logger.error(f"Failed to get tools from client {i+1}: {e}")

        logger.info(
            f"Total tools available: {len(all_tools)} (all with strict "
            f"schemas)"
        )
        return all_tools

    def get_text_tools(self) -> str:
        r"""Returns a string containing the descriptions of the tools.

        Returns:
            str: A string containing the descriptions of all tools.
        """
        if not self.is_connected:
            logger.warning(
                "MCPToolkit is not connected. "
                "Tool descriptions may not be available until connected."
            )

        tool_descriptions = []
        for i, client in enumerate(self.clients):
            try:
                client_tools_text = client.get_text_tools()
                if client_tools_text:
                    tool_descriptions.append(
                        f"=== Client {i+1} Tools ===\n{client_tools_text}"
                    )
            except Exception as e:
                logger.error(
                    f"Failed to get tool descriptions from client {i+1}: {e}"
                )

        return "\n\n".join(tool_descriptions)

    async def call_tool(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Any:
        r"""Call a tool by name across all managed clients.

        Searches for and executes a tool with the specified name across all
        connected MCP clients. The method will try each client in sequence
        until the tool is found and successfully executed.

        Args:
            tool_name (str): Name of the tool to call. Must match a tool name
                available from one of the connected MCP servers.
            tool_args (Dict[str, Any]): Arguments to pass to the tool. The
                argument names and types must match the tool's expected
                parameters.

        Returns:
            Any: The result of the tool call. The type and structure depend
                on the specific tool being called.

        Raises:
            MCPConnectionError: If the toolkit is not connected to any MCP
                servers.
            MCPToolError: If the tool is not found in any client, or if all
                attempts to call the tool fail. The error message will include
                details about the last failure encountered.

        Example:
            .. code-block:: python

                async with MCPToolkit(config_dict=config) as toolkit:
                    # Call a file reading tool
                    result = await toolkit.call_tool(
                        "read_file",
                        {"path": "/tmp/example.txt"}
                    )
                    print(f"File contents: {result}")
        """
        if not self.is_connected:
            raise MCPConnectionError(
                "MCPToolkit is not connected. Call connect() first."
            )

        # Try to find and call the tool from any client
        last_error = None
        for i, client in enumerate(self.clients):
            try:
                # Check if this client has the tool
                tools = client.get_tools()
                tool_names = [tool.func.__name__ for tool in tools]

                if tool_name in tool_names:
                    result = await client.call_tool(tool_name, tool_args)
                    logger.debug(
                        f"Tool '{tool_name}' called successfully "
                        f"on client {i+1}"
                    )
                    return result
            except Exception as e:
                last_error = e
                logger.debug(f"Tool '{tool_name}' failed on client {i+1}: {e}")
                continue

        # If we get here, the tool wasn't found or all calls failed
        if last_error:
            raise MCPToolError(
                f"Tool '{tool_name}' failed on all clients. "
                f"Last error: {last_error}"
            ) from last_error
        else:
            raise MCPToolError(f"Tool '{tool_name}' not found in any client")

    def call_tool_sync(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        r"""Synchronously call a tool."""
        return run_async(self.call_tool)(tool_name, tool_args)

    def list_available_tools(self) -> Dict[str, List[str]]:
        r"""List all available tools organized by client.

        Returns:
            Dict[str, List[str]]: Dictionary mapping client indices to tool
                names.
        """
        available_tools = {}
        for i, client in enumerate(self.clients):
            try:
                tools = client.get_tools()
                tool_names = [tool.func.__name__ for tool in tools]
                available_tools[f"client_{i+1}"] = tool_names
            except Exception as e:
                logger.error(f"Failed to list tools from client {i+1}: {e}")
                available_tools[f"client_{i+1}"] = []

        return available_tools
