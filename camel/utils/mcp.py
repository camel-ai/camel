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
import warnings
from typing import (
    Any,
    Callable,
    List,
    Optional,
    Tuple,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from pydantic import create_model
from pydantic.errors import PydanticSchemaGenerationError

from camel.logger import get_logger

logger = get_logger(__name__)


def _is_pydantic_serializable(type_annotation: Any) -> Tuple[bool, str]:
    r"""Check if a type annotation is Pydantic serializable.

    Args:
        type_annotation: The type annotation to check

    Returns:
        Tuple[bool, str]: (is_serializable, error_message)
    """
    # Handle None type
    if type_annotation is type(None) or type_annotation is None:
        return True, ""

    # Handle generic types (List, Dict, Optional, etc.)
    origin = get_origin(type_annotation)
    if origin is not None:
        args = get_args(type_annotation)

        # For Union types (including Optional), check all args
        if origin is Union:
            for arg in args:
                is_serializable, error_msg = _is_pydantic_serializable(arg)
                if not is_serializable:
                    return False, error_msg
            return True, ""

        # For List, Set, Tuple, etc., check the contained types
        if origin in (list, set, tuple, frozenset):
            for arg in args:
                is_serializable, error_msg = _is_pydantic_serializable(arg)
                if not is_serializable:
                    return False, error_msg
            return True, ""

        # For Dict, check both key and value types
        if origin is dict:
            for arg in args:
                is_serializable, error_msg = _is_pydantic_serializable(arg)
                if not is_serializable:
                    return False, error_msg
            return True, ""

    # Try to create a simple pydantic model with this type
    try:
        create_model("TestModel", test_field=(type_annotation, ...))
        # If model creation succeeds, the type is serializable
        return True, ""
    except (PydanticSchemaGenerationError, TypeError, ValueError) as e:
        error_msg = (
            f"Type '{type_annotation}' is not Pydantic serializable. "
            f"Consider using a custom serializable type or converting "
            f"to bytes/base64. Error: {e!s}"
        )
        return False, error_msg


def _validate_function_types(func: Callable[..., Any]) -> List[str]:
    r"""Validate function parameter and return types are Pydantic serializable.

    Args:
        func (Callable[..., Any]): The function to validate.

    Returns:
        List[str]: List of error messages for incompatible types.
    """
    errors = []

    try:
        type_hints = get_type_hints(func)
    except (NameError, AttributeError) as e:
        # If we can't get type hints, skip validation
        logger.warning(f"Could not get type hints for {func.__name__}: {e}")
        return []

    # Check return type
    return_type = type_hints.get('return', Any)
    if return_type != Any:
        is_serializable, error_msg = _is_pydantic_serializable(return_type)
        if not is_serializable:
            errors.append(f"Return type: {error_msg}")

    # Check parameter types
    sig = inspect.signature(func)
    for param_name, _param in sig.parameters.items():
        if param_name == 'self':
            continue

        param_type = type_hints.get(param_name, Any)
        if param_type != Any:
            is_serializable, error_msg = _is_pydantic_serializable(param_type)
            if not is_serializable:
                errors.append(f"Parameter '{param_name}': {error_msg}")

    return errors


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
        function_names: Optional[List[str]] = None,
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

        original_init = cls.__init__

        def new_init(instance, *args, **kwargs):
            from camel.toolkits.base import BaseToolkit

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

                # Validate function types for Pydantic compatibility
                type_errors = _validate_function_types(func)
                if type_errors:
                    error_message = (
                        f"Method '{name}' in class '{cls.__name__}' has "
                        f"non-Pydantic-serializable types:\n"
                        + "\n".join(f"  - {error}" for error in type_errors)
                        + "\n\nSuggestions:"
                        + "\n  - Use standard Python types (str, int, float, bool, bytes)"  # noqa: E501
                        + "\n  - Convert complex objects to JSON strings or bytes"  # noqa: E501
                        + "\n  - Create custom Pydantic models for complex data"  # noqa: E501
                        + "\n  - Use base64 encoding for binary data like images"  # noqa: E501
                    )

                    # For now, issue a warning instead of raising an error
                    # This allows gradual migration while alerting developers
                    warnings.warn(error_message, UserWarning, stacklevel=3)
                    logger.warning(error_message)

                wrapper = self.make_wrapper(func)
                instance.mcp.tool(name=name)(wrapper)

        cls.__init__ = new_init
        return cls
