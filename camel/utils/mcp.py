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
from typing import Callable, Any

from mcp.server.fastmcp import FastMCP


class MCPServer:
    def __init__(
        self, function_names: list[str],
        server_name: str = "MCPServer",
    ):
        self.function_names = function_names
        self.server_name = server_name

    def make_wrapper(self, func: Callable[..., Any]) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

        wrapper.__signature__ = inspect.signature(func)
        return wrapper

    def __call__(self, cls):
        original_init = cls.__init__

        def new_init(instance, *args, **kwargs):
            original_init(instance, *args, **kwargs)
            instance.mcp = FastMCP(self.server_name)
            for name in self.function_names:
                func = getattr(instance, name, None)
                if func is None or not callable(func):
                    raise ValueError(
                        f"Method {name} not found in class {cls.__name} or "
                        "cannot be called."
                    )
                wrapper = self.make_wrapper(func)
                instance.mcp.tool(name=name)(wrapper)

        cls.__init__ = new_init
        return cls
