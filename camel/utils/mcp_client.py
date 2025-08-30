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

import inspect
from contextlib import asynccontextmanager
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Union,
)

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
    r"""Supported transport types."""

    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable_http"
    WEBSOCKET = "websocket"


class ServerConfig(BaseModel):
    r"""Unified server configuration that automatically detects transport type.

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

    # New transport type parameter
    type: Optional[str] = None

    # Legacy parameter for backward compatibility
    prefer_sse: bool = False

    @model_validator(mode='after')
    def validate_config(self):
        r"""Validate that either command or url is provided."""
        if not self.command and not self.url:
            raise ValueError(
                "Either 'command' (for stdio) or 'url' "
                "(for http/websocket) must be provided"
            )

        if self.command and self.url:
            raise ValueError("Cannot specify both 'command' and 'url'")

        # Validate type if provided
        if self.type is not None:
            valid_types = {"stdio", "sse", "streamable_http", "websocket"}
            if self.type not in valid_types:
                raise ValueError(
                    f"Invalid type: "
                    f"'{self.type}'. "
                    f"Valid options: {valid_types}"
                )

        # Issue deprecation warning if prefer_sse is used
        if self.prefer_sse and self.type is None:
            import warnings

            warnings.warn(
                "The 'prefer_sse' parameter is deprecated. "
                "Use 'type=\"sse\"' instead.",
                DeprecationWarning,
                stacklevel=2,
            )

        return self

    @property
    def transport_type(self) -> TransportType:
        r"""Automatically detect transport type based on configuration."""
        # Use explicit transport type if provided
        if self.type is not None:
            transport_map = {
                "stdio": TransportType.STDIO,
                "sse": TransportType.SSE,
                "streamable_http": TransportType.STREAMABLE_HTTP,
                "websocket": TransportType.WEBSOCKET,
            }
            return transport_map[self.type]

        # If no type is provided, fall back to automatic detection
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
    r"""Unified MCP client that automatically detects and connects to servers
    using the appropriate transport protocol.

    This client provides a unified interface for connecting to Model Context
    Protocol (MCP) servers using different transport protocols including STDIO,
    HTTP/HTTPS, WebSocket, and Server-Sent Events (SSE). The client
    automatically detects the appropriate transport type based on the
    configuration provided.

    The client should be used as an async context manager for automatic
    connectionmanagement.

    Args:
        config (Union[ServerConfig, Dict[str, Any]]): Server configuration
            as either a :obj:`ServerConfig` object or a dictionary that will
            be converted to a :obj:`ServerConfig`. The configuration determines
            the transport type and connection parameters.
        client_info (Optional[types.Implementation], optional): Client
            implementation information to send to the server during
            initialization. (default: :obj:`None`)
        timeout (Optional[float], optional): Timeout for waiting for messages
            from the server in seconds. (default: :obj:`10.0`)

    Examples:
        STDIO server:

        .. code-block:: python

            async with MCPClient({
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    "/path"
                ]
            }) as client:
                tools = client.get_tools()
                result = await client.call_tool("tool_name", {"arg": "value"})

        HTTP server:

        .. code-block:: python

            async with MCPClient({
                "url": "https://api.example.com/mcp",
                "headers": {"Authorization": "Bearer token"}
            }) as client:
                tools = client.get_tools()

        WebSocket server:

        .. code-block:: python

            async with MCPClient({"url": "ws://localhost:8080/mcp"}) as client:
                tools = client.get_tools()

    Attributes:
        config (ServerConfig): The server configuration object.
        client_info (Optional[types.Implementation]): Client implementation
            information.
        read_timeout_seconds (timedelta): Timeout for reading from the server.
    """

    def __init__(
        self,
        config: Union[ServerConfig, Dict[str, Any]],
        client_info: Optional[types.Implementation] = None,
        timeout: Optional[float] = 10.0,
    ):
        # Convert dict config to ServerConfig if needed
        if isinstance(config, dict):
            config = ServerConfig(**config)

        self.config = config

        # Validate transport type early (this will raise ValueError if invalid)
        _ = self.config.transport_type

        self.client_info = client_info
        self.read_timeout_seconds = timedelta(seconds=timeout or 10.0)

        self._session: Optional[ClientSession] = None
        self._tools: List[types.Tool] = []
        self._connection_context = None

    @property
    def transport_type(self) -> TransportType:
        r"""Get the detected transport type."""
        return self.config.transport_type

    async def __aenter__(self):
        r"""Async context manager entry point.

        Establishes connection to the MCP server and initializes the session.

        Returns:
            MCPClient: The connected client instance.
        """
        await self._establish_connection()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        r"""Async context manager exit point.

        Cleans up the connection and resources.
        """
        await self._cleanup_connection()

    async def _establish_connection(self):
        r"""Establish connection to the MCP server."""
        try:
            self._connection_context = self._create_transport()
            streams = await self._connection_context.__aenter__()

            # Handle extra returns safely
            read_stream, write_stream = streams[:2]

            self._session = ClientSession(
                read_stream=read_stream,
                write_stream=write_stream,
                client_info=self.client_info,
                read_timeout_seconds=self.read_timeout_seconds,
            )

            # Start the session's message processing loop
            await self._session.__aenter__()

            # Initialize the session and load tools
            await self._session.initialize()
            tools_response = await self._session.list_tools()
            self._tools = tools_response.tools if tools_response else []

        except Exception as e:
            # Clean up on error
            await self._cleanup_connection()

            # Convert complex exceptions to simpler, more understandable ones
            from camel.logger import get_logger

            logger = get_logger(__name__)

            error_msg = self._simplify_connection_error(e)
            logger.error(f"MCP connection failed: {error_msg}")

            # Raise a simpler exception
            raise ConnectionError(error_msg) from e

    async def _cleanup_connection(self):
        r"""Clean up connection resources."""
        try:
            if self._session:
                try:
                    await self._session.__aexit__(None, None, None)
                except Exception:
                    pass  # Ignore cleanup errors
                finally:
                    self._session = None

            if self._connection_context:
                try:
                    await self._connection_context.__aexit__(None, None, None)
                except Exception:
                    pass  # Ignore cleanup errors
                finally:
                    self._connection_context = None

            # Add a small delay to allow subprocess cleanup on Windows
            # This prevents "Event loop is closed" errors during shutdown
            import asyncio
            import sys

            if sys.platform == "win32":
                await asyncio.sleep(0.01)

        finally:
            # Ensure state is reset
            self._tools = []

    def _simplify_connection_error(self, error: Exception) -> str:
        r"""Convert complex MCP connection errors to simple, understandable
        messages.
        """
        error_str = str(error).lower()

        # Handle different types of errors
        if "exceptiongroup" in error_str or "taskgroup" in error_str:
            # Often happens when the command fails to start
            if "processlookuperror" in error_str:
                return (
                    f"Failed to start MCP server command "
                    f"'{self.config.command}'. The command may have "
                    "exited unexpectedly."
                )
            elif "cancelled" in error_str:
                return (
                    "Connection to MCP server was cancelled, "
                    "likely due to timeout or server startup failure."
                )
            else:
                return (
                    f"MCP server process error. The server command "
                    f"'{self.config.command}' failed to start properly."
                )

        elif "timeout" in error_str:
            return (
                f"Connection timeout after {self.config.timeout}s. "
                "The MCP server may be taking too long to respond."
            )

        elif "not found" in error_str or "404" in error_str:
            command_parts = []
            if self.config.command:
                command_parts.append(self.config.command)
                if self.config.args:
                    command_parts.extend(self.config.args)
            command_str = (
                ' '.join(command_parts) if command_parts else "unknown command"
            )
            return (
                f"MCP server package not found. Check if '{command_str}' "
                "is correct."
            )

        elif "permission" in error_str:
            return (
                f"Permission denied when trying to run MCP server "
                f"command '{self.config.command}'."
            )

        elif "connection" in error_str:
            if self.config.url:
                return f"Failed to connect to MCP server at {self.config.url}."
            else:
                return "Connection failed to MCP server."

        else:
            # Generic fallback
            command_info = (
                f"'{self.config.command}'"
                if self.config.command
                else f"URL: {self.config.url}"
            )
            return (
                f"MCP connection failed for {command_info}. Error: "
                f"{str(error)[:100]}{'...' if len(str(error)) > 100 else ''}"
            )

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

            try:
                # Try with httpx_client_factory first (newer versions)
                async with sse_client(
                    url=self.config.url,
                    headers=self.config.headers,
                    timeout=self.config.timeout,
                    sse_read_timeout=self.config.sse_read_timeout,
                    httpx_client_factory=create_mcp_http_client,
                ) as (read_stream, write_stream):
                    yield read_stream, write_stream
            except TypeError:
                # Fall back to basic call without httpx_client_factory
                async with sse_client(
                    url=self.config.url,
                    headers=self.config.headers,
                    timeout=self.config.timeout,
                    sse_read_timeout=self.config.sse_read_timeout,
                ) as (read_stream, write_stream):
                    yield read_stream, write_stream

        elif transport_type == TransportType.STREAMABLE_HTTP:
            from mcp.client.streamable_http import streamablehttp_client

            # Ensure URL is not None for StreamableHTTP
            if not self.config.url:
                raise ValueError(
                    "URL is required for StreamableHTTP transport"
                )

            try:
                # Try with httpx_client_factory first (newer versions)
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
            except TypeError:
                # Fall back to basic call without httpx_client_factory
                async with streamablehttp_client(
                    url=self.config.url,
                    headers=self.config.headers,
                    timeout=timedelta(seconds=self.config.timeout),
                    sse_read_timeout=timedelta(
                        seconds=self.config.sse_read_timeout
                    ),
                    terminate_on_close=self.config.terminate_on_close,
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
        r"""Get the current session if connected."""
        return self._session

    def is_connected(self) -> bool:
        r"""Check if the client is currently connected."""
        return self._session is not None

    async def list_mcp_tools(self):
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
            raise e

    def list_mcp_tools_sync(self):
        r"""Synchronously retrieves the list of available tools from the
        connected MCP server.

        Returns:
            ListToolsResult: Result containing available MCP tools.
        """
        from camel.utils.commons import run_async

        return run_async(self.list_mcp_tools)()

    def generate_function_from_mcp_tool(
        self, mcp_tool: types.Tool
    ) -> Callable:
        r"""Dynamically generates a Python callable function corresponding to
        a given MCP tool.

        Args:
            mcp_tool (types.Tool): The MCP tool definition received from the
                MCP server.

        Returns:
            Callable: A dynamically created Python function that wraps
                the MCP tool and works in both sync and async contexts.
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

        # Create the async version of the function
        async def async_mcp_call(**kwargs) -> str:
            r"""Async version of MCP tool call."""
            missing_params: Set[str] = set(required_params) - set(
                kwargs.keys()
            )
            if missing_params:
                from camel.logger import get_logger

                logger = get_logger(__name__)
                logger.warning(
                    f"Missing required parameters: {missing_params}"
                )
                return "Missing required parameters."

            if not self._session:
                from camel.logger import get_logger

                logger = get_logger(__name__)
                logger.error(
                    "MCP Client is not connected. Call `connection()` first."
                )
                raise RuntimeError(
                    "MCP Client is not connected. Call `connection()` first."
                )

            try:
                result = await self._session.call_tool(func_name, kwargs)
            except Exception as e:
                from camel.logger import get_logger

                logger = get_logger(__name__)
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
                from camel.logger import get_logger

                logger = get_logger(__name__)
                logger.error(
                    f"Error processing content from MCP tool response: {e!s}"
                )
                raise e

        def adaptive_dynamic_function(**kwargs) -> str:
            r"""Adaptive function that works in both sync and async contexts.

            This function detects if it's being called from an async context
            and behaves accordingly.

            Args:
                kwargs: Keyword arguments corresponding to MCP tool parameters.

            Returns:
                str: The textual result returned by the MCP tool.

            Raises:
                TimeoutError: If the operation times out.
                RuntimeError: If there are issues with async execution.
            """
            import asyncio
            import concurrent.futures

            try:
                # Check if we're in an async context with a running loop
                loop = asyncio.get_running_loop()  # noqa: F841
                # If we get here, we're in an async context with a running loop
                # We need to run the async function in a separate thread with
                # a new loop

                def run_in_thread():
                    # Create a new event loop for this thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            async_mcp_call(**kwargs)
                        )
                    except Exception as e:
                        # Preserve the original exception context
                        raise RuntimeError(
                            f"MCP call failed in thread: {e}"
                        ) from e
                    finally:
                        new_loop.close()

                # Run in a separate thread to avoid event loop conflicts
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    try:
                        return future.result(
                            timeout=self.read_timeout_seconds.total_seconds()
                        )
                    except concurrent.futures.TimeoutError:
                        raise TimeoutError(
                            f"MCP call timed out after "
                            f"{self.read_timeout_seconds.total_seconds()}"
                            f" seconds"
                        )

            except RuntimeError as e:
                # Only handle the specific "no running event loop" case
                if (
                    "no running event loop" in str(e).lower()
                    or "no current event loop" in str(e).lower()
                ):
                    # No event loop is running, we can safely use run_async
                    from camel.utils.commons import run_async

                    run_async_func = run_async(async_mcp_call)
                    return run_async_func(**kwargs)
                else:
                    # Re-raise other RuntimeErrors
                    raise

        # Add an async_call method to the function for explicit async usage
        adaptive_dynamic_function.async_call = async_mcp_call  # type: ignore[attr-defined]

        adaptive_dynamic_function.__name__ = func_name
        adaptive_dynamic_function.__doc__ = func_desc
        adaptive_dynamic_function.__annotations__ = annotations

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
        adaptive_dynamic_function.__signature__ = sig  # type: ignore[attr-defined]

        return adaptive_dynamic_function

    def _build_tool_schema(self, mcp_tool: types.Tool) -> Dict[str, Any]:
        r"""Build tool schema for OpenAI function calling format."""
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
                "parameters": parameters,
            },
        }

    def get_tools(self):
        r"""Get available tools as CAMEL FunctionTool objects.

        Retrieves all available tools from the connected MCP server and
        converts them to CAMEL-compatible :obj:`FunctionTool` objects. The
        tools are automatically wrapped to handle the MCP protocol
        communication.

        Returns:
            List[FunctionTool]: A list of :obj:`FunctionTool` objects
                representing the available tools from the MCP server. Returns
                an empty list if the client is not connected.

        Note:
            This method requires an active connection to the MCP server.
            If the client is not connected, an empty list will be returned.
        """
        if not self.is_connected():
            return []

        # Import FunctionTool here to avoid circular imports
        try:
            from camel.toolkits import FunctionTool
        except ImportError:
            from camel.logger import get_logger

            logger = get_logger(__name__)
            logger.error(
                "Failed to import FunctionTool. Please ensure "
                "camel.toolkits is available."
            )
            return []

        camel_tools = []
        for tool in self._tools:
            try:
                # Generate the function and build the tool schema
                func = self.generate_function_from_mcp_tool(tool)
                schema = self._build_tool_schema(tool)

                # Create CAMEL FunctionTool
                camel_tool = FunctionTool(
                    func,
                    openai_tool_schema=schema,
                )
                camel_tools.append(camel_tool)
            except Exception as e:
                # Log error but continue with other tools
                from camel.logger import get_logger

                logger = get_logger(__name__)
                logger.warning(f"Failed to convert tool {tool.name}: {e}")

        return camel_tools

    def get_text_tools(self) -> str:
        r"""Get a text description of available tools.

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
        r"""Call a tool by name with the provided arguments.

        Executes a specific tool on the connected MCP server with the given
        arguments. The tool must be available in the server's tool list.

        Args:
            tool_name (str): The name of the tool to call. Must match a tool
                name returned by :obj:`get_tools()`.
            arguments (Dict[str, Any]): A dictionary of arguments to pass to
                the tool. The argument names and types must match the tool's
                expected parameters.

        Returns:
            Any: The result returned by the tool execution. The type and
                structure depend on the specific tool being called.

        Raises:
            RuntimeError: If the client is not connected to an MCP server.
            ValueError: If the specified tool name is not found in the list
                of available tools.

        Example:
            .. code-block:: python

                # Call a file reading tool
                result = await client.call_tool(
                    "read_file",
                    {"path": "/tmp/example.txt"}
                )
        """
        if not self.is_connected():
            raise RuntimeError("Client is not connected")

        # Check if tool exists
        tool_names = [tool.name for tool in self._tools]
        if tool_name not in tool_names:
            available_tools = ', '.join(tool_names)
            raise ValueError(
                f"Tool '{tool_name}' not found. "
                f"Available tools: {available_tools}"
            )

        # Call the tool using the correct API
        if self._session is None:
            raise RuntimeError("Client session is not available")

        result = await self._session.call_tool(
            name=tool_name, arguments=arguments
        )

        return result

    def call_tool_sync(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        r"""Synchronously call a tool by name with the provided arguments.

        Args:
            tool_name (str): The name of the tool to call.
            arguments (Dict[str, Any]): A dictionary of arguments to pass to
                the tool.

        Returns:
            Any: The result returned by the tool execution.
        """
        from camel.utils.commons import run_async

        return run_async(self.call_tool)(tool_name, arguments)


def create_mcp_client(
    config: Union[Dict[str, Any], ServerConfig], **kwargs: Any
) -> MCPClient:
    r"""Create an MCP client from configuration.

    Factory function that creates an :obj:`MCPClient` instance from various
    configuration formats. This is the recommended way to create MCP clients
    as it handles configuration validation and type conversion automatically.

    Args:
        config (Union[Dict[str, Any], ServerConfig]): Server configuration
            as either a dictionary or a :obj:`ServerConfig` object. If a
            dictionary is provided, it will be automatically converted to
            a :obj:`ServerConfig`.
        **kwargs: Additional keyword arguments passed to the :obj:`MCPClient`
            constructor, such as :obj:`client_info`, :obj:`timeout`.

    Returns:
        MCPClient: A configured :obj:`MCPClient` instance ready for use as
            an async context manager.

    Examples:
        STDIO server:

        .. code-block:: python

            async with create_mcp_client({
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    "/path",
                ],
            }) as client:
                tools = client.get_tools()

        HTTP server:

        .. code-block:: python

            async with create_mcp_client({
                "url": "https://api.example.com/mcp",
                "headers": {"Authorization": "Bearer token"}
            }) as client:
                result = await client.call_tool("tool_name", {"arg": "value"})

        WebSocket server:

        .. code-block:: python

            async with create_mcp_client({
                "url": "ws://localhost:8080/mcp"
            }) as client:
                tools = client.get_tools()
    """
    return MCPClient(config, **kwargs)


def create_mcp_client_from_config_file(
    config_path: Union[str, Path], server_name: str, **kwargs: Any
) -> MCPClient:
    r"""Create an MCP client from a configuration file.

    Args:
        config_path (Union[str, Path]): Path to configuration file (JSON).
        server_name (str): Name of the server in the config.
        **kwargs: Additional arguments passed to MCPClient constructor.

    Returns:
        MCPClient: MCPClient instance as an async context manager.
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
        .. code-block:: python

            async with create_mcp_client_from_config_file(
                "config.json", "filesystem"
            ) as client:
                tools = client.get_tools()
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
