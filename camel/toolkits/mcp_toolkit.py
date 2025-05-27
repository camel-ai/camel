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
import asyncio
import inspect
import json
import os
import shlex
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import timedelta
from enum import Enum
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
    from mcp import ClientSession, ListToolsResult, Tool


from camel.logger import get_logger
from camel.toolkits import BaseToolkit, FunctionTool
from camel.utils.commons import run_async

logger = get_logger(__name__)


class ConnectionMode(Enum):
    r"""Enumeration of supported connection modes."""

    SSE = "sse"
    STREAMABLE_HTTP = "streamable-http"
    STDIO = "stdio"


class MCPConnectionError(Exception):
    r"""Raised when MCP connection fails."""

    pass


class MCPToolError(Exception):
    r"""Raised when MCP tool execution fails."""

    pass


class ConnectionState(Enum):
    r"""Connection state enumeration for better state management."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    FAILED = "failed"


class MCPClient(BaseToolkit):
    r"""Internal class that provides an abstraction layer to interact with
    external tools using the Model Context Protocol (MCP). It supports three
    modes of connection:

    1. stdio mode: Connects via standard input/output streams for local
       command-line interactions.

    2. SSE mode (HTTP Server-Sent Events): Connects via HTTP for persistent,
       event-based interactions.

    3. streamable-http mode: Connects via HTTP for persistent, streamable
        interactions.

    Connection Lifecycle:
        There are three ways to manage the connection lifecycle:

        1. Using the async context manager:
           ```python
           async with MCPClient(command_or_url="...") as client:
               # Client is connected here
               result = await client.some_tool()
           # Client is automatically disconnected here
           ```

        2. Using the factory method:
           ```python
           client = await MCPClient.create(command_or_url="...")
           # Client is connected here
           result = await client.some_tool()
           # Don't forget to disconnect when done!
           await client.disconnect()
           ```

        3. Using explicit connect/disconnect:
           ```python
           client = MCPClient(command_or_url="...")
           await client.connect()
           # Client is connected here
           result = await client.some_tool()
           # Don't forget to disconnect when done!
           await client.disconnect()
           ```

    Attributes:
        command_or_url (str): URL for SSE mode or command executable for stdio
            mode. (default: :obj:`None`)
        args (List[str]): List of command-line arguments if stdio mode is used.
            (default: :obj:`None`)
        env (Dict[str, str]): Environment variables for the stdio mode command.
            (default: :obj:`None`)
        timeout (Optional[float]): Connection timeout.
            (default: :obj:`None`)
        headers (Dict[str, str]): Headers for the HTTP request.
            (default: :obj:`None`)
        mode (Optional[str]): Connection mode. Can be "sse" for Server-Sent
            Events, "streamable-http" for streaming HTTP,
            or None for stdio mode.
            (default: :obj:`None`)
        strict (Optional[bool]): Whether to enforce strict mode for the
            function call. (default: :obj:`False`)
    """

    def __init__(
        self,
        command_or_url: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        mode: Optional[str] = None,
        strict: Optional[bool] = False,
    ):
        from mcp import Tool

        super().__init__(timeout=timeout)

        self.command_or_url = command_or_url
        self.args = args or []
        self.env = env or {}
        self.headers = headers or {}
        self.strict = strict
        self.mode = mode

        # Validate mode if provided
        if mode and mode not in [m.value for m in ConnectionMode]:
            valid_modes = [m.value for m in ConnectionMode]
            error_msg = f"Invalid mode '{mode}'. Must be one of: {valid_modes}"
            raise ValueError(error_msg)

        self._mcp_tools: List[Tool] = []
        self._session: Optional['ClientSession'] = None
        self._exit_stack: Optional[AsyncExitStack] = None
        self._connection_state = ConnectionState.DISCONNECTED
        self._connection_lock = asyncio.Lock()

        # Track cleanup tasks for better resource management
        self._cleanup_tasks: List[Callable] = []

    @property
    def is_connected(self) -> bool:
        r"""Check if client is currently connected."""
        return self._connection_state == ConnectionState.CONNECTED

    @property
    def connection_state(self) -> ConnectionState:
        r"""Get current connection state."""
        return self._connection_state

    async def connect(self):
        r"""Explicitly connect to the MCP server.

        Returns:
            MCPClient: The client used to connect to the server.
        """
        async with self._connection_lock:
            if self._connection_state == ConnectionState.CONNECTED:
                logger.warning("Server is already connected")
                return self

            if self._connection_state == ConnectionState.CONNECTING:
                raise MCPConnectionError("Connection already in progress")

            self._connection_state = ConnectionState.CONNECTING

            try:
                # Initialize fresh resources
                await self._ensure_clean_state()

                # Establish connection
                await self._establish_connection()
                await self._initialize_session()
                await self._load_tools()

                self._connection_state = ConnectionState.CONNECTED
                msg = (
                    f"Successfully connected to MCP server: "
                    f"{self.command_or_url}"
                )
                logger.info(msg)
                return self

            except Exception as e:
                self._connection_state = ConnectionState.FAILED
                error_msg = (
                    f"Failed to connect to MCP server "
                    f"'{self.command_or_url}': {e}"
                )
                logger.error(error_msg)

                # Ensure cleanup on failure
                await self._force_cleanup()
                raise MCPConnectionError(f"Connection failed: {e}") from e

    async def _ensure_clean_state(self):
        r"""Ensure clean initial state."""
        if self._exit_stack is not None:
            await self._safe_cleanup_exit_stack()

        # Create new exit stack
        self._exit_stack = AsyncExitStack()

        # Clear other state
        self._session = None
        self._cleanup_tasks.clear()

    async def _establish_connection(self):
        r"""Establish the underlying connection based on URL scheme."""
        parsed_url = urlparse(self.command_or_url)

        if parsed_url.scheme in ("http", "https"):
            await self._establish_http_connection(parsed_url)
        else:
            await self._establish_stdio_connection()

    async def _establish_http_connection(self, parsed_url):
        r"""Establish HTTP-based connection (SSE or streamable-http)."""
        from mcp.client.sse import sse_client
        from mcp.client.streamable_http import streamablehttp_client

        # Default to SSE for HTTP URLs if no mode specified
        connection_mode = self.mode or ConnectionMode.SSE.value

        if connection_mode == ConnectionMode.SSE.value:
            streams = await self._exit_stack.enter_async_context(
                sse_client(
                    self.command_or_url,
                    headers=self.headers,
                    timeout=self.timeout,
                )
            )
            read_stream, write_stream = streams
        elif connection_mode == ConnectionMode.STREAMABLE_HTTP.value:
            # Handle timeout conversion safely
            timeout_delta = None
            if self.timeout is not None:
                timeout_delta = timedelta(seconds=self.timeout)

            streams = await self._exit_stack.enter_async_context(
                streamablehttp_client(
                    self.command_or_url,
                    headers=self.headers,
                    timeout=timeout_delta,
                )
            )
            read_stream, write_stream = streams[0], streams[1]
        else:
            error_msg = f"Invalid mode '{connection_mode}' for HTTP URL"
            raise ValueError(error_msg)

        self._read_stream = read_stream
        self._write_stream = write_stream

    async def _establish_stdio_connection(self):
        r"""Establish stdio-based connection."""
        from mcp.client.stdio import StdioServerParameters, stdio_client

        command = self.command_or_url
        arguments = self.args

        if not self.args:
            argv = shlex.split(command)
            if not argv:
                raise ValueError("Command is empty")
            command = argv[0]
            arguments = argv[1:]

        # Windows npx handling
        if os.name == "nt" and command.lower() == "npx":
            command = "npx.cmd"

        server_parameters = StdioServerParameters(
            command=command, args=arguments, env=self.env
        )

        read_stream, write_stream = await self._exit_stack.enter_async_context(
            stdio_client(server_parameters)
        )

        self._read_stream = read_stream
        self._write_stream = write_stream

    async def _initialize_session(self):
        r"""Initialize the MCP session."""
        from mcp.client.session import ClientSession

        session_timeout = None
        if self.timeout is not None:
            session_timeout = timedelta(seconds=self.timeout)

        self._session = await self._exit_stack.enter_async_context(
            ClientSession(
                self._read_stream,
                self._write_stream,
                session_timeout,
            )
        )
        await self._session.initialize()

    async def _load_tools(self):
        r"""Load available tools from the MCP server."""
        try:
            list_tools_result = await self.list_mcp_tools()
            if isinstance(list_tools_result, str):
                error_msg = f"Failed to load tools: {list_tools_result}"
                raise MCPConnectionError(error_msg)
            self._mcp_tools = list_tools_result.tools
            logger.info(f"Loaded {len(self._mcp_tools)} tools from MCP server")
        except Exception as e:
            raise MCPConnectionError(f"Failed to load tools: {e}") from e

    def connect_sync(self):
        r"""Synchronously connect to the MCP server."""
        return run_async(self.connect)()

    async def disconnect(self):
        r"""Disconnect from the MCP server."""
        async with self._connection_lock:
            if self._connection_state == ConnectionState.DISCONNECTED:
                logger.debug("Server is already disconnected")
                return

            if self._connection_state == ConnectionState.DISCONNECTING:
                logger.warning("Disconnection already in progress")
                return

            self._connection_state = ConnectionState.DISCONNECTING

            try:
                await self._cleanup_resources()
                msg = (
                    f"Successfully disconnected from MCP server: "
                    f"{self.command_or_url}"
                )
                logger.info(msg)
            except Exception as e:
                error_msg = (
                    f"Error during disconnect from "
                    f"'{self.command_or_url}': {e}"
                )
                logger.error(error_msg)
            finally:
                self._connection_state = ConnectionState.DISCONNECTED

    async def _cleanup_resources(self):
        r"""Comprehensive resource cleanup."""
        # Run custom cleanup tasks first
        for cleanup_task in reversed(self._cleanup_tasks):
            try:
                if inspect.iscoroutinefunction(cleanup_task):
                    await cleanup_task()
                else:
                    cleanup_task()
            except Exception as e:
                logger.warning(f"Error in cleanup task: {e}")

        self._cleanup_tasks.clear()

        # Clean up exit stack
        await self._safe_cleanup_exit_stack()

        # Clear references
        self._session = None
        self._mcp_tools.clear()

    async def _safe_cleanup_exit_stack(self):
        r"""Safely cleanup the AsyncExitStack with proper error handling."""
        if self._exit_stack is not None:
            try:
                # Don't use shield or parallel cleanup - keep it simple
                await self._exit_stack.aclose()
            except (asyncio.CancelledError, RuntimeError) as e:
                # These are expected during shutdown, just log and continue
                logger.debug(f"Expected cleanup error during shutdown: {e}")
            except Exception as e:
                logger.warning(f"Error closing exit stack: {e}")
            finally:
                self._exit_stack = None

    async def _force_cleanup(self):
        r"""Force cleanup - used when connection fails."""
        try:
            await self._cleanup_resources()
        except Exception as e:
            # Force cleanup should never fail completely
            logger.warning(f"Force cleanup error: {e}")
            self._exit_stack = None
            self._session = None
            self._cleanup_tasks.clear()

    def add_cleanup_task(self, task: Callable):
        r"""Add a custom cleanup task to be executed during disconnect."""
        self._cleanup_tasks.append(task)

    @asynccontextmanager
    async def connection(self):
        r"""Async context manager for establishing and managing the connection
        with the MCP server. Automatically selects SSE or stdio mode based
        on the provided `command_or_url`.

        Yields:
            MCPClient: Instance with active connection ready for tool
                interaction.
        """
        try:
            await self.connect()
            yield self
        finally:
            try:
                await self.disconnect()
            except Exception as e:
                logger.warning(f"Error: {e}")

    def connection_sync(self):
        r"""Synchronously connect to the MCP server."""
        return run_async(self.connection)()

    def disconnect_sync(self):
        r"""Synchronously disconnect from the MCP server."""
        return run_async(self.disconnect)()

    async def list_mcp_tools(self) -> Union[str, "ListToolsResult"]:
        r"""List available tools with better error handling."""
        if not self._session:
            return "MCP Client is not connected. Call `connect()` first."

        try:
            return await self._session.list_tools()
        except Exception as e:
            logger.error(f"Failed to list MCP tools: {e}")
            raise MCPToolError(f"Failed to list tools: {e}") from e

    def list_mcp_tools_sync(self) -> Union[str, "ListToolsResult"]:
        r"""Synchronously list the available tools from the connected MCP
        server."""
        return run_async(self.list_mcp_tools)()

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

        async def dynamic_function(**kwargs) -> str:
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
                logger.warning(
                    f"Missing required parameters: {missing_params}"
                )
                return "Missing required parameters."

            if not self._session:
                logger.error(
                    "MCP Client is not connected. Call `connection()` first."
                )
                raise RuntimeError(
                    "MCP Client is not connected. Call `connection()` first."
                )

            try:
                result: CallToolResult = await self._session.call_tool(
                    func_name, kwargs
                )
            except Exception as e:
                logger.error(f"Failed to call MCP tool '{func_name}': {e!s}")
                raise e

            if not result.content or len(result.content) == 0:
                return "No data available for this request."

            # Handle different content types
            try:
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
            except (IndexError, AttributeError) as e:
                logger.error(
                    f"Error processing content from MCP tool response: {e!s}"
                )
                raise e

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

    def generate_function_from_mcp_tool_sync(self, mcp_tool: "Tool") -> Any:
        r"""Synchronously generate a function from an MCP tool."""
        return run_async(self.generate_function_from_mcp_tool)(mcp_tool)

    def _build_tool_schema(self, mcp_tool: "Tool") -> Dict[str, Any]:
        input_schema = mcp_tool.inputSchema
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        parameters = {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }

        return {
            "type": "function",
            "function": {
                "name": mcp_tool.name,
                "description": mcp_tool.description
                or "No description provided.",
                "strict": self.strict,
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

    def get_text_tools(self) -> str:
        r"""Returns a string containing the descriptions of the tools
        in the toolkit.

        Returns:
            str: A string containing the descriptions of the tools
                in the toolkit.
        """
        return "\n".join(
            f"tool_name: {tool.name}\n"
            + f"description: {tool.description or 'No description'}\n"
            + f"input Schema: {tool.inputSchema}\n"
            for tool in self._mcp_tools
        )

    async def call_tool(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Any:
        r"""Calls the specified tool with the provided arguments.

        Args:
            tool_name (str): Name of the tool to call.
            tool_args (Dict[str, Any]): Arguments to pass to the tool
                (default: :obj:`{}`).

        Returns:
            Any: The result of the tool call.
        """
        if self._session is None:
            raise RuntimeError("Session is not initialized.")

        return await self._session.call_tool(tool_name, tool_args)

    def call_tool_sync(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        r"""Synchronously call a tool."""
        return run_async(self.call_tool)(tool_name, tool_args)

    @property
    def session(self) -> Optional["ClientSession"]:
        return self._session

    @classmethod
    async def create(
        cls,
        command_or_url: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        mode: Optional[str] = None,
    ) -> "MCPClient":
        r"""Factory method that creates and connects to the MCP server.

        This async factory method ensures the connection to the MCP server is
        established before the client object is fully constructed.

        Args:
            command_or_url (str): URL for SSE mode or command executable
                for stdio mode.
            args (Optional[List[str]]): List of command-line arguments if
                stdio mode is used. (default: :obj:`None`)
            env (Optional[Dict[str, str]]): Environment variables for
                the stdio mode command. (default: :obj:`None`)
            timeout (Optional[float]): Connection timeout.
                (default: :obj:`None`)
            headers (Optional[Dict[str, str]]): Headers for the HTTP request.
                (default: :obj:`None`)
            mode (Optional[str]): Connection mode. Can be "sse" for
                Server-Sent Events, "streamable-http" for
                streaming HTTP, or None for stdio mode.
                (default: :obj:`None`)

        Returns:
            MCPClient: A fully initialized and connected MCPClient instance.

        Raises:
            RuntimeError: If connection to the MCP server fails.
        """
        client = cls(
            command_or_url=command_or_url,
            args=args,
            env=env,
            timeout=timeout,
            headers=headers,
            mode=mode,
        )
        try:
            await client.connect()
            return client
        except Exception as e:
            # Ensure cleanup on initialization failure
            await client.disconnect()
            logger.error(f"Failed to initialize MCPClient: {e}")
            raise RuntimeError(f"Failed to initialize MCPClient: {e}") from e

    @classmethod
    def create_sync(
        self,
        command_or_url: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        mode: Optional[str] = None,
    ) -> "MCPClient":
        r"""Synchronously create and connect to the MCP server."""
        return run_async(self.create)(
            command_or_url, args, env, timeout, headers, mode
        )

    async def __aenter__(self) -> "MCPClient":
        r"""Async context manager entry point. Automatically connects to the
        MCP server when used in an async with statement.

        Returns:
            MCPClient: Self with active connection.
        """
        await self.connect()
        return self

    def __enter__(self) -> "MCPClient":
        r"""Synchronously enter the async context manager."""
        return run_async(self.__aenter__)()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        r"""Async context manager exit point. Automatically disconnects from
        the MCP server when exiting an async with statement.

        Args:
            exc_type: The type of exception that occurred during execution.
            exc_val: The exception that occurred during execution.
            exc_tb: The traceback of the exception that occurred.

        Returns:
            None
        """
        await self.disconnect()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        r"""Synchronously exit the async context manager.

        Args:
            exc_type (Optional[Type[Exception]]): The type of exception that
                occurred during the execution of the with statement.
            exc_val (Optional[Exception]): The exception that occurred during
                the execution of the with statement.
            exc_tb (Optional[TracebackType]): The traceback of the exception
                that occurred during the execution of the with statement.

        Returns:
            None
        """
        return run_async(self.__aexit__)()


class MCPToolkit(BaseToolkit):
    r"""MCPToolkit provides a unified interface for managing multiple
    MCP server connections and their tools.

    This class handles the lifecycle of multiple MCP server connections and
    offers a centralized configuration mechanism for both local and remote
    MCP services.

    Connection Lifecycle:
        There are three ways to manage the connection lifecycle:

        1. Using the async context manager:
           ```python
           async with MCPToolkit(config_path="config.json") as toolkit:
               # Toolkit is connected here
               tools = toolkit.get_tools()
           # Toolkit is automatically disconnected here
           ```

        2. Using the factory method:
           ```python
           toolkit = await MCPToolkit.create(config_path="config.json")
           # Toolkit is connected here
           tools = toolkit.get_tools()
           # Don't forget to disconnect when done!
           await toolkit.disconnect()
           ```

        3. Using explicit connect/disconnect:
           ```python
           toolkit = MCPToolkit(config_path="config.json")
           await toolkit.connect()
           # Toolkit is connected here
           tools = toolkit.get_tools()
           # Don't forget to disconnect when done!
           await toolkit.disconnect()
           ```

    Args:
        servers (Optional[List[MCPClient]]): List of MCPClient
            instances to manage. (default: :obj:`None`)
        config_path (Optional[str]): Path to a JSON configuration file
            defining MCP servers. (default: :obj:`None`)
        config_dict (Optional[Dict[str, Any]]): Dictionary containing MCP
            server configurations in the same format as the config file.
            (default: :obj:`None`)
        strict (Optional[bool]): Whether to enforce strict mode for the
            function call. (default: :obj:`False`)

    Note:
        Either `servers`, `config_path`, or `config_dict` must be provided.
        If multiple are provided, servers from all sources will be combined.

        For web servers in the config, you can specify authorization
        headers using the "headers" field to connect to protected MCP server
        endpoints.

        Example configuration:

        .. code-block:: json

            {
              "mcpServers": {
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
        servers (List[MCPClient]): List of MCPClient instances being managed.
    """

    def __init__(
        self,
        servers: Optional[List[MCPClient]] = None,
        config_path: Optional[str] = None,
        config_dict: Optional[Dict[str, Any]] = None,
        strict: Optional[bool] = False,
    ):
        super().__init__()

        # Validate input parameters
        sources_provided = sum(
            1 for src in [servers, config_path, config_dict] if src is not None
        )
        if sources_provided == 0:
            error_msg = (
                "At least one of servers, config_path, or "
                "config_dict must be provided"
            )
            raise ValueError(error_msg)

        self.servers: List[MCPClient] = servers or []
        self._connection_state = ConnectionState.DISCONNECTED

        # Load servers from config sources
        if config_path:
            self.servers.extend(
                self._load_servers_from_config(config_path, strict)
            )

        if config_dict:
            self.servers.extend(
                self._load_servers_from_dict(config_dict, strict)
            )

    async def connect(self) -> "MCPToolkit":
        r"""Connect to all servers with improved error handling."""
        if self._connection_state == ConnectionState.CONNECTED:
            logger.warning("MCPToolkit is already connected")
            return self

        self._connection_state = ConnectionState.CONNECTING
        connected_servers = []

        try:
            for i, server in enumerate(self.servers):
                try:
                    await server.connect()
                    connected_servers.append(server)
                    msg = f"Connected to server {i+1}/{len(self.servers)}"
                    logger.debug(msg)
                except Exception as e:
                    logger.error(f"Failed to connect to server {i+1}: {e}")

                    # Cleanup already connected servers
                    await self._rollback_connections(connected_servers)

                    error_msg = f"Failed to connect to server {i+1}: {e}"
                    raise MCPConnectionError(error_msg) from e

            self._connection_state = ConnectionState.CONNECTED
            msg = f"Successfully connected to {len(self.servers)} MCP servers"
            logger.info(msg)
            return self

        except Exception:
            self._connection_state = ConnectionState.FAILED
            raise

    async def _rollback_connections(self, connected_servers: List[MCPClient]):
        r"""Rollback already connected servers - key improvement."""
        rollback_errors = []

        for server in connected_servers:
            try:
                await server.disconnect()
            except Exception as e:
                rollback_errors.append(f"Rollback error for server: {e}")

        if rollback_errors:
            logger.warning(f"Rollback errors: {rollback_errors}")

    async def disconnect(self):
        r"""Disconnect from all servers with comprehensive cleanup."""
        if self._connection_state == ConnectionState.DISCONNECTED:
            return

        self._connection_state = ConnectionState.DISCONNECTING

        # Disconnect servers sequentially to avoid task scope conflicts
        disconnect_errors = []
        for i, server in enumerate(self.servers):
            try:
                await server.disconnect()
            except Exception as e:
                disconnect_errors.append(f"Server {i+1}: {e}")
                logger.warning(f"Error disconnecting server {i+1}: {e}")

        self._connection_state = ConnectionState.DISCONNECTED

        if disconnect_errors:
            error_msg = (
                f"Some servers had disconnect errors: " f"{disconnect_errors}"
            )
            logger.warning(error_msg)

    @property
    def is_connected(self) -> bool:
        r"""Check if toolkit is connected."""
        # First check our own connection state
        if self._connection_state != ConnectionState.CONNECTED:
            return False

        # Then check if all servers are connected
        for server in self.servers:
            if hasattr(server, 'is_connected'):
                if not server.is_connected:
                    return False
            elif hasattr(server, '_connection_state'):
                state_check = (
                    server._connection_state != ConnectionState.CONNECTED
                )
                if state_check:
                    return False

        return True

    def connect_sync(self):
        r"""Synchronously connect to all MCP servers."""
        return run_async(self.connect)()

    def disconnect_sync(self):
        r"""Synchronously disconnect from all MCP servers."""
        return run_async(self.disconnect)()

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator["MCPToolkit", None]:
        r"""Async context manager that simultaneously establishes connections
        to all managed MCP server instances.

        Yields:
            MCPToolkit: Self with all servers connected.
        """
        try:
            await self.connect()
            yield self
        finally:
            await self.disconnect()

    def connection_sync(self):
        r"""Synchronously connect to all MCP servers."""
        return run_async(self.connection)()

    def _load_servers_from_config(
        self, config_path: str, strict: Optional[bool] = False
    ) -> List[MCPClient]:
        r"""Load servers from config with improved validation."""
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

        return self._load_servers_from_dict(config=data, strict=strict)

    def _load_servers_from_dict(
        self, config: Dict[str, Any], strict: Optional[bool] = False
    ) -> List[MCPClient]:
        r"""Load servers from config dict with improved validation."""
        if not isinstance(config, dict):
            raise ValueError("Config must be a dictionary")

        mcp_servers = config.get("mcpServers", {})
        if not isinstance(mcp_servers, dict):
            raise ValueError("'mcpServers' must be a dictionary")

        all_servers = []

        for name, cfg in mcp_servers.items():
            try:
                server = self._create_server_from_config(name, cfg, strict)
                all_servers.append(server)
            except Exception as e:
                logger.error(f"Failed to create server '{name}': {e}")
                error_msg = f"Invalid configuration for server '{name}': {e}"
                raise ValueError(error_msg) from e

        return all_servers

    def _create_server_from_config(
        self, name: str, cfg: Dict[str, Any], strict: Optional[bool]
    ) -> MCPClient:
        r"""Create a single server from configuration."""
        if not isinstance(cfg, dict):
            error_msg = f"Configuration for server '{name}' must be a dict"
            raise ValueError(error_msg)

        if "command" not in cfg and "url" not in cfg:
            error_msg = (
                f"Server '{name}' must have either 'command' or " "'url' field"
            )
            raise ValueError(error_msg)

        cmd_or_url = cfg.get("command") or cfg.get("url")
        if not cmd_or_url:
            raise ValueError(f"Server '{name}' command/url cannot be empty")

        # Validate mode if provided
        mode = cfg.get("mode")
        if mode and mode not in [m.value for m in ConnectionMode]:
            raise ValueError(f"Invalid mode '{mode}' for server '{name}'")

        # Validate timeout
        timeout = cfg.get("timeout")
        if timeout is not None and not isinstance(timeout, (int, float)):
            error_msg = (
                f"Invalid timeout '{timeout}' for server '{name}': "
                "must be a number"
            )
            raise ValueError(error_msg)

        return MCPClient(
            command_or_url=cmd_or_url,
            args=cfg.get("args", []),
            env={**os.environ, **cfg.get("env", {})},
            timeout=timeout,
            headers=cfg.get("headers", {}),
            mode=mode,
            strict=strict or False,  # Handle None case
        )

    def get_tools(self) -> List[FunctionTool]:
        r"""Aggregates all tools from the managed MCP server instances.

        Returns:
            List[FunctionTool]: Combined list of all available function tools.
        """
        all_tools = []
        for server in self.servers:
            all_tools.extend(server.get_tools())
        return all_tools

    def get_text_tools(self) -> str:
        r"""Returns a string containing the descriptions of the tools
        in the toolkit.

        Returns:
            str: A string containing the descriptions of the tools
                in the toolkit.
        """
        return "\n".join(server.get_text_tools() for server in self.servers)
