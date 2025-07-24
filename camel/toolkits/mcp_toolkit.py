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
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits import BaseToolkit, FunctionTool
from camel.utils.commons import run_async
from camel.utils.mcp_client import MCPClient, create_mcp_client

logger = get_logger(__name__)


class MCPConnectionError(Exception):
    r"""Raised when MCP connection fails."""

    pass


class MCPToolError(Exception):
    r"""Raised when MCP tool execution fails."""

    pass


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
        force_openai_compatible: bool = True,
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
        self.force_openai_compatible = force_openai_compatible

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
            # Connect to all clients using AsyncExitStack
            for i, client in enumerate(self.clients):
                try:
                    # Use MCPClient directly as async context manager
                    await self._exit_stack.enter_async_context(client)
                    msg = f"Connected to client {i+1}/{len(self.clients)}"
                    logger.debug(msg)
                except Exception as e:
                    logger.error(f"Failed to connect to client {i+1}: {e}")
                    # AsyncExitStack will handle cleanup of already connected
                    await self._exit_stack.aclose()
                    self._exit_stack = None
                    error_msg = f"Failed to connect to client {i+1}: {e}"
                    raise MCPConnectionError(error_msg) from e

            self._is_connected = True
            msg = f"Successfully connected to {len(self.clients)} MCP servers"
            logger.info(msg)
            return self

        except Exception:
            self._is_connected = False
            if self._exit_stack:
                await self._exit_stack.aclose()
                self._exit_stack = None
            raise

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
        r"""Ensure a tool has a strict schema compatible with OpenAI's
        requirements.

        Args:
            tool (FunctionTool): The tool to check and update if necessary.

        Returns:
            FunctionTool: The tool with a strict schema, or fallback to non-strict
                mode if strict mode cannot be applied.
        """
        tool_name = "unknown"

        try:
            # Get tool name early for better error reporting
            try:
                tool_name = tool.get_function_name()
            except Exception:
                tool_name = getattr(tool.func, '__name__', 'unknown')

            # Force OpenAI compatible mode - skip complex validation and go straight to reconstruction
            if self.force_openai_compatible:
                logger.debug(
                    f"Force OpenAI compatible mode enabled for tool '{tool_name}'"
                )
                return self._force_openai_compatible_schema(tool, tool_name)

            # Original logic for non-force mode
            # Try to get the schema, but handle cases where it might be malformed
            try:
                schema = tool.get_openai_tool_schema()
            except Exception as schema_error:
                logger.warning(
                    f"Tool '{tool_name}' has malformed schema: {schema_error}"
                )
                return self._reconstruct_and_fallback(
                    tool, tool_name, f"Malformed schema: {schema_error}"
                )

            # Validate basic schema structure
            if not self._validate_basic_schema_structure(schema, tool_name):
                return self._apply_fallback_schema(
                    tool, tool_name, "Invalid basic schema structure"
                )

            # Check for strict mode incompatibilities
            strict_incompatible_reason = self._check_strict_mode_compatibility(
                schema
            )
            if strict_incompatible_reason:
                return self._apply_fallback_schema(
                    tool, tool_name, strict_incompatible_reason
                )

            # Check if the tool already has strict mode enabled and is valid
            if schema.get("function", {}).get("strict") is True:
                if self._validate_strict_schema_requirements(
                    schema, tool_name
                ):
                    logger.debug(
                        f"Tool '{tool_name}' already has valid strict schema"
                    )
                    return tool
                else:
                    logger.warning(
                        f"Tool '{tool_name}' has strict=True but invalid schema, attempting to fix"
                    )

            # Attempt to convert to strict mode
            strict_schema = self._convert_to_strict_schema(schema, tool_name)
            if strict_schema:
                logger.debug(
                    f"Setting strict schema for tool '{tool_name}': {strict_schema}"
                )
                tool.set_openai_tool_schema(strict_schema)
                logger.debug(
                    f"Successfully converted tool '{tool_name}' to strict mode"
                )
                return tool
            else:
                return self._apply_fallback_schema(
                    tool, tool_name, "Failed to convert to strict mode"
                )

        except Exception as e:
            logger.error(
                f"Unexpected error processing tool '{tool_name}': {e}"
            )
            return self._reconstruct_and_fallback(
                tool, tool_name, f"Unexpected error: {e}"
            )

    def _force_openai_compatible_schema(
        self, tool: FunctionTool, tool_name: str
    ) -> FunctionTool:
        """Force creation of OpenAI-compatible schema by rebuilding from function signature."""
        try:
            # Always rebuild the schema from scratch for maximum compatibility
            from camel.toolkits.function_tool import get_openai_tool_schema

            # Get the basic schema from function signature
            basic_schema = get_openai_tool_schema(tool.func)

            # Ensure strict mode is enabled for maximum reliability
            basic_schema["function"]["strict"] = True

            # Apply additional OpenAI strict mode requirements
            parameters = basic_schema["function"].get("parameters", {})
            if parameters:
                # Ensure additionalProperties is False at root level
                parameters["additionalProperties"] = False

                # Recursively ensure all nested objects have additionalProperties: False
                self._ensure_additional_properties_false_recursive(parameters)

                # Ensure all properties are in required array
                properties = parameters.get("properties", {})
                if properties:
                    parameters["required"] = list(properties.keys())

            # Set the OpenAI-compatible schema
            tool.set_openai_tool_schema(basic_schema)

            logger.info(
                f"Tool '{tool_name}' schema force-converted to OpenAI-compatible format"
            )
            return tool

        except Exception as e:
            logger.error(
                f"Failed to force OpenAI-compatible schema for tool '{tool_name}': {e}"
            )
            # Last resort: create minimal schema
            return self._create_minimal_schema(tool, tool_name)

    def _ensure_additional_properties_false_recursive(self, obj):
        """Recursively ensure all objects have additionalProperties: False."""
        if isinstance(obj, dict):
            # If this is an object type, ensure additionalProperties is False
            if obj.get("type") == "object":
                obj["additionalProperties"] = False

            # Handle empty items objects - give them a default type
            if "items" in obj and isinstance(obj["items"], dict):
                items = obj["items"]
                if not items or (isinstance(items, dict) and not items):
                    # Empty items object - default to string type for maximum compatibility
                    obj["items"] = {"type": "string"}
                    logger.debug(
                        "Fixed empty items object by setting default type: string"
                    )
                elif (
                    isinstance(items, dict)
                    and "type" not in items
                    and not any(
                        key in items
                        for key in [
                            "properties",
                            "anyOf",
                            "allOf",
                            "oneOf",
                            "$ref",
                        ]
                    )
                ):
                    # Items object exists but has no type or schema structure - default to string
                    items["type"] = "string"
                    logger.debug("Added missing type to items object: string")

            # Recursively process nested structures
            for key, value in obj.items():
                if key == "properties" and isinstance(value, dict):
                    for prop_value in value.values():
                        self._ensure_additional_properties_false_recursive(
                            prop_value
                        )
                elif key in [
                    "items",
                    "allOf",
                    "oneOf",
                    "anyOf",
                ] and isinstance(value, (dict, list)):
                    if isinstance(value, dict):
                        self._ensure_additional_properties_false_recursive(
                            value
                        )
                    elif isinstance(value, list):
                        for item in value:
                            self._ensure_additional_properties_false_recursive(
                                item
                            )
                elif key == "$defs" and isinstance(value, dict):
                    for def_value in value.values():
                        self._ensure_additional_properties_false_recursive(
                            def_value
                        )

    def _create_minimal_schema(
        self, tool: FunctionTool, tool_name: str
    ) -> FunctionTool:
        """Create a minimal OpenAI-compatible schema as last resort."""
        try:
            # Create the most basic schema possible
            minimal_schema = {
                "type": "function",
                "function": {
                    "name": tool_name.replace(
                        '-', '_'
                    ),  # Ensure valid function name
                    "description": f"Execute {tool_name} function",
                    "strict": False,  # Use non-strict mode for minimal schema
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    },
                },
            }

            tool.set_openai_tool_schema(minimal_schema)
            logger.warning(
                f"Tool '{tool_name}' using minimal schema as last resort"
            )
            return tool

        except Exception as e:
            logger.error(
                f"Failed to create minimal schema for tool '{tool_name}': {e}"
            )
            return tool

    def _reconstruct_and_fallback(
        self, tool: FunctionTool, tool_name: str, reason: str
    ) -> FunctionTool:
        """Reconstruct a basic schema from the function and set to non-strict mode."""
        try:
            from camel.toolkits.function_tool import get_openai_tool_schema

            basic_schema = get_openai_tool_schema(tool.func)
            basic_schema["function"]["strict"] = False
            tool.set_openai_tool_schema(basic_schema)
            logger.warning(
                f"Tool '{tool_name}' reconstructed with basic schema due to: {reason}. "
                f"Using non-strict mode."
            )
        except Exception as reconstruct_error:
            logger.error(
                f"Failed to reconstruct schema for tool '{tool_name}': {reconstruct_error}. "
                f"Tool may not function correctly."
            )
        return tool

    def _validate_basic_schema_structure(
        self, schema: dict, tool_name: str
    ) -> bool:
        """Validate that the schema has the basic required structure."""
        try:
            # Check top-level structure
            if not isinstance(schema, dict):
                logger.warning(
                    f"Tool '{tool_name}' schema is not a dictionary"
                )
                return False

            if "type" not in schema or schema["type"] != "function":
                logger.warning(
                    f"Tool '{tool_name}' missing or invalid 'type' field"
                )
                return False

            if "function" not in schema or not isinstance(
                schema["function"], dict
            ):
                logger.warning(
                    f"Tool '{tool_name}' missing or invalid 'function' field"
                )
                return False

            function_def = schema["function"]

            # Check required function fields
            if "name" not in function_def or not isinstance(
                function_def["name"], str
            ):
                logger.warning(
                    f"Tool '{tool_name}' missing or invalid function name"
                )
                return False

            # Description is recommended but not required
            if "description" not in function_def:
                logger.info(
                    f"Tool '{tool_name}' missing description (recommended)"
                )

            # Parameters field validation
            if "parameters" in function_def:
                parameters = function_def["parameters"]
                if not isinstance(parameters, dict):
                    logger.warning(
                        f"Tool '{tool_name}' parameters field is not a dictionary"
                    )
                    return False

                # If parameters exist, they should have type: object
                if parameters.get("type") != "object":
                    logger.warning(
                        f"Tool '{tool_name}' parameters type should be 'object'"
                    )
                    return False

            return True
        except Exception as e:
            logger.warning(
                f"Error validating basic schema structure for '{tool_name}': {e}"
            )
            return False

    def _check_strict_mode_compatibility(self, schema: dict) -> str:
        """Check if schema has features incompatible with strict mode.

        Returns:
            str: Reason for incompatibility, or empty string if compatible.
        """
        try:
            # Check for additionalProperties: true (most common incompatibility)
            def _has_additional_properties_true(obj, path=""):
                if isinstance(obj, dict):
                    if obj.get("additionalProperties") is True:
                        return f"additionalProperties: true found at {path}"
                    for key, value in obj.items():
                        result = _has_additional_properties_true(
                            value, f"{path}.{key}" if path else key
                        )
                        if result:
                            return result
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        result = _has_additional_properties_true(
                            item, f"{path}[{i}]"
                        )
                        if result:
                            return result
                return ""

            additional_props_issue = _has_additional_properties_true(schema)
            if additional_props_issue:
                return additional_props_issue

            # Check for other strict mode incompatibilities
            parameters = schema.get("function", {}).get("parameters", {})
            if parameters:
                # Check for unsupported JSON Schema features
                unsupported_features = (
                    self._check_unsupported_json_schema_features(parameters)
                )
                if unsupported_features:
                    return f"Unsupported JSON Schema features: {unsupported_features}"

            return ""

        except Exception as e:
            return f"Error checking strict mode compatibility: {e}"

    def _check_unsupported_json_schema_features(self, obj, path="") -> str:
        """Check for JSON Schema features not supported in strict mode."""
        try:
            if not isinstance(obj, dict):
                return ""

            # Features not supported in strict mode
            unsupported_keywords = {
                "patternProperties": "pattern properties",
                "dependencies": "dependencies",
                "additionalItems": "additional items",
                "minProperties": "min properties",
                "maxProperties": "max properties",
                "not": "not keyword",
                "if": "conditional schemas",
                "allOf": "allOf composition",
                "dependentRequired": "dependent required",
                "dependentSchemas": "dependent schemas",
                "then": "then keyword",
                "else": "else keyword",
            }

            for keyword, description in unsupported_keywords.items():
                if keyword in obj:
                    return f"{description} at {path}"

            # Recursively check nested objects
            for key, value in obj.items():
                if isinstance(value, dict):
                    result = self._check_unsupported_json_schema_features(
                        value, f"{path}.{key}" if path else key
                    )
                    if result:
                        return result
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            result = (
                                self._check_unsupported_json_schema_features(
                                    item,
                                    f"{path}.{key}[{i}]"
                                    if path
                                    else f"{key}[{i}]",
                                )
                            )
                            if result:
                                return result

            return ""

        except Exception as e:
            return f"Error checking unsupported features: {e}"

    def _validate_strict_schema_requirements(
        self, schema: dict, tool_name: str
    ) -> bool:
        """Validate that a schema meets all strict mode requirements."""
        try:
            parameters = schema.get("function", {}).get("parameters")
            if not parameters:
                return True  # No parameters is valid

            # All objects must have additionalProperties: false
            def _validate_additional_properties(obj, path=""):
                if isinstance(obj, dict):
                    if obj.get("type") == "object":
                        if "additionalProperties" not in obj:
                            logger.warning(
                                f"Missing additionalProperties at {path}"
                            )
                            return False
                        if obj.get("additionalProperties") is not False:
                            logger.warning(
                                f"additionalProperties must be false at {path}"
                            )
                            return False

                    # Check nested objects
                    for key, value in obj.items():
                        if not _validate_additional_properties(
                            value, f"{path}.{key}" if path else key
                        ):
                            return False
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        if not _validate_additional_properties(
                            item, f"{path}[{i}]"
                        ):
                            return False
                return True

            if not _validate_additional_properties(parameters, "parameters"):
                return False

            # All properties should be required in strict mode
            properties = parameters.get("properties", {})
            required = parameters.get("required", [])

            if properties and set(properties.keys()) != set(required):
                logger.debug(
                    f"Tool '{tool_name}' has optional properties, should use null types"
                )
                # This is not necessarily invalid - optional fields should have null type

            return True

        except Exception as e:
            logger.warning(
                f"Error validating strict schema requirements for '{tool_name}': {e}"
            )
            return False

    def _convert_to_strict_schema(self, schema: dict, tool_name: str) -> dict:
        """Convert a schema to strict mode, returning None if conversion fails."""
        try:
            # Create a deep copy to avoid modifying the original
            import copy

            strict_schema = copy.deepcopy(schema)

            # Set strict mode
            strict_schema["function"]["strict"] = True

            # Process parameters
            parameters = strict_schema["function"].get("parameters")
            if parameters:
                # Ensure additionalProperties is false
                parameters["additionalProperties"] = False

                # Use the existing sanitization function from function_tool
                from camel.toolkits.function_tool import (
                    sanitize_and_enforce_required,
                )

                strict_schema = sanitize_and_enforce_required(strict_schema)

            # Validate the resulting schema
            if self._validate_strict_schema_requirements(
                strict_schema, tool_name
            ):
                return strict_schema
            else:
                logger.warning(
                    f"Converted schema for '{tool_name}' failed validation"
                )
                return None

        except Exception as e:
            logger.warning(
                f"Error converting schema to strict mode for '{tool_name}': {e}"
            )
            return None

    def _apply_fallback_schema(
        self, tool: FunctionTool, tool_name: str, reason: str
    ) -> FunctionTool:
        """Apply fallback non-strict schema when strict mode cannot be used."""
        try:
            schema = tool.get_openai_tool_schema()

            # For severely malformed schemas, try to reconstruct a basic one
            if "function" not in schema or not isinstance(
                schema.get("function"), dict
            ):
                # Reconstruct basic schema from the function itself
                try:
                    from camel.toolkits.function_tool import (
                        get_openai_tool_schema,
                    )

                    basic_schema = get_openai_tool_schema(tool.func)
                    basic_schema["function"]["strict"] = False
                    tool.set_openai_tool_schema(basic_schema)
                    logger.warning(
                        f"Tool '{tool_name}' had malformed schema, reconstructed basic schema. "
                        f"Reason: {reason}. This may result in less reliable function calling."
                    )
                except Exception as reconstruct_error:
                    logger.error(
                        f"Failed to reconstruct schema for tool '{tool_name}': {reconstruct_error}. "
                        f"Tool may not function correctly."
                    )
            else:
                # Schema has function field, set to non-strict and apply basic fixes
                schema["function"]["strict"] = False

                # Even in non-strict mode, apply basic fixes for better reliability
                try:
                    from camel.toolkits.function_tool import (
                        sanitize_and_enforce_required,
                    )

                    # Apply sanitization but without strict mode constraints
                    fixed_schema = sanitize_and_enforce_required(schema)
                    # Ensure it's still set to non-strict after sanitization
                    fixed_schema["function"]["strict"] = False

                    # Perform a final validation to see if the schema would be acceptable to OpenAI
                    try:
                        from jsonschema.validators import (
                            Draft202012Validator as JSONValidator,
                        )

                        parameters = fixed_schema.get("function", {}).get(
                            "parameters", {}
                        )
                        JSONValidator.check_schema(parameters)
                        # If validation passes, use the fixed schema
                        tool.set_openai_tool_schema(fixed_schema)
                        logger.warning(
                            f"Tool '{tool_name}' using non-strict mode with basic fixes applied. "
                            f"Reason: {reason}. This may result in less reliable function calling."
                        )
                    except Exception as validation_error:
                        # If the fixed schema still fails validation, rebuild from scratch
                        logger.warning(
                            f"Fixed schema for tool '{tool_name}' still fails validation: {validation_error}. "
                            f"Rebuilding schema from function signature."
                        )
                        try:
                            from camel.toolkits.function_tool import (
                                get_openai_tool_schema,
                            )

                            basic_schema = get_openai_tool_schema(tool.func)
                            basic_schema["function"]["strict"] = False
                            tool.set_openai_tool_schema(basic_schema)
                            logger.warning(
                                f"Tool '{tool_name}' schema rebuilt from function signature. "
                                f"Original reason: {reason}. This may result in less reliable function calling."
                            )
                        except Exception as rebuild_error:
                            logger.error(
                                f"Failed to rebuild schema for tool '{tool_name}': {rebuild_error}. "
                                f"Tool may not function correctly."
                            )

                except Exception as fix_error:
                    # If fixing fails, rebuild from scratch instead of using broken schema
                    logger.warning(
                        f"Tool '{tool_name}' schema fixing failed: {fix_error}. "
                        f"Rebuilding schema from function signature."
                    )
                    try:
                        from camel.toolkits.function_tool import (
                            get_openai_tool_schema,
                        )

                        basic_schema = get_openai_tool_schema(tool.func)
                        basic_schema["function"]["strict"] = False
                        tool.set_openai_tool_schema(basic_schema)
                        logger.warning(
                            f"Tool '{tool_name}' schema rebuilt from function signature. "
                            f"Original reason: {reason}. This may result in less reliable function calling."
                        )
                    except Exception as rebuild_error:
                        logger.error(
                            f"Failed to rebuild schema for tool '{tool_name}': {rebuild_error}. "
                            f"Tool may not function correctly."
                        )

        except Exception as e:
            logger.error(
                f"Failed to apply fallback schema for tool '{tool_name}': {e}"
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
        for i, client in enumerate(self.clients):
            try:
                client_tools = client.get_tools()

                # Ensure all tools have strict schemas
                strict_tools = []
                for tool in client_tools:
                    strict_tool = self._ensure_strict_tool_schema(tool)
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
