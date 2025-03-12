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
import inspect
import json
import os
from contextlib import AsyncExitStack, asynccontextmanager
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Union,
)
from urllib.parse import urlparse

if TYPE_CHECKING:
    from mcp import ListToolsResult, Tool

from camel.toolkits import BaseToolkit, FunctionTool


class MCPToolkit(BaseToolkit):
    r"""MCPToolkit provides an abstraction layer to interact with external
    tools using the Model Context Protocol (MCP). It supports two modes of
    connection:

    1. stdio mode: Connects via standard input/output streams for local
       command-line interactions.

    2. SSE mode (HTTP Server-Sent Events): Connects via HTTP for persistent,
       event-based interactions.

    Attributes:
        command_or_url (str): URL for SSE mode or command executable for stdio
            mode. (default: :obj:`'None'`)
        args (List[str]): List of command-line arguments if stdio mode is used.
            (default: :obj:`'None'`)
        env (Dict[str, str]): Environment variables for the stdio mode command.
            (default: :obj:`'None'`)
        timeout (Optional[float]): Connection timeout. (default: :obj:`'None'`)
    """

    def __init__(
        self,
        command_or_url: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ):
        from mcp import Tool
        from mcp.client.session import ClientSession

        super().__init__(timeout=timeout)

        self.command_or_url = command_or_url
        self.args = args or []
        self.env = env or {}

        self._mcp_tools: List[Tool] = []
        self._session: Optional['ClientSession'] = None
        self._exit_stack = AsyncExitStack()
        self._is_connected = False

    @asynccontextmanager
    async def connection(self):
        r"""Async context manager for establishing and managing the connection
        with the MCP server. Automatically selects SSE or stdio mode based
        on the provided `command_or_url`.

        Yields:
            MCPToolkit: Instance with active connection ready for tool
                interaction.
        """
        from mcp.client.session import ClientSession
        from mcp.client.sse import sse_client
        from mcp.client.stdio import StdioServerParameters, stdio_client

        try:
            if urlparse(self.command_or_url).scheme in ("http", "https"):
                (
                    read_stream,
                    write_stream,
                ) = await self._exit_stack.enter_async_context(
                    sse_client(self.command_or_url)
                )
            else:
                server_parameters = StdioServerParameters(
                    command=self.command_or_url, args=self.args, env=self.env
                )
                (
                    read_stream,
                    write_stream,
                ) = await self._exit_stack.enter_async_context(
                    stdio_client(server_parameters)
                )

            self._session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self._session.initialize()
            list_tools_result = await self.list_mcp_tools()
            self._mcp_tools = list_tools_result.tools
            self._is_connected = True
            yield self

        finally:
            self._is_connected = False
            await self._exit_stack.aclose()
            self._session = None

    async def list_mcp_tools(self) -> Union[str, "ListToolsResult"]:
        r"""Retrieves the list of available tools from the connected MCP
        server.

        Returns:
            ListToolsResult: Result containing available MCP tools.
        """
        if not self._session:
            return "MCP Client is not connected. Call `connection()` first."
        try:
            return await self._session.list_tools()
        except Exception as e:
            return f"Failed to list MCP tools: {e!s}"

    def generate_function_from_mcp_tool(self, mcp_tool: "Tool") -> Callable:
        r"""Dynamically generates a Python callable function corresponding to
        a given MCP tool.

        Args:
            mcp_tool (Tool): The MCP tool definition received from the MCP
                server.

        Returns:
            Callable: A dynamically created async Python function that wraps
                the MCP tool.
        """
        func_name = mcp_tool.name
        func_desc = mcp_tool.description or "No description provided."
        parameters_schema = mcp_tool.inputSchema.get("properties", {})
        required_params = mcp_tool.inputSchema.get("required", [])

        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        annotations = {}  # used to type hints
        defaults: Dict[str, Any] = {}  # store default values

        func_params = []
        for param_name, param_schema in parameters_schema.items():
            param_type = param_schema.get("type", "Any")
            param_type = type_map.get(param_type, Any)

            annotations[param_name] = param_type
            if param_name not in required_params:
                defaults[param_name] = None

            func_params.append(param_name)

        async def dynamic_function(**kwargs):
            r"""Auto-generated function for MCP Tool interaction.

            Args:
                kwargs: Keyword arguments corresponding to MCP tool parameters.

            Returns:
                str: The textual result returned by the MCP tool.
            """
            from mcp.types import CallToolResult

            missing_params: Set[str] = set(required_params) - set(
                kwargs.keys()
            )
            if missing_params:
                raise ValueError(
                    f"Missing required parameters: {missing_params}"
                )

            result: CallToolResult = await self._session.call_tool(
                func_name, kwargs
            )

            if not result.content:
                return "No data available for this request."

            # Handle different content types
            content = result.content[0]
            if content.type == "text":
                return content.text
            elif content.type == "image":
                # Return image URL or data URI if available
                if hasattr(content, "url") and content.url:
                    return f"Image available at: {content.url}"
                return "Image content received (data URI not shown)"
            elif content.type == "embedded_resource":
                # Return resource information if available
                if hasattr(content, "name") and content.name:
                    return f"Embedded resource: {content.name}"
                return "Embedded resource received"
            else:
                msg = f"Received content of type '{content.type}'"
                return f"{msg} which is not fully supported yet."

        dynamic_function.__name__ = func_name
        dynamic_function.__doc__ = func_desc
        dynamic_function.__annotations__ = annotations

        sig = inspect.Signature(
            parameters=[
                inspect.Parameter(
                    name=param,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                    default=defaults.get(param, inspect.Parameter.empty),
                    annotation=annotations[param],
                )
                for param in func_params
            ]
        )
        dynamic_function.__signature__ = sig  # type: ignore[attr-defined]

        return dynamic_function

    def _build_tool_schema(self, mcp_tool: "Tool") -> Dict[str, Any]:
        input_schema = mcp_tool.inputSchema
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        parameters = {
            "type": "object",
            "properties": properties,
            "required": required,
        }

        return {
            "type": "function",
            "function": {
                "name": mcp_tool.name,
                "description": mcp_tool.description
                or "No description provided.",
                "parameters": parameters,
            },
        }

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit. Each function is dynamically generated
        based on the MCP tool definitions received from the server.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(
                self.generate_function_from_mcp_tool(mcp_tool),
                openai_tool_schema=self._build_tool_schema(mcp_tool),
            )
            for mcp_tool in self._mcp_tools
        ]


