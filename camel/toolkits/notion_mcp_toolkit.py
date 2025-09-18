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

from typing import Any, ClassVar, Dict, List, Optional, Set

from camel.toolkits import FunctionTool

from .mcp_toolkit import MCPToolkit


class NotionMCPToolkit(MCPToolkit):
    r"""NotionMCPToolkit provides an interface for interacting with Notion
    through the Model Context Protocol (MCP).

    Attributes:
        timeout (Optional[float]): Connection timeout in seconds.
            (default: :obj:`None`)

    Note:
        Currently only supports asynchronous operation mode.
    """

    # TODO: Create unified method to validate and fix the schema
    SCHEMA_KEYWORDS: ClassVar[Set[str]] = {
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

    def __init__(
        self,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes the NotionMCPToolkit.

        Args:
            timeout (Optional[float]): Connection timeout in seconds.
                (default: :obj:`None`)
        """
        config_dict = {
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
        }

        # Initialize parent MCPToolkit with Notion configuration
        super().__init__(config_dict=config_dict, timeout=timeout)

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of tools provided by the NotionMCPToolkit.

        Returns:
            List[FunctionTool]: List of available tools.
        """
        all_tools = []
        for client in self.clients:
            try:
                original_build_schema = client._build_tool_schema

                def create_wrapper(orig_func):
                    def wrapper(mcp_tool):
                        return self._build_notion_tool_schema(
                            mcp_tool, orig_func
                        )

                    return wrapper

                client._build_tool_schema = create_wrapper(  # type: ignore[method-assign]
                    original_build_schema
                )

                client_tools = client.get_tools()
                all_tools.extend(client_tools)

                client._build_tool_schema = original_build_schema  # type: ignore[method-assign]

            except Exception as e:
                from camel.logger import get_logger

                logger = get_logger(__name__)
                logger.error(f"Failed to get tools from client: {e}")

        return all_tools

    def _build_notion_tool_schema(self, mcp_tool, original_build_schema):
        r"""Build tool schema with Notion-specific fixes."""
        schema = original_build_schema(mcp_tool)
        self._fix_notion_schema_recursively(schema)
        return schema

    def _fix_notion_schema_recursively(self, obj: Any) -> None:
        r"""Recursively fix Notion MCP schema issues."""
        if isinstance(obj, dict):
            self._fix_dict_schema(obj)
            self._process_nested_structures(obj)
        elif isinstance(obj, list):
            for item in obj:
                self._fix_notion_schema_recursively(item)

    def _fix_dict_schema(self, obj: Dict[str, Any]) -> None:
        r"""Fix dictionary schema issues."""
        if "properties" in obj and "type" not in obj:
            self._fix_missing_type_with_properties(obj)
        elif obj.get("type") == "object" and "properties" in obj:
            self._fix_object_with_properties(obj)

    def _fix_missing_type_with_properties(self, obj: Dict[str, Any]) -> None:
        r"""Fix objects with properties but missing type field."""
        properties = obj.get("properties", {})
        if properties and isinstance(properties, dict):
            obj["type"] = "object"
            obj["additionalProperties"] = False

            required_properties = self._get_required_properties(
                properties, conservative=True
            )
            if required_properties:
                obj["required"] = required_properties

    def _fix_object_with_properties(self, obj: Dict[str, Any]) -> None:
        r"""Fix objects with type="object" and properties."""
        properties = obj.get("properties", {})
        if properties and isinstance(properties, dict):
            existing_required = obj.get("required", [])

            for prop_name, prop_schema in properties.items():
                if (
                    prop_name not in existing_required
                    and prop_name not in self.SCHEMA_KEYWORDS
                    and self._is_property_required(prop_schema)
                ):
                    existing_required.append(prop_name)

            if existing_required:
                obj["required"] = existing_required

            if "additionalProperties" not in obj:
                obj["additionalProperties"] = False

    def _get_required_properties(
        self, properties: Dict[str, Any], conservative: bool = False
    ) -> List[str]:
        r"""Get list of required properties from a properties dict."""
        required = []
        for prop_name, prop_schema in properties.items():
            if (
                prop_name not in self.SCHEMA_KEYWORDS
                and isinstance(prop_schema, dict)
                and self._is_property_required(prop_schema)
            ):
                required.append(prop_name)
        return required

    def _is_property_required(self, prop_schema: Dict[str, Any]) -> bool:
        r"""Check if a property should be marked as required."""
        prop_type = prop_schema.get("type")
        return (
            prop_type is not None
            and prop_type != "null"
            and "default" not in prop_schema
            and not (isinstance(prop_type, list) and "null" in prop_type)
        )

    def _process_nested_structures(self, obj: Dict[str, Any]) -> None:
        r"""Process all nested structures in a schema object."""
        for key, value in obj.items():
            if key in ["anyOf", "oneOf", "allOf"] and isinstance(value, list):
                for item in value:
                    self._fix_notion_schema_recursively(item)
            elif key == "items" and isinstance(value, dict):
                self._fix_notion_schema_recursively(value)
            elif key == "properties" and isinstance(value, dict):
                for prop_value in value.values():
                    self._fix_notion_schema_recursively(prop_value)
            elif key == "$defs" and isinstance(value, dict):
                for def_value in value.values():
                    self._fix_notion_schema_recursively(def_value)
            elif isinstance(value, (dict, list)):
                self._fix_notion_schema_recursively(value)
