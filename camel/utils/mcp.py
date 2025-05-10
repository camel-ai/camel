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
import functools
import inspect
from typing import Any, Callable, Optional


class MCPServer:
    r"""Decorator class for registering functions of a class as tools in an MCP
    (Model Context Protocol) server.

    This class is typically used to wrap a toolkit or service class and
    automatically register specified methods (or methods derived from
    `BaseToolkit`) with a FastMCP server.

    Args:
        function_names (Optional[list[str]]): A list of method names to expose
            via the MCP server. If not provided and the class is a subclass of
            `BaseToolkit`, method names will be inferred from the tools
            returned by `get_tools()`.
        server_name (Optional[str]): A name for the MCP server. If not
            provided, the class name of the decorated object is used.

    Example:
        ```
        @MCPServer(function_names=["run", "status"])
        class MyTool:
            def run(self): ...
            def status(self): ...
        ```
        Or, with a class inheriting from BaseToolkit (no need to specify
        `function_names`):
        ```
        @MCPServer()
        class MyToolkit(BaseToolkit):
            ...
        ```

    Raises:
        ValueError: If no function names are provided and the class does not
            inherit from BaseToolkit, or if any specified method is not found
            or not callable.
    """

    def __init__(
        self,
        function_names: Optional[list[str]] = None,
        server_name: Optional[str] = None,
    ):
        self.function_names = function_names
        self.server_name = server_name

    def make_wrapper(self, func: Callable[..., Any]) -> Callable[..., Any]:
        r"""Wraps a function (sync or async) to preserve its signature and
        metadata.

        This is used to ensure the MCP server can correctly call and introspect
        the method.

        Args:
            func (Callable[..., Any]): The function to wrap.

        Returns:
            Callable[..., Any]: The wrapped function, with preserved signature
            and async support.
        """
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
        else:

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

        wrapper.__signature__ = inspect.signature(func)  # type: ignore[attr-defined]
        return wrapper

    def __call__(self, cls):
        r"""Decorates a class by injecting an MCP server instance and
        registering specified methods.

        Args:
            cls (type): The class being decorated.

        Returns:
            type: The modified class with MCP integration.

        Raises:
            ValueError: If function names are missing and the class is not a
                `BaseToolkit` subclass,
                or if a specified method cannot be found or is not callable.
        """
        from mcp.server.fastmcp import FastMCP

        from camel.toolkits.base import BaseToolkit

        original_init = cls.__init__

        def new_init(instance, *args, **kwargs):
            original_init(instance, *args, **kwargs)
            self.server_name = self.server_name or cls.__name__
            instance.mcp = FastMCP(self.server_name)

            if not self.function_names and not isinstance(
                instance, BaseToolkit
            ):
                raise ValueError(
                    "Please specify function names or use BaseToolkit."
                )

            function_names = self.function_names
            if not function_names and isinstance(instance, BaseToolkit):
                function_names = [
                    tool.get_function_name() for tool in instance.get_tools()
                ]

            for name in function_names:
                func = getattr(instance, name, None)
                if func is None or not callable(func):
                    raise ValueError(
                        f"Method {name} not found in class {cls.__name__} or "
                        "cannot be called."
                    )
                wrapper = self.make_wrapper(func)
                instance.mcp.tool(name=name)(wrapper)

        cls.__init__ = new_init
        return cls
