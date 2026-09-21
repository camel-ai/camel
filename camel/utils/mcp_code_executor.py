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
MCP Code Executor

This module provides code execution capabilities for interacting with MCP
servers. Instead of direct tool calls, agents write code that uses generated
APIs to call MCP tools, reducing token consumption and enabling better
tool composition.

Based on: https://www.anthropic.com/engineering/code-execution-with-mcp
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

from camel.logger import get_logger

if TYPE_CHECKING:
    from camel.toolkits.mcp_toolkit import MCPToolkit

logger = get_logger(__name__)


class MCPCodeExecutor:
    r"""Executor for running agent code that interacts with MCP servers.

    This class manages the execution of code that calls MCP tools through
    generated APIs. It maintains references to the MCP toolkit and provides
    a singleton instance for global access from generated code.

    Args:
        mcp_toolkit (MCPToolkit): The MCP toolkit instance managing server
            connections.
        workspace_dir (str): Directory where code APIs and skills are stored.

    Attributes:
        mcp_toolkit (MCPToolkit): The MCP toolkit instance.
        workspace_dir (Path): Path to the workspace directory.
        _instance (Optional[MCPCodeExecutor]): Singleton instance for global
            access.

    Example:
        >>> from camel.toolkits.mcp_toolkit import MCPToolkit
        >>> toolkit = MCPToolkit(config_path="config.json")
        >>> await toolkit.connect()
        >>> executor = MCPCodeExecutor(toolkit, "/path/to/workspace")
        >>> await executor.generate_apis()
        >>> # Agents can now write code using the generated APIs
    """

    _instance: Optional["MCPCodeExecutor"] = None

    def __init__(self, mcp_toolkit: "MCPToolkit", workspace_dir: str) -> None:
        self.mcp_toolkit = mcp_toolkit
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Set singleton instance for global access
        MCPCodeExecutor._instance = self

        logger.info(
            f"Initialized MCPCodeExecutor with workspace: {workspace_dir}"
        )

    @classmethod
    def get_instance(cls) -> Optional["MCPCodeExecutor"]:
        r"""Get the singleton instance of MCPCodeExecutor.

        Returns:
            Optional[MCPCodeExecutor]: The current instance, or None if not
                initialized.
        """
        return cls._instance

    async def generate_apis(self) -> None:
        r"""Generate code APIs for all connected MCP servers.

        This creates a file tree structure representing all available MCP
        tools as Python modules that agents can import and use.
        """
        from camel.utils.mcp_code_generator import MCPCodeGenerator

        generator = MCPCodeGenerator(str(self.workspace_dir))

        # Ensure toolkit is connected
        if not self.mcp_toolkit.is_connected:
            await self.mcp_toolkit.connect()

        # Generate API for each client
        for i, client in enumerate(self.mcp_toolkit.clients):
            # Get server name (try to extract from config or use index)
            server_name = f"server_{i}"
            if hasattr(client, "config") and hasattr(client.config, "command"):
                # Try to extract name from command
                command = client.config.command
                if command:
                    # Use the package name as server name
                    if "server-" in command:
                        parts = command.split("server-")
                        if len(parts) > 1:
                            server_name = parts[-1].strip("/")
                    else:
                        server_name = command.replace("/", "_")

            # Get tools from the client
            tools = client._tools

            if tools:
                generator.generate_server_api(server_name, tools)
                logger.info(
                    f"Generated API for {server_name} with {len(tools)} tools"
                )

        # Generate supporting files
        generator.generate_main_client()
        generator.generate_skills_structure()

        logger.info("Successfully generated all MCP APIs")

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        r"""Call an MCP tool through the toolkit.

        This method is called by generated code to execute MCP tools.

        Args:
            server_name (str): Name of the MCP server.
            tool_name (str): Name of the tool to call.
            arguments (Dict[str, Any]): Arguments to pass to the tool.

        Returns:
            Dict[str, Any]: The tool's response.

        Raises:
            RuntimeError: If the toolkit is not connected.
            ValueError: If the tool is not found.
        """
        if not self.mcp_toolkit.is_connected:
            raise RuntimeError(
                "MCP toolkit is not connected. "
                "Call connect() on the toolkit first."
            )

        # Find the appropriate client
        # For now, try to call the tool on all clients
        result = await self.mcp_toolkit.call_tool(tool_name, arguments)

        # Process the result to return a simple dict
        if hasattr(result, "content") and result.content:
            content = result.content[0]
            if hasattr(content, "text"):
                return {"result": content.text, "type": "text"}
            elif hasattr(content, "data"):
                return {"result": content.data, "type": "data"}
            else:
                return {"result": str(content), "type": "unknown"}
        else:
            return {"result": str(result), "type": "raw"}

    def get_workspace_info(self) -> Dict[str, Any]:
        r"""Get information about the workspace structure.

        Returns:
            Dict[str, Any]: Information including available servers, tools,
                and skills.
        """
        from camel.utils.mcp_code_generator import MCPCodeGenerator

        generator = MCPCodeGenerator(str(self.workspace_dir))

        return {
            "workspace_dir": str(self.workspace_dir),
            "available_tools": generator.list_available_tools(),
            "directory_tree": generator.get_directory_tree(),
        }

    def get_execution_context(self) -> Dict[str, Any]:
        r"""Get the execution context for running agent code.

        Returns a dictionary that can be used as the globals/locals context
        when executing agent-generated code.

        Returns:
            Dict[str, Any]: Execution context with necessary imports and
                utilities.
        """
        import sys

        # Add workspace to Python path
        workspace_str = str(self.workspace_dir)
        if workspace_str not in sys.path:
            sys.path.insert(0, workspace_str)

        # Return basic context
        context = {
            "__builtins__": __builtins__,
            "workspace_dir": str(self.workspace_dir),
        }

        return context

    async def execute_code(self, code: str) -> Any:
        r"""Execute agent-generated code that interacts with MCP tools.

        Args:
            code (str): Python code to execute.

        Returns:
            Any: The result of the code execution.

        Raises:
            Exception: Any exception raised during code execution.
        """
        # Get execution context
        context = self.get_execution_context()

        # Execute the code
        try:
            # Use exec for statements, eval for expressions
            try:
                # Try as expression first
                result = eval(code, context)
                return result
            except SyntaxError:
                # Execute as statements
                exec(code, context)
                # Return the last assigned variable if any
                if "result" in context:
                    return context["result"]
                return None
        except Exception as e:
            logger.error(f"Error executing code: {e}")
            raise

    def cleanup(self) -> None:
        r"""Clean up the workspace and generated files."""
        from camel.utils.mcp_code_generator import MCPCodeGenerator

        generator = MCPCodeGenerator(str(self.workspace_dir))
        generator.cleanup()

        logger.info("Cleaned up MCPCodeExecutor workspace")


# Global function for calling MCP tools from generated code
async def call_mcp_tool(
    server_name: str, tool_name: str, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    r"""Global function to call MCP tools from generated code.

    This function is used by the generated tool wrapper code to execute
    MCP tool calls.

    Args:
        server_name (str): Name of the MCP server.
        tool_name (str): Name of the tool to call.
        arguments (Dict[str, Any]): Arguments to pass to the tool.

    Returns:
        Dict[str, Any]: The tool's response.

    Raises:
        RuntimeError: If MCPCodeExecutor is not initialized.
    """
    executor = MCPCodeExecutor.get_instance()
    if executor is None:
        raise RuntimeError(
            "MCPCodeExecutor not initialized. "
            "Create an instance before calling tools."
        )

    return await executor.call_tool(server_name, tool_name, arguments)
