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


from typing import Callable, Dict, List, Union, Any
from camel.toolkits import FunctionTool
from camel.agents._utils import convert_to_function_tool, convert_to_schema

class ToolManager:
    r"""
    Class for unified management of internal and external tools for CAMEL Agents.

    The `ToolManager` is responsible for handling all tool-related operations for agents,
    including adding, removing, and retrieving both internal tools (used directly by the agent)
    and external tool schemas (for tools handled externally or by other systems).
    This class ensures tool name uniqueness, provides a single source of truth for tool
    management, and decouples tool logic from the main agent workflow.

    Attributes:
        _internal_tools (Dict[str, FunctionTool]): Dictionary of internal tools, keyed by function name.
        _external_tool_schemas (Dict[str, dict]): Dictionary of external tool schemas, keyed by tool name.
    """
    def __init__(self):
        self._internal_tools: Dict[str, FunctionTool] = {}
        self._external_tool_schemas: Dict[str, dict] = {}

    def add_tool(self, tool: Union[FunctionTool, Callable]) -> None:
        new_tool = convert_to_function_tool(tool)
        self._internal_tools[new_tool.get_function_name()] = new_tool

    def add_tools(self, tools: List[Union[FunctionTool, Callable]]) -> None:
        for tool in tools:
            self.add_tool(tool)

    def remove_tool(self, tool_name: str) -> bool:
        r"""Remove a tool from the agent by name.

        Args:
            tool_name (str): The name of the tool to remove.

        Returns:
            bool: Whether the tool was successfully removed.
        """
        if tool_name in self._internal_tools:
            del self._internal_tools[tool_name]
            return True
        return False

    def remove_tools(self, tool_names: List[str]) -> None:
        r"""Remove a list of tools from the agent by name."""
        for name in tool_names:
            self.remove_tool(name)

    def add_external_tool(self, tool: Union[FunctionTool, Callable, Dict[str, Any]]) -> None:
        new_tool_schema = convert_to_schema(tool)
        self._external_tool_schemas[new_tool_schema["name"]] = new_tool_schema

    def add_external_tools(self, tools: List[Union[FunctionTool, Callable, Dict[str, Any]]]) -> None:
        for tool in tools:
            self.add_external_tool(tool)

    def remove_external_tool(self, tool_name: str) -> bool:
        r"""Remove an external tool from the agent by name.

        Args:
            tool_name (str): The name of the tool to remove.

        Returns:
            bool: Whether the tool was successfully removed.
        """
        if tool_name in self._external_tool_schemas:
            del self._external_tool_schemas[tool_name]
            return True
        return False

    def get_internal_tools(self) -> Dict[str, FunctionTool]:
        return self._internal_tools

    def get_external_tool_schemas(self) -> Dict[str, dict]:
        return self._external_tool_schemas

    def get_full_tool_schemas(self) -> List[dict]:
        r"""Returns a list of tool schemas of all tools, including internal
         and external tools.
         """
        return list(self._external_tool_schemas.values()) + [
            tool.get_openai_tool_schema()
            for tool in self._internal_tools.values()
        ]