class MCPToolkitManager:
    r"""MCPToolkitManager provides a unified interface for managing multiple
    MCPToolkit instances and their connections.

    This class handles the lifecycle of multiple MCP tool connections and
    offers a centralized configuration mechanism for both local and remote
    MCP services.

    Attributes:
        toolkits (List[MCPToolkit]): List of MCPToolkit instances to manage.
    """

    def __init__(self, toolkits: List[MCPToolkit]):
        self.toolkits = toolkits
        self._exit_stack: Optional[AsyncExitStack] = None
        self._connected = False

    @staticmethod
    def from_config(config_path: str) -> "MCPToolkitManager":
        r"""Creates an MCPToolkitManager from a JSON config file.

        The configuration file should define local MCP servers and/or remote
        MCP web servers with their respective parameters.

        Args:
            config_path (str): Path to the JSON configuration file.

        Returns:
            MCPToolkitManager: An initialized toolkit manager with configured
                MCPToolkit instances.

        Raises:
            FileNotFoundError: If the config file doesn't exist.
            json.JSONDecodeError: If the config file contains invalid JSON.
            ValueError: If the config is missing required fields or has invalid
                structure.

        Example:
            Example JSON configuration format:

            ```json
            {
              "mcpServers": {
                "filesystem": {
                  "command": "mcp-filesystem-server",
                  "args": ["/Users/user/Desktop", "/Users/user/Downloads"]
                },
              },
              "mcpWebServers": {
                "weather": {
                  "url": "https://example-api.ngrok-free.app/sse"
                }
              }
            }
            ```

            Each entry under "mcpServers" requires at least a "command" field.
            Each entry under "mcpWebServers" requires a "url" field.
            Optional fields include "args", "env", and "timeout".
        """
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError as e:
                    raise json.JSONDecodeError(
                        f"Invalid JSON in config file '{config_path}': {e!s}",
                        e.doc,
                        e.pos,
                    ) from e
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: '{config_path}'")

        all_toolkits = []

        # Process local MCP servers
        mcp_servers = data.get("mcpServers", {})
        if not isinstance(mcp_servers, dict):
            raise ValueError("'mcpServers' must be a dictionary")

        for name, cfg in mcp_servers.items():
            if not isinstance(cfg, dict):
                raise ValueError(
                    f"Configuration for server '{name}' must be a dictionary"
                )

            if "command" not in cfg:
                raise ValueError(
                    f"Missing required 'command' field for server '{name}'"
                )

            toolkit = MCPToolkit(
                command_or_url=cfg["command"],
                args=cfg.get("args", []),
                env={**os.environ, **cfg.get("env", {})},
                timeout=cfg.get("timeout", None),
            )
            all_toolkits.append(toolkit)

        # Process remote MCP web servers
        mcp_web_servers = data.get("mcpWebServers", {})
        if not isinstance(mcp_web_servers, dict):
            raise ValueError("'mcpWebServers' must be a dictionary")

        for name, cfg in mcp_web_servers.items():
            if not isinstance(cfg, dict):
                raise ValueError(
                    f"Configuration for web server '{name}' must"
                    "be a dictionary"
                )

            if "url" not in cfg:
                raise ValueError(
                    f"Missing required 'url' field for web server '{name}'"
                )

            toolkit = MCPToolkit(
                command_or_url=cfg["url"],
                timeout=cfg.get("timeout", None),
            )
            all_toolkits.append(toolkit)

        return MCPToolkitManager(all_toolkits)

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator["MCPToolkitManager", None]:
        r"""Async context manager that simultaneously establishes connections
        to all managed MCPToolkit instances.

        Yields:
            MCPToolkitManager: Self with all toolkits connected.
        """
        self._exit_stack = AsyncExitStack()
        try:
            # Sequentially connect to each toolkit
            for tk in self.toolkits:
                await self._exit_stack.enter_async_context(tk.connection())
            self._connected = True
            yield self
        finally:
            self._connected = False
            await self._exit_stack.aclose()
            self._exit_stack = None

    def is_connected(self) -> bool:
        r"""Checks if all the managed toolkits are connected.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self._connected

    def get_all_tools(self) -> List[FunctionTool]:
        r"""Aggregates all tools from the managed MCPToolkit instances.

        Returns:
            List[FunctionTool]: Combined list of all available function tools.
        """
        all_tools = []
        for tk in self.toolkits:
            all_tools.extend(tk.get_tools())
        return all_tools
