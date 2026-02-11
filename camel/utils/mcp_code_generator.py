# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

"""
MCP Code Generator

This module generates code API representations for MCP servers, enabling
agents to interact with MCP tools through code execution instead of
direct tool calls. This approach reduces token consumption and enables
better tool composition.

Based on: https://www.anthropic.com/engineering/code-execution-with-mcp
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import mcp.types as types

from camel.logger import get_logger

logger = get_logger(__name__)


class MCPCodeGenerator:
    r"""Generates code API representations for MCP servers.

    This class creates a file tree structure representing MCP servers and
    their tools as code APIs. Agents can then write code to interact with
    MCP tools instead of making direct tool calls, which reduces token
    consumption and enables better tool composition.

    Args:
        workspace_dir (str): Directory where the code API will be generated.
            Typically a 'workspace' directory for the agent.
        servers_dir (str, optional): Name of the servers directory within
            workspace. (default: :obj:`"servers"`)

    Attributes:
        workspace_dir (Path): Path to the workspace directory.
        servers_dir (Path): Path to the servers directory.

    Example:
        >>> generator = MCPCodeGenerator("/path/to/workspace")
        >>> generator.generate_server_api("google_drive", tools_list)
        >>> # Creates: /path/to/workspace/servers/google_drive/getDocument.py
    """

    def __init__(
        self, workspace_dir: str, servers_dir: str = "servers"
    ) -> None:
        self.workspace_dir = Path(workspace_dir)
        self.servers_dir = self.workspace_dir / servers_dir

        # Create workspace and servers directories if they don't exist
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.servers_dir.mkdir(parents=True, exist_ok=True)

    def generate_server_api(
        self, server_name: str, tools: List[types.Tool]
    ) -> None:
        r"""Generate code API for a single MCP server.

        Creates a directory structure for the server with individual files
        for each tool.

        Args:
            server_name (str): Name of the MCP server (e.g., "google_drive").
            tools (List[types.Tool]): List of tools available from this
                server.
        """
        server_dir = self.servers_dir / server_name
        server_dir.mkdir(parents=True, exist_ok=True)

        # Generate individual tool files
        for tool in tools:
            self._generate_tool_file(server_name, tool, server_dir)

        # Generate index file for the server
        self._generate_server_index(server_name, tools, server_dir)

        logger.info(
            f"Generated code API for server '{server_name}' "
            f"with {len(tools)} tools"
        )

    def _generate_tool_file(
        self, server_name: str, tool: types.Tool, server_dir: Path
    ) -> None:
        r"""Generate a Python file for a single tool.

        Args:
            server_name (str): Name of the MCP server.
            tool (types.Tool): The MCP tool definition.
            server_dir (Path): Directory where the tool file will be created.
        """
        tool_name = tool.name
        safe_tool_name = self._sanitize_name(tool_name)

        # Generate type hints from schema
        input_schema = tool.inputSchema
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        # Build parameter type hints
        param_defs = []
        for param_name, param_schema in properties.items():
            param_type = self._schema_type_to_python(param_schema)
            is_required = param_name in required
            if is_required:
                param_defs.append(f"    {param_name}: {param_type}")
            else:
                param_defs.append(
                    f"    {param_name}: Optional[{param_type}] = None"
                )

        params_str = ",\n".join(param_defs) if param_defs else ""

        # Generate the tool file content
        content = f'''# Auto-generated MCP tool wrapper for {tool_name}
from typing import Any, Dict, Optional
from camel.utils.mcp_code_executor import call_mcp_tool

async def {safe_tool_name}(
{params_str}
) -> Dict[str, Any]:
    """
    {tool.description or "No description provided."}

    This is an auto-generated wrapper for the MCP tool '{tool_name}'
    from server '{server_name}'.
    """
    arguments = {{}}
    {self._generate_argument_collection(properties.keys())}

    return await call_mcp_tool(
        server_name="{server_name}",
        tool_name="{tool_name}",
        arguments=arguments
    )
'''

        file_path = server_dir / f"{safe_tool_name}.py"
        file_path.write_text(content)
        logger.debug(f"Generated tool file: {file_path}")

    def _generate_argument_collection(
        self, param_names: List[str]
    ) -> str:
        r"""Generate code to collect arguments into a dictionary.

        Args:
            param_names (List[str]): List of parameter names.

        Returns:
            str: Python code for collecting arguments.
        """
        lines = []
        for param_name in param_names:
            lines.append(
                f"    if {param_name} is not None:\n"
                f"        arguments['{param_name}'] = {param_name}"
            )
        return "\n".join(lines) if lines else "    pass"

    def _generate_server_index(
        self, server_name: str, tools: List[types.Tool], server_dir: Path
    ) -> None:
        r"""Generate an index file that exports all tools from a server.

        Args:
            server_name (str): Name of the MCP server.
            tools (List[types.Tool]): List of tools from this server.
            server_dir (Path): Directory where the index file will be created.
        """
        imports = []
        exports = []

        for tool in tools:
            safe_name = self._sanitize_name(tool.name)
            imports.append(f"from .{safe_name} import {safe_name}")
            exports.append(f'    "{safe_name}",')

        content = f'''# Auto-generated index for {server_name} MCP server
"""
MCP server: {server_name}

