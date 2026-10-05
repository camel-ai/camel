from typing import Dict, List, Optional, Union, Any
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.toolkits.mcp_toolkit import MCPClient, MCPToolkit
from camel.utils import dependencies_required


class EditorControlToolkit(BaseToolkit):
    r"""A toolkit for controlling various code editors through MCP protocol.

    Supports windsurf, cursor, aider, celine and other editors that implement
    MCP protocol for agent interaction.
    """

    def __init__(
            self,
            editor_configs: Optional[Dict[str, Dict[str, Any]]] = None,
            timeout: Optional[float] = 30.0,
    ):
        self.editor_configs = editor_configs or self._get_default_configs()
        self.timeout = timeout
        self.mcp_clients: Dict[str, MCPClient] = {}
        self._initialize_clients()

    def _get_default_configs(self) -> Dict[str, Dict[str, Any]]:
        """Default configurations for supported editors."""
        return {
            "windsurf": {
                "command": "windsurf",
                "args": ["--mcp-server"],
                "port": 8001,
            },
            "cursor": {
                "command": "cursor",
                "args": ["--enable-mcp"],
                "port": 8002,
            },
            "aider": {
                "command": "aider",
                "args": ["--mcp-mode"],
                "port": 8003,
            },
            "celine": {
                "command": "celine",
                "args": ["--mcp-server"],
                "port": 8004,
            }
        }

    def _initialize_clients(self):
        """Initialize MCP clients for each configured editor."""
        for editor_name, config in self.editor_configs.items():
            try:
                client = MCPClient(
                    command_or_url=config["command"],
                    args=config.get("args", []),
                    timeout=self.timeout
                )
                self.mcp_clients[editor_name] = client
            except Exception as e:
                print(f"Failed to initialize {editor_name} client: {e}")

    async def connect_editor(self, editor_name: str) -> bool:
        """Connect to a specific editor's MCP server."""
        if editor_name not in self.mcp_clients:
            return False

        try:
            await self.mcp_clients[editor_name].connect()
            return True
        except Exception as e:
            print(f"Failed to connect to {editor_name}: {e}")
            return False

    def open_file(self, editor_name: str, file_path: str) -> str:
        """Open a file in the specified editor."""
        if editor_name not in self.mcp_clients:
            return f"Editor {editor_name} not configured"

        try:
            # This would call the editor's MCP tool for opening files
            result = self.mcp_clients[editor_name].call_tool(
                "open_file",
                {"path": file_path}
            )
            return f"Opened {file_path} in {editor_name}"
        except Exception as e:
            return f"Failed to open file: {e}"

    def search_in_repository(self, editor_name: str, query: str, repo_path: str) -> str:
        """Search for code patterns in repository using editor's search capabilities."""
        if editor_name not in self.mcp_clients:
            return f"Editor {editor_name} not configured"

        try:
            result = self.mcp_clients[editor_name].call_tool(
                "search_repository",
                {
                    "query": query,
                    "path": repo_path,
                    "include_files": ["*.py", "*.js", "*.ts", "*.java"],
                }
            )
            return result
        except Exception as e:
            return f"Search failed: {e}"

    def review_code_changes(self, editor_name: str, file_path: str, changes: str) -> str:
        """Review code changes using editor's analysis capabilities."""
        if editor_name not in self.mcp_clients:
            return f"Editor {editor_name} not configured"

        try:
            result = self.mcp_clients[editor_name].call_tool(
                "review_changes",
                {
                    "file_path": file_path,
                    "changes": changes,
                    "check_style": True,
                    "check_logic": True,
                    "suggest_improvements": True,
                }
            )
            return result
        except Exception as e:
            return f"Code review failed: {e}"

    def apply_code_suggestions(self, editor_name: str, file_path: str, suggestions: List[Dict]) -> str:
        """Apply code suggestions through the editor."""
        if editor_name not in self.mcp_clients:
            return f"Editor {editor_name} not configured"

        try:
            result = self.mcp_clients[editor_name].call_tool(
                "apply_suggestions",
                {
                    "file_path": file_path,
                    "suggestions": suggestions,
                    "auto_format": True,
                }
            )
            return result
        except Exception as e:
            return f"Failed to apply suggestions: {e}"

    def get_project_context(self, editor_name: str, project_path: str) -> str:
        """Get project structure and context from editor."""
        if editor_name not in self.mcp_clients:
            return f"Editor {editor_name} not configured"

        try:
            result = self.mcp_clients[editor_name].call_tool(
                "get_project_context",
                {
                    "project_path": project_path,
                    "include_dependencies": True,
                    "include_structure": True,
                }
            )
            return result
        except Exception as e:
            return f"Failed to get project context: {e}"

    def get_tools(self) -> List[FunctionTool]:
        """Return list of available tools."""
        return [
            FunctionTool(self.open_file),
            FunctionTool(self.search_in_repository),
            FunctionTool(self.review_code_changes),
            FunctionTool(self.apply_code_suggestions),
            FunctionTool(self.get_project_context),
        ]