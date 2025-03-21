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
from typing import Literal, Optional

from mcp.server.fastmcp import FastMCP


class MCPServerMixin:
    _mcp_instance: Optional[FastMCP] = None

    @staticmethod
    def _register_mcp_tools(cls):
        r"""Register all public methods in the class as MCP tools."""
        assert (
            cls._mcp_instance is not None
        ), "_mcp_instance must be initialized before registering tools"

        for name, method in inspect.getmembers(
            cls, predicate=inspect.isfunction
        ):
            if not name.startswith("_"):
                cls._mcp_instance.tool()(method)
                print(f"Registered {cls.__name__}.{name} as MCP tool.")

    @classmethod
    def start_mcp_server(
        cls,
        transport: Literal["stdio", "sse"] = "stdio",
        **kwargs,
    ):
        r"""Initialize the MCP server, register public methods as MCP tools,
        and start the MCP server.

        Args:
            transport (Literal["stdio", "sse"], optional): The transport
                protocol to use. Defaults to "stdio".
        """
        if cls._mcp_instance is None:
            cls._mcp_instance = FastMCP(name=cls.__name__, **kwargs)
        cls._register_mcp_tools(cls)
        cls._mcp_instance.run(transport)