This module provides access to all tools from the {server_name} MCP server.
"""

{chr(10).join(imports)}

__all__ = [
{chr(10).join(exports)}
]
'''

        index_path = server_dir / "__init__.py"
        index_path.write_text(content)
        logger.debug(f"Generated server index: {index_path}")

    def _schema_type_to_python(self, schema: Dict[str, Any]) -> str:
        r"""Convert JSON schema type to Python type hint.

        Args:
            schema (Dict[str, Any]): JSON schema for a parameter.

        Returns:
            str: Python type hint string.
        """
        schema_type = schema.get("type", "Any")

        type_map = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "List[Any]",
            "object": "Dict[str, Any]",
        }

        return type_map.get(schema_type, "Any")

    def _sanitize_name(self, name: str) -> str:
        r"""Sanitize a tool name to be a valid Python identifier.

        Args:
            name (str): The original tool name.

        Returns:
            str: A valid Python identifier.
        """
        # Replace invalid characters with underscores
        safe_name = "".join(
            c if c.isalnum() or c == "_" else "_" for c in name
        )

        # Ensure it doesn't start with a number
        if safe_name and safe_name[0].isdigit():
            safe_name = f"tool_{safe_name}"

        return safe_name

    def generate_main_client(self) -> None:
        r"""Generate a main client module for calling MCP tools.

        This creates a central module that agents can import to access
        the tool calling functionality.
        """
        content = '''# MCP Tool Client
"""
Central client for calling MCP tools from generated code.

This module provides the core functionality for executing MCP tool calls
from agent-generated code.
"""

from typing import Any, Dict


async def call_mcp_tool(
    server_name: str, tool_name: str, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Call an MCP tool through the registered executor.

    Args:
        server_name: Name of the MCP server.
        tool_name: Name of the tool to call.
        arguments: Arguments to pass to the tool.

    Returns:
        Dict containing the tool's response.
    """
    from camel.utils.mcp_code_executor import MCPCodeExecutor

    executor = MCPCodeExecutor.get_instance()
    if executor is None:
        raise RuntimeError(
            "MCPCodeExecutor not initialized. "
            "Create an instance before calling tools."
        )

    return await executor.call_tool(server_name, tool_name, arguments)
'''

        client_path = self.servers_dir / "client.py"
        client_path.write_text(content)
        logger.debug(f"Generated main client: {client_path}")

    def generate_skills_structure(self) -> None:
        r"""Generate the skills directory structure.

        Creates a skills directory where agents can save reusable code
        snippets and functions.
        """
        skills_dir = self.workspace_dir / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)

        # Create README for skills
        readme_content = '''# Skills Directory

This directory contains reusable code snippets and functions that the agent
has developed. Skills can be imported and used in future executions to avoid
regenerating common functionality.

## Usage

Agents can save useful functions here and import them in later tasks:

```python
from skills.my_skill import useful_function

result = useful_function(arg1, arg2)
```

## Structure

Each skill should be a separate Python file with clear documentation.
Skills can also include SKILL.md files with metadata and usage instructions.
'''

        readme_path = skills_dir / "README.md"
        readme_path.write_text(readme_content)

        # Create __init__.py
        init_path = skills_dir / "__init__.py"
        init_path.write_text('# Skills module\n')

        logger.info(f"Generated skills structure at {skills_dir}")

    def list_available_tools(self) -> Dict[str, List[str]]:
        r"""List all available tools organized by server.

        Returns:
            Dict[str, List[str]]: Dictionary mapping server names to
                lists of tool names.
        """
        available_tools: Dict[str, List[str]] = {}

        if not self.servers_dir.exists():
            return available_tools

        for server_dir in self.servers_dir.iterdir():
            if server_dir.is_dir() and not server_dir.name.startswith("_"):
                server_name = server_dir.name
                tools = []

                for file_path in server_dir.glob("*.py"):
                    if file_path.stem not in ["__init__", "client"]:
                        tools.append(file_path.stem)

                if tools:
                    available_tools[server_name] = tools

        return available_tools

    def get_directory_tree(self) -> str:
        r"""Generate a text representation of the directory tree.

        This can be used to show agents what tools are available.

        Returns:
            str: Text representation of the directory tree.
        """

        def build_tree(
            path: Path, prefix: str = "", is_last: bool = True
        ) -> List[str]:
            lines = []
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{path.name}")

            if path.is_dir():
                children = sorted(list(path.iterdir()))
                for i, child in enumerate(children):
                    is_last_child = i == len(children) - 1
                    extension = "    " if is_last else "│   "
                    lines.extend(
                        build_tree(child, prefix + extension, is_last_child)
                    )

            return lines

        if not self.servers_dir.exists():
            return "No servers directory found."

        tree_lines = [str(self.servers_dir)]
        for child in sorted(self.servers_dir.iterdir()):
            tree_lines.extend(build_tree(child, "", True))

        return "\n".join(tree_lines)

    def cleanup(self) -> None:
        r"""Remove all generated code API files.

        This is useful for regenerating the API or cleaning up after use.
        """
        import shutil

        if self.servers_dir.exists():
            shutil.rmtree(self.servers_dir)
            logger.info(f"Cleaned up servers directory: {self.servers_dir}")
