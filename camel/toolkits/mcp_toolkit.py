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
        requirements with enhanced fixing capabilities and fallback mechanisms.

        This method attempts to automatically fix schemas that don't comply
        with OpenAI's strict mode requirements. It provides multiple fallback
        strategies when automatic fixing fails.

        Args:
            tool (FunctionTool): The tool to check and update if necessary.

        Returns:
            FunctionTool: The tool with a strict schema or appropriate fallback.
        """
        original_schema = tool.get_openai_tool_schema().copy()
        tool_name = tool.get_function_name()
        
        try:
            schema = tool.get_openai_tool_schema()
            
            # Step 1: Try to fix schema issues automatically
            fixed_schema, fixes_applied = self._attempt_schema_fixes(schema, tool_name)
            
            # Step 2: Validate if the fixed schema is strict-mode compatible
            is_compatible, issues = self._validate_strict_compatibility(fixed_schema)
            
            if is_compatible:
                # Success: Apply the fixed schema
                tool.set_openai_tool_schema(fixed_schema)
                if fixes_applied:
                    logger.info(
                        f"Successfully fixed tool '{tool_name}' schema for strict mode. "
                        f"Applied fixes: {', '.join(fixes_applied)}"
                    )
                else:
                    logger.debug(f"Tool '{tool_name}' already compatible with strict mode")
                return tool
            
            # Step 3: Apply fallback mechanisms
            return self._apply_fallback_mechanisms(
                tool, original_schema, issues, tool_name
            )
            
        except Exception as e:
            logger.error(f"Error processing tool '{tool_name}': {e}")
            return self._emergency_fallback(tool, original_schema, tool_name)

    def _attempt_schema_fixes(self, schema: dict, tool_name: str) -> tuple:
        r"""Attempt to automatically fix common schema issues."""
        fixes_applied = []
        working_schema = schema.copy()
        
        # Fix 1: Convert additionalProperties: true to false
        if self._fix_additional_properties_true(working_schema):
            fixes_applied.append("converted additionalProperties:true to false")
        
        # Fix 2: Ensure all objects have additionalProperties: false
        if self._ensure_additional_properties_false(working_schema):
            fixes_applied.append("added missing additionalProperties:false")
        
        # Fix 3: Fix root-level anyOf (not allowed in strict mode)
        if self._fix_root_anyof(working_schema):
            fixes_applied.append("converted root-level anyOf to object wrapper")
        
        # Fix 4: Handle unsupported schema features
        if self._fix_unsupported_features(working_schema):
            fixes_applied.append("removed/converted unsupported schema features")
        
        # Fix 5: Ensure all properties are required with null type for optionals
        if self._fix_required_fields(working_schema):
            fixes_applied.append("made all fields required with null types for optionals")
        
        # Fix 6: Clarify ambiguous types and union handling
        if self._fix_ambiguous_types(working_schema):
            fixes_applied.append("clarified ambiguous parameter types")
        
        # Fix 7: Handle schema size limitations
        if self._fix_schema_limitations(working_schema):
            fixes_applied.append("applied schema size/complexity limits")
        
        # Fix 8: Apply sanitization if other fixes were successful
        if not self._has_critical_issues_preventing_sanitization(working_schema):
            try:
                from camel.toolkits.function_tool import sanitize_and_enforce_required
                working_schema = sanitize_and_enforce_required(working_schema)
                if fixes_applied:  # Only add if other fixes were applied
                    fixes_applied.append("applied schema sanitization")
            except Exception as e:
                logger.warning(f"Failed to apply sanitization to tool '{tool_name}': {e}")
        
        return working_schema, fixes_applied

    def _fix_additional_properties_true(self, schema: dict) -> bool:
        r"""Convert additionalProperties: true to false recursively."""
        fixes_made = False
        
        def _fix_recursive(obj):
            nonlocal fixes_made
            if isinstance(obj, dict):
                if obj.get("additionalProperties") is True:
                    obj["additionalProperties"] = False
                    fixes_made = True
                for value in obj.values():
                    _fix_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    _fix_recursive(item)
        
        _fix_recursive(schema)
        return fixes_made

    def _ensure_additional_properties_false(self, schema: dict) -> bool:
        r"""Ensure all object types have additionalProperties: false."""
        fixes_made = False
        
        def _ensure_recursive(obj):
            nonlocal fixes_made
            if isinstance(obj, dict):
                if (obj.get("type") == "object" and 
                    "additionalProperties" not in obj):
                    obj["additionalProperties"] = False
                    fixes_made = True
                for value in obj.values():
                    _ensure_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    _ensure_recursive(item)
        
        _ensure_recursive(schema)
        return fixes_made

    def _fix_root_anyof(self, schema: dict) -> bool:
        r"""Fix root-level anyOf which is not allowed in strict mode."""
        if (schema.get("function", {}).get("parameters", {}).get("anyOf")):
            # Wrap anyOf in an object structure
            params = schema["function"]["parameters"]
            anyof_content = params.pop("anyOf")
            
            # Create a wrapper object
            params.update({
                "type": "object",
                "properties": {
                    "data": {
                        "anyOf": anyof_content
                    }
                },
                "required": ["data"],
                "additionalProperties": False
            })
            return True
        return False

    def _fix_unsupported_features(self, schema: dict) -> bool:
        r"""Remove or convert unsupported schema features."""
        fixes_made = False
        unsupported_keywords = ["allOf", "not", "dependentRequired", 
                               "dependentSchemas", "if", "then", "else"]
        
        def _remove_unsupported(obj):
            nonlocal fixes_made
            if isinstance(obj, dict):
                for keyword in list(obj.keys()):
                    if keyword in unsupported_keywords:
                        # Try to handle specific cases
                        if keyword == "allOf" and isinstance(obj[keyword], list):
                            # Merge allOf into single object (simple case)
                            all_of = obj.pop(keyword)
                            if len(all_of) == 1 and isinstance(all_of[0], dict):
                                obj.update(all_of[0])
                                fixes_made = True
                            elif len(all_of) > 1:
                                # Merge multiple objects (basic merge)
                                merged = {}
                                for item in all_of:
                                    if isinstance(item, dict):
                                        merged.update(item)
                                obj.update(merged)
                                fixes_made = True
                        else:
                            # Remove unsupported keyword
                            obj.pop(keyword)
                            fixes_made = True
                
                for value in obj.values():
                    _remove_unsupported(value)
            elif isinstance(obj, list):
                for item in obj:
                    _remove_unsupported(item)
        
        _remove_unsupported(schema)
        return fixes_made

    def _fix_required_fields(self, schema: dict) -> bool:
        r"""Ensure all fields are marked as required."""
        fixes_made = False
        
        if "function" in schema and "parameters" in schema["function"]:
            params = schema["function"]["parameters"]
            properties = params.get("properties", {})
            
            if properties:
                current_required = set(params.get("required", []))
                all_properties = set(properties.keys())
                
                if current_required != all_properties:
                    params["required"] = list(all_properties)
                    fixes_made = True
        
        return fixes_made

    def _fix_schema_limitations(self, schema: dict) -> bool:
        r"""Apply OpenAI schema size and complexity limitations."""
        fixes_made = False
        
        # Count object properties (max 5000)
        property_count = self._count_object_properties(schema)
        if property_count > 5000:
            # Simplify schema by removing less important properties
            fixes_made = True
            logger.warning(f"Schema has {property_count} properties, exceeding limit of 5000")
        
        # Check nesting depth (max 5 levels)
        max_depth = self._get_max_nesting_depth(schema)
        if max_depth > 5:
            fixes_made = True
            logger.warning(f"Schema nesting depth {max_depth} exceeds limit of 5")
        
        return fixes_made

    def _count_object_properties(self, obj, count=0):
        r"""Count total object properties in schema."""
        if isinstance(obj, dict):
            if "properties" in obj:
                count += len(obj["properties"])
            for value in obj.values():
                count = self._count_object_properties(value, count)
        elif isinstance(obj, list):
            for item in obj:
                count = self._count_object_properties(item, count)
        return count

    def _get_max_nesting_depth(self, obj, current_depth=0):
        r"""Get maximum nesting depth of schema."""
        max_depth = current_depth
        if isinstance(obj, dict):
            for value in obj.values():
                depth = self._get_max_nesting_depth(value, current_depth + 1)
                max_depth = max(max_depth, depth)
        elif isinstance(obj, list):
            for item in obj:
                depth = self._get_max_nesting_depth(item, current_depth)
                max_depth = max(max_depth, depth)
        return max_depth

    def _has_critical_issues_preventing_sanitization(self, schema: dict) -> bool:
        r"""Check if schema has critical issues that prevent sanitization."""
        # Check for structural issues that would break sanitization
        if not isinstance(schema, dict):
            return True
        
        function_schema = schema.get("function", {})
        if not isinstance(function_schema, dict):
            return True
            
        parameters = function_schema.get("parameters", {})
        if parameters and not isinstance(parameters, dict):
            return True
            
        return False

    def _validate_strict_compatibility(self, schema: dict) -> tuple:
        r"""Validate if schema is compatible with OpenAI strict mode."""
        issues = []
        
        # Check for unsupported features
        if self._has_unsupported_features(schema):
            issues.append("contains unsupported schema features")
        
        # Check additionalProperties
        if self._has_additional_properties_true(schema):
            issues.append("contains additionalProperties: true")
        
        # Check root anyOf
        if self._has_root_anyof(schema):
            issues.append("has root-level anyOf")
        
        # Check required fields
        if not self._all_fields_required(schema):
            issues.append("not all fields are marked as required")
        
        # Check schema size limits
        if self._count_object_properties(schema) > 5000:
            issues.append("exceeds 5000 property limit")
            
        if self._get_max_nesting_depth(schema) > 5:
            issues.append("exceeds 5-level nesting limit")
        
        return len(issues) == 0, issues

    def _has_unsupported_features(self, schema: dict) -> bool:
        r"""Check for unsupported schema features."""
        unsupported = ["allOf", "not", "dependentRequired", "dependentSchemas", 
                      "if", "then", "else"]
        
        def _check_recursive(obj):
            if isinstance(obj, dict):
                if any(keyword in obj for keyword in unsupported):
                    return True
                return any(_check_recursive(v) for v in obj.values())
            elif isinstance(obj, list):
                return any(_check_recursive(item) for item in obj)
            return False
        
        return _check_recursive(schema)

    def _has_additional_properties_true(self, schema: dict) -> bool:
        r"""Check if schema has additionalProperties: true."""
        def _check_recursive(obj):
            if isinstance(obj, dict):
                if obj.get("additionalProperties") is True:
                    return True
                return any(_check_recursive(v) for v in obj.values())
            elif isinstance(obj, list):
                return any(_check_recursive(item) for item in obj)
            return False
        
        return _check_recursive(schema)

    def _has_root_anyof(self, schema: dict) -> bool:
        r"""Check for root-level anyOf."""
        return bool(schema.get("function", {}).get("parameters", {}).get("anyOf"))

    def _all_fields_required(self, schema: dict) -> bool:
        r"""Check if all fields are marked as required."""
        if "function" in schema and "parameters" in schema["function"]:
            params = schema["function"]["parameters"]
            properties = params.get("properties", {})
            required = params.get("required", [])
            return set(required) == set(properties.keys())
        return True

    def _apply_fallback_mechanisms(self, tool: FunctionTool, original_schema: dict, 
                                  issues: list, tool_name: str) -> FunctionTool:
        r"""Apply fallback mechanisms when automatic fixing fails."""
        
        # Fallback Strategy 1: Try aggressive fixing with schema simplification
        try:
            simplified_schema = self._create_simplified_schema(original_schema)
            is_compatible, _ = self._validate_strict_compatibility(simplified_schema)
            
            if is_compatible:
                tool.set_openai_tool_schema(simplified_schema)
                logger.info(
                    f"Applied simplified strict schema for tool '{tool_name}' "
                    f"after initial fixes failed"
                )
                return tool
        except Exception as e:
            logger.warning(f"Schema simplification failed for tool '{tool_name}': {e}")
        
        # Fallback Strategy 2: Force non-strict mode with original schema
        fallback_schema = original_schema.copy()
        if "function" in fallback_schema:
            fallback_schema["function"]["strict"] = False
        
        tool.set_openai_tool_schema(fallback_schema)
        logger.warning(
            f"Tool '{tool_name}' could not be made strict-mode compatible. "
            f"Issues: {', '.join(issues)}. "
            f"Falling back to non-strict mode."
        )
        
        return tool

    def _create_simplified_schema(self, original_schema: dict) -> dict:
        r"""Create a maximally simplified version of the schema for strict mode."""
        schema = original_schema.copy()
        
        if "function" not in schema or "parameters" not in schema["function"]:
            return schema
            
        # Force basic strict mode structure
        schema["function"]["strict"] = True
        params = schema["function"]["parameters"]
        
        # Simplify parameters to basic object structure
        if isinstance(params, dict):
            params["type"] = "object"
            params["additionalProperties"] = False
            
            # Keep only string/number/boolean properties, simplify complex ones
            properties = params.get("properties", {})
            simplified_properties = {}
            
            for prop_name, prop_schema in properties.items():
                if isinstance(prop_schema, dict):
                    prop_type = prop_schema.get("type", "string")
                    if prop_type in ["string", "number", "boolean", "integer"]:
                        simplified_properties[prop_name] = {
                            "type": prop_type,
                            "description": prop_schema.get("description", "")
                        }
                    else:
                        # Convert complex types to string
                        simplified_properties[prop_name] = {
                            "type": "string",
                            "description": prop_schema.get("description", "")
                        }
            
            params["properties"] = simplified_properties
            params["required"] = list(simplified_properties.keys())
        
        return schema

    def _emergency_fallback(self, tool: FunctionTool, original_schema: dict, 
                           tool_name: str) -> FunctionTool:
        r"""Emergency fallback when all else fails."""
        try:
            # Create minimal working schema
            minimal_schema = {
                "type": "function",
                "function": {
                    "name": original_schema.get("function", {}).get("name", tool_name),
                    "description": original_schema.get("function", {}).get("description", "Tool function"),
                    "strict": False,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": True
                    }
                }
            }
            
            tool.set_openai_tool_schema(minimal_schema)
            logger.error(
                f"Applied emergency fallback for tool '{tool_name}': "
                f"using minimal schema with no parameters"
            )
        except Exception as e:
            logger.error(f"Emergency fallback failed for tool '{tool_name}': {e}")
        
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
