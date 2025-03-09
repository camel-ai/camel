import inspect
from typing import Optional, List, Dict, Callable, Any

from urllib.parse import urlparse

from mcp import ListToolsResult, Tool
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.types import CallToolResult

from camel.toolkits import BaseToolkit, FunctionTool
from contextlib import asynccontextmanager, AsyncExitStack


class McpToolkit(BaseToolkit):
    def __init__(
        self,
        command_or_url: str,
        args: List[str] = None,
        env: Dict[str, str] = None,
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
        """Context manager for managing the connection."""
        try:
            if urlparse(self.command_or_url).scheme in ("http", "https"):
                read_stream, write_stream = await (
                    self._exit_stack.enter_async_context(
                        sse_client(self.command_or_url)
                    )
                )
            else:
                server_parameters = StdioServerParameters(
                    command=self.command_or_url, args=self.args, env=self.env
                )
                read_stream, write_stream = await (
                    self._exit_stack.enter_async_context(
                        stdio_client(server_parameters)
                    )
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
        if not self._session:
            raise RuntimeError(
                "MCP Client is not connected. Call `connect()` first."
            )
        return await self._session.list_tools()

    def generate_function_from_mcp_tool(self, mcp_tool: Tool) -> Callable:
        func_name = mcp_tool.name
        func_desc = mcp_tool.description.strip() or "No description provided."
        parameters_schema = mcp_tool.inputSchema.get("properties", {})
        required_params = mcp_tool.inputSchema.get("required", [])

        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        annotations = {}  # 用于 type hints
        defaults = {}  # 存储默认参数值

        func_params = []
        for param_name, param_schema in parameters_schema.items():

            param_type = param_schema.get("type", "Any")
            param_type = type_map.get(param_type, Any)

            annotations[param_name] = param_type
            if param_name not in required_params:
                defaults[param_name] = None  # 非必填参数默认值设为 None

            func_params.append(param_name)

        async def dynamic_function(**kwargs):
            """Auto-generated function for MCP Tool."""
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
        dynamic_function.__signature__ = sig

        return dynamic_function

    def get_tools(self) -> List[FunctionTool]:
        return [
            FunctionTool(self.generate_function_from_mcp_tool(mcp_tool))
            for mcp_tool in self._mcp_tools
        ]
