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
import warnings
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from typing_extensions import TypeGuard

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils.commons import run_async
from camel.utils.mcp_client import MCPClient, create_mcp_client

logger = get_logger(__name__)

# Suppress parameter description warnings for MCP tools
warnings.filterwarnings(
    "ignore", message="Parameter description is missing", category=UserWarning
)


class MCPConnectionError(Exception):
    r"""Raised when MCP connection fails."""

    pass


class MCPToolError(Exception):
    r"""Raised when MCP tool execution fails."""

    pass


_EMPTY_SCHEMA = {
    "additionalProperties": False,
    "type": "object",
    "properties": {},
    "required": [],
}


def ensure_strict_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    r"""Mutates the given JSON schema to ensure it conforms to the
    `strict` standard that the OpenAI API expects.
    """
    if schema == {}:
        return _EMPTY_SCHEMA
    return _ensure_strict_json_schema(schema, path=(), root=schema)


def _ensure_strict_json_schema(
    json_schema: object,
    *,
    path: tuple[str, ...],
    root: dict[str, object],
) -> dict[str, Any]:
    if not is_dict(json_schema):
        raise TypeError(
            f"Expected {json_schema} to be a dictionary; path={path}"
        )

    defs = json_schema.get("$defs")
    if is_dict(defs):
        for def_name, def_schema in defs.items():
            _ensure_strict_json_schema(
                def_schema, path=(*path, "$defs", def_name), root=root
            )

    definitions = json_schema.get("definitions")
    if is_dict(definitions):
        for definition_name, definition_schema in definitions.items():
            _ensure_strict_json_schema(
                definition_schema,
                path=(*path, "definitions", definition_name),
                root=root,
            )

    typ = json_schema.get("type")
    if typ == "object" and "additionalProperties" not in json_schema:
        json_schema["additionalProperties"] = False
    elif (
        typ == "object"
        and "additionalProperties" in json_schema
        and json_schema["additionalProperties"]
    ):
        raise ValueError(
            "additionalProperties should not be set for object types. This "
            "could be because you're using an older version of Pydantic, or "
            "because you configured additional properties to be allowed. If "
            "you really need this, update the function or output tool "
            "to not use a strict schema."
        )

    # object types
    # { 'type': 'object', 'properties': { 'a':  {...} } }
    properties = json_schema.get("properties")
    if is_dict(properties):
        json_schema["required"] = list(properties.keys())
        json_schema["properties"] = {
            key: _ensure_strict_json_schema(
                prop_schema, path=(*path, "properties", key), root=root
            )
            for key, prop_schema in properties.items()
        }

    # arrays
    # { 'type': 'array', 'items': {...} }
    items = json_schema.get("items")
    if is_dict(items):
        json_schema["items"] = _ensure_strict_json_schema(
            items, path=(*path, "items"), root=root
        )

    # unions
    any_of = json_schema.get("anyOf")
    if is_list(any_of):
        json_schema["anyOf"] = [
            _ensure_strict_json_schema(
                variant, path=(*path, "anyOf", str(i)), root=root
            )
            for i, variant in enumerate(any_of)
        ]

    # intersections
    all_of = json_schema.get("allOf")
    if is_list(all_of):
        if len(all_of) == 1:
            json_schema.update(
                _ensure_strict_json_schema(
                    all_of[0], path=(*path, "allOf", "0"), root=root
                )
            )
            json_schema.pop("allOf")
        else:
            json_schema["allOf"] = [
                _ensure_strict_json_schema(
                    entry, path=(*path, "allOf", str(i)), root=root
                )
                for i, entry in enumerate(all_of)
            ]

    # strip `None` defaults as there's no meaningful distinction here
    # the schema will still be `nullable` and the model will default
    # to using `None` anyway
    if json_schema.get("default", None) is None:
        json_schema.pop("default", None)

    # we can't use `$ref`s if there are also other properties defined, e.g.
    # `{"$ref": "...", "description": "my description"}`
    #
    # so we unravel the ref
    # `{"type": "string", "description": "my description"}`
    ref = json_schema.get("$ref")
    if ref and has_more_than_n_keys(json_schema, 1):
        assert isinstance(ref, str), f"Received non-string $ref - {ref}"

        resolved = resolve_ref(root=root, ref=ref)
        if not is_dict(resolved):
            raise ValueError(
                f"Expected `$ref: {ref}` to resolved to a dictionary but got "
                f"{resolved}"
            )

        # properties from the json schema take priority
        # over the ones on the `$ref`
        json_schema.update({**resolved, **json_schema})
        json_schema.pop("$ref")
        # Since the schema expanded from `$ref` might not
        # have `additionalProperties: false` applied
        # we call `_ensure_strict_json_schema` again to fix the inlined
        # schema and ensure it's valid
        return _ensure_strict_json_schema(json_schema, path=path, root=root)

    return json_schema


