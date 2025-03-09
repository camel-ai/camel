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
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

from mcp import ListToolsResult, Tool
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CallToolResult

from camel.toolkits import BaseToolkit, FunctionTool


class McpToolkit(BaseToolkit):
    r"""McpToolkit provides an abstraction layer to interact with external
    tools using the Model Context Protocol (MCP). It supports two modes of
    connection:

    1. stdio mode: Connects via standard input/output streams for local
       command-line interactions.

    2. SSE mode (HTTP Server-Sent Events): Connects via HTTP for persistent,
       event-based interactions.

    Attributes:
        command_or_url (str): URL for SSE mode or command executable for stdio
            mode.
        args (List[str]): List of command-line arguments if stdio mode is used.
        env (Dict[str, str]): Environment variables for the stdio mode command.
        timeout (Optional[float]): Connection timeout.
    """

    def __init__(
        self,
        command_or_url: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ):
        super().__init__(timeout=timeout)

        self.command_or_url = command_or_url
        self.args = args or []
        self.env = env or {}

        self._mcp_tools: List[Tool] = []
        self._session: Optional[ClientSession] = None
        self._exit_stack = AsyncExitStack()

    @asynccontextmanager
    async def connection(self):
        r"""Async context manager for establishing and managing the connection
        with the MCP server. Automatically selects SSE or stdio mode based
        on the provided `command_or_url`.

        Yields:
            McpToolkit: Instance with active connection ready for tool
                interaction.
        """
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
            yield self

        finally:
            await self._exit_stack.aclose()
            self._session = None

    async def list_mcp_tools(self) -> ListToolsResult:
        r"""Retrieves the list of available tools from the connected MCP
        server.

        Returns:
            ListToolsResult: Result containing available MCP tools.

        Raises:
            RuntimeError: If the client session is not yet established.
        """
        if not self._session:
            raise RuntimeError(
                "MCP Client is not connected. Call `connection()` first."
            )
        return await self._session.list_tools()

    def generate_function_from_mcp_tool(self, mcp_tool: Tool) -> Callable:
        r"""Dynamically generates a Python callable function corresponding to
        a given MCP tool.

        Args:
            mcp_tool: The MCP tool definition received from the MCP server.

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
            missing_params = required_params - kwargs.keys()
            if missing_params:
                raise ValueError(
                    f"Missing required parameters: {missing_params}"
                )

            result: CallToolResult = await self._session.call_tool(
                func_name, kwargs
            )

            if not result.content:
                return "No data available for this request."

            if result.content[0].type != "text":
                # TODO: Handle other content types:
                #  [ImageContent | EmbeddedResource]
                return "Unsupported content type."

            return result.content[0].text

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

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit. Each function is dynamically generated
        based on the MCP tool definitions received from the server.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.generate_function_from_mcp_tool(mcp_tool))
            for mcp_tool in self._mcp_tools
        ]
