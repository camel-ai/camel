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

from typing import List, Optional

from camel.toolkits import BaseToolkit, FunctionTool

from .mcp_toolkit import MCPToolkit


class NotionMCPToolkit(BaseToolkit):
    r"""NotionMCPToolkit provides an interface for interacting with Notion
    through the Model Context Protocol (MCP).

    Attributes:
        timeout (Optional[float]): Connection timeout in seconds.
            (default: :obj:`None`)

    Note:
        Currently only supports asynchronous operation mode.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes the NotionMCPToolkit.

        Args:
            timeout (Optional[float]): Connection timeout in seconds.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

        self._mcp_toolkit = MCPToolkit(
            config_dict={
                "mcpServers": {
                    "notionMCP": {
                        "command": "npx",
                        "args": [
                            "-y",
                            "mcp-remote",
                            "https://mcp.notion.com/mcp",
                        ],
                    }
                }
            },
            timeout=timeout,
        )

    async def connect(self):
        r"""Explicitly connect to the Notion MCP server."""
        await self._mcp_toolkit.connect()

    async def disconnect(self):
        r"""Explicitly disconnect from the Notion MCP server."""
        await self._mcp_toolkit.disconnect()

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of tools provided by the NotionMCPToolkit.

        Returns:
            List[FunctionTool]: List of available tools.
        """
        # Get tools directly from clients without going
        # through MCPToolkit.get_tools()
        # to avoid the _ensure_strict_tool_schema processing
        # that conflicts with our fix
        all_tools = []
        for client in self._mcp_toolkit.clients:
            try:
                # Temporarily override the client's _build_tool_schema method
                original_build_schema = client._build_tool_schema

                # Create a proper closure to avoid B023 lint warning
                def make_build_schema_wrapper(orig_func):
                    def wrapper(mcp_tool):
                        return self._build_notion_tool_schema(
                            mcp_tool, orig_func
                        )

                    return wrapper

                client._build_tool_schema = make_build_schema_wrapper(
                    original_build_schema
                )

                # Get tools directly from the client
                client_tools = client.get_tools()
                all_tools.extend(client_tools)

                # Restore original method
                client._build_tool_schema = original_build_schema

            except Exception as e:
                from camel.logger import get_logger

                logger = get_logger(__name__)
                logger.error(f"Failed to get tools from client: {e}")

        return all_tools

    def _build_notion_tool_schema(self, mcp_tool, original_build_schema):
        r"""Build tool schema with Notion-specific fixes."""
        # Get the original schema
        schema = original_build_schema(mcp_tool)

        # Apply our custom fixing to the schema
        self._fix_notion_schema_recursively(schema)

        return schema

    def _fix_notion_schema_recursively(self, obj):
        r"""Recursively fix Notion MCP schema issues,
        including deep nested anyOf structures."""
        if isinstance(obj, dict):
            # Handle special case: object with properties but missing
            # type field
            # This MUST be checked first before the type=="object" check
            if "properties" in obj and "type" not in obj:
                # This object has properties but no type,
                # assume it should be "object"
                properties = obj.get("properties", {})
                if properties and isinstance(properties, dict):
                    obj["type"] = "object"
                    obj["additionalProperties"] = False

                    # For objects that were missing type,
                    # we should be more conservative
                    # about adding required fields - only add ones
                    # that seem truly required
                    schema_keywords = {
                        "type",
                        "properties",
                        "items",
                        "required",
                        "additionalProperties",
                        "description",
                        "title",
                        "default",
                        "enum",
                        "const",
                        "examples",
                        "$ref",
                        "$defs",
                        "definitions",
                        "allOf",
                        "oneOf",
                        "anyOf",
                        "not",
                        "if",
                        "then",
                        "else",
                        "format",
                        "pattern",
                        "minimum",
                        "maximum",
                        "minLength",
                        "maxLength",
                        "minItems",
                        "maxItems",
                        "uniqueItems",
                    }

                    required_properties = []
                    for prop_name, prop_schema in properties.items():
                        if prop_name not in schema_keywords:
                            # Only add if it seems required
                            # (no null type, no default)
                            if isinstance(prop_schema, dict):
                                prop_type = prop_schema.get("type")
                                if (
                                    prop_type
                                    and prop_type != "null"
                                    and "default" not in prop_schema
                                    and not (
                                        isinstance(prop_type, list)
                                        and "null" in prop_type
                                    )
                                ):
                                    required_properties.append(prop_name)

                    if required_properties:
                        obj["required"] = required_properties

            # Fix objects with properties but missing required fields
            elif obj.get("type") == "object" and "properties" in obj:
                properties = obj.get("properties", {})
                if properties and isinstance(properties, dict):
                    # Only add actual property names to required,
                    # not schema keywords
                    schema_keywords = {
                        "type",
                        "properties",
                        "items",
                        "required",
                        "additionalProperties",
                        "description",
                        "title",
                        "default",
                        "enum",
                        "const",
                        "examples",
                        "$ref",
                        "$defs",
                        "definitions",
                        "allOf",
                        "oneOf",
                        "anyOf",
                        "not",
                        "if",
                        "then",
                        "else",
                        "format",
                        "pattern",
                        "minimum",
                        "maximum",
                        "minLength",
                        "maxLength",
                        "minItems",
                        "maxItems",
                        "uniqueItems",
                    }

                    # Get existing required fields to preserve
                    # original requirements
                    existing_required = obj.get("required", [])

                    # Only add properties that don't already
                    # have required field
                    # and are not schema keywords
                    for prop_name in properties.keys():
                        if (
                            prop_name not in existing_required
                            and prop_name not in schema_keywords
                        ):
                            # Check if this property is actually required
                            # based on original schema
                            # For now, only add if it doesn't have a
                            # default or null type
                            prop_schema = properties[prop_name]
                            if isinstance(prop_schema, dict):
                                # Skip optional properties
                                prop_type = prop_schema.get("type")
                                if (
                                    prop_type != "null"
                                    and "default" not in prop_schema
                                    and not (
                                        isinstance(prop_type, list)
                                        and "null" in prop_type
                                    )
                                ):
                                    existing_required.append(prop_name)

                    if existing_required:
                        obj["required"] = existing_required

                    # Ensure additionalProperties is false for strict mode
                    if "additionalProperties" not in obj:
                        obj["additionalProperties"] = False

            # Recursively process all nested values,
            # including anyOf, oneOf, allOf
            for key, value in obj.items():
                if key in ["anyOf", "oneOf", "allOf"] and isinstance(
                    value, list
                ):
                    # Handle schema combination structures
                    for item in value:
                        self._fix_notion_schema_recursively(item)
                elif key == "items" and isinstance(value, dict):
                    # Handle array items
                    self._fix_notion_schema_recursively(value)
                elif key == "properties" and isinstance(value, dict):
                    # Handle object properties
                    for prop_value in value.values():
                        self._fix_notion_schema_recursively(prop_value)
                elif key == "$defs" and isinstance(value, dict):
                    # Handle schema definitions
                    for def_value in value.values():
                        self._fix_notion_schema_recursively(def_value)
                elif isinstance(value, (dict, list)):
                    # Handle other nested structures
                    self._fix_notion_schema_recursively(value)

        elif isinstance(obj, list):
            # Process each item in the list
            for item in obj:
                self._fix_notion_schema_recursively(item)