def resolve_ref(*, root: dict[str, object], ref: str) -> object:
    if not ref.startswith("#/"):
        raise ValueError(
            f"Unexpected $ref format {ref!r}; Does not start with #/"
        )

    path = ref[2:].split("/")
    resolved = root
    for key in path:
        value = resolved[key]
        assert is_dict(value), (
            f"encountered non-dictionary entry while resolving {ref} - "
            f"{resolved}"
        )
        resolved = value

    return resolved


def is_dict(obj: object) -> TypeGuard[dict[str, object]]:
    # just pretend that we know there are only `str` keys
    # as that check is not worth the performance cost
    return isinstance(obj, dict)


def is_list(obj: object) -> TypeGuard[list[object]]:
    return isinstance(obj, list)


def has_more_than_n_keys(obj: dict[str, object], n: int) -> bool:
    i = 0
    for _ in obj.keys():
        i += 1
        if i > n:
            return True
    return False


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
            # Apply timeout to the entire connection process
            import asyncio

            timeout_seconds = self.timeout or 30.0
            await asyncio.wait_for(
                self._connect_all_clients(), timeout=timeout_seconds
            )

            self._is_connected = True
            msg = f"Successfully connected to {len(self.clients)} MCP servers"
            logger.info(msg)
            return self

        except (asyncio.TimeoutError, asyncio.CancelledError):
            self._is_connected = False
            if self._exit_stack:
                await self._exit_stack.aclose()
                self._exit_stack = None

            timeout_seconds = self.timeout or 30.0
            error_msg = (
                f"Connection timeout after {timeout_seconds}s. "
                f"One or more MCP servers are not responding. "
                f"Please check if the servers are running and accessible."
            )
            logger.error(error_msg)
            raise MCPConnectionError(error_msg)

        except Exception:
            self._is_connected = False
            if self._exit_stack:
                await self._exit_stack.aclose()
                self._exit_stack = None
            raise

    async def _connect_all_clients(self):
        r"""Connect to all clients sequentially."""
        # Connect to all clients using AsyncExitStack
        for i, client in enumerate(self.clients):
            try:
                # Use MCPClient directly as async context manager
                await self._exit_stack.enter_async_context(client)
                msg = f"Connected to client {i+1}/{len(self.clients)}"
                logger.debug(msg)
            except Exception as e:
                logger.error(f"Failed to connect to client {i+1}: {e}")
                # AsyncExitStack will cleanup already connected clients
                await self._exit_stack.aclose()
                self._exit_stack = None
                error_msg = f"Failed to connect to client {i+1}: {e}"
                raise MCPConnectionError(error_msg) from e

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
        r"""Ensure a tool has a strict schema compatible with
        OpenAI's requirements.

        Strategy:
        - Ensure parameters exist with at least an empty properties object
            (OpenAI requirement).
        - Try converting parameters to strict using ensure_strict_json_schema.
        - If conversion fails, mark function.strict = False and
            keep best-effort parameters.
        """
        try:
            schema = tool.get_openai_tool_schema()

            def _has_strict_mode_incompatible_features(json_schema):
                r"""Check if schema has features incompatible
                with OpenAI strict mode."""

                def _check_incompatible(obj, path=""):
                    if not isinstance(obj, dict):
                        return False

                    # Check for allOf in array items (known to cause issues)
                    if "items" in obj and isinstance(obj["items"], dict):
                        items_schema = obj["items"]
                        if "allOf" in items_schema:
                            logger.debug(
                                f"Found allOf in array items at {path}"
                            )
                            return True
                        # Recursively check items schema
                        if _check_incompatible(items_schema, f"{path}.items"):
                            return True

                    # Check for other potentially problematic patterns
                    # anyOf/oneOf in certain contexts can also cause issues
                    if (
                        "anyOf" in obj and len(obj["anyOf"]) > 10
                    ):  # Large unions can be problematic
                        return True

                    # Recursively check nested objects
                    for key in [
                        "properties",
                        "additionalProperties",
                        "patternProperties",
                    ]:
                        if key in obj and isinstance(obj[key], dict):
                            if key == "properties":
                                for prop_name, prop_schema in obj[key].items():
                                    if isinstance(
                                        prop_schema, dict
                                    ) and _check_incompatible(
                                        prop_schema,
                                        f"{path}.{key}.{prop_name}",
                                    ):
                                        return True
                            elif _check_incompatible(
                                obj[key], f"{path}.{key}"
                            ):
                                return True

                    # Check arrays and unions
                    for key in ["allOf", "anyOf", "oneOf"]:
                        if key in obj and isinstance(obj[key], list):
                            for i, item in enumerate(obj[key]):
                                if isinstance(
                                    item, dict
                                ) and _check_incompatible(
                                    item, f"{path}.{key}[{i}]"
                                ):
                                    return True

                    return False

                return _check_incompatible(json_schema)

            # Apply sanitization if available
            if "function" in schema:
                try:
                    from camel.toolkits.function_tool import (
                        sanitize_and_enforce_required,
                    )

                    schema = sanitize_and_enforce_required(schema)
                except ImportError:
                    logger.debug("sanitize_and_enforce_required not available")

                parameters = schema["function"].get("parameters", {})
                if not parameters:
                    # Empty parameters - use minimal valid schema
                    parameters = {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    }
                    schema["function"]["parameters"] = parameters

                # MCP spec doesn't require 'properties', but OpenAI spec does
                if (
                    parameters.get("type") == "object"
                    and "properties" not in parameters
                ):
                    parameters["properties"] = {}

                try:
                    # _check_schema_limits(parameters)

                    # Check for OpenAI strict mode incompatible features
                    if _has_strict_mode_incompatible_features(parameters):
                        raise ValueError(
                            "Schema contains features "
                            "incompatible with strict mode"
                        )

                    strict_params = ensure_strict_json_schema(parameters)
                    schema["function"]["parameters"] = strict_params
                    schema["function"]["strict"] = True
                except Exception as e:
                    # Fallback to non-strict mode on any failure
                    schema["function"]["strict"] = False
                    logger.warning(
                        f"Tool '{tool.get_function_name()}' "
                        f"cannot use strict mode: {e}"
                    )

            tool.set_openai_tool_schema(schema)

        except Exception as e:
            # Final fallback - ensure tool still works
            try:
                current_schema = tool.get_openai_tool_schema()
                if "function" in current_schema:
                    current_schema["function"]["strict"] = False
                tool.set_openai_tool_schema(current_schema)
                logger.warning(
                    f"Error processing schema for tool "
                    f"'{tool.get_function_name()}': {str(e)[:100]}. "
                    f"Using non-strict mode."
                )
            except Exception as inner_e:
                logger.error(
                    f"Critical error processing tool "
                    f"'{tool.get_function_name()}': {inner_e}. "
                    f"Tool may not function correctly."
                )

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
        seen_names: set[str] = set()
        for i, client in enumerate(self.clients):
            try:
                client_tools = client.get_tools()

                # Ensure all tools have strict schemas
                strict_tools = []
                for tool in client_tools:
                    strict_tool = self._ensure_strict_tool_schema(tool)
                    name = strict_tool.get_function_name()
                    if name in seen_names:
                        logger.warning(
                            f"Duplicate tool name detected and "
                            f"skipped: '{name}' from client {i+1}"
                        )
                        continue
                    seen_names.add(name)
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
