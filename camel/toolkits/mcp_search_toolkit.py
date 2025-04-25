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

from typing import Any, Dict, List, Optional

import requests

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer


@MCPServer()
class PulseMCPSearchToolkit(BaseToolkit):
    r"""A toolkit for searching MCP servers using the PulseMCP API.

    This toolkit provides methods for searching and retrieving information
    about MCP servers available through the PulseMCP platform.
    """

    def __init__(self, timeout: Optional[float] = None):
        r"""Initialize the MCPSearchToolkit.

        Args:
            timeout (Optional[float]): The timeout for API requests.
                Defaults to None.
        """
        super().__init__(timeout=timeout)
        self.api_base_url = "https://api.pulsemcp.com/v0beta"

    def search_mcp_servers(
        self,
        query: Optional[str] = None,
        count_per_page: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        r"""Search for MCP servers using the PulseMCP API.

        Args:
            query (Optional[str]): Search term to filter servers.
                Defaults to None.
            count_per_page (int): Number of results per page
                (maximum: 5000). Defaults to 50.
            offset (int): Number of results to skip for pagination.
                Defaults to 0.

        Returns:
            Dict[str, Any]: Dictionary containing information about
                matching MCP servers.
        """
        params: Dict[str, Any] = {
            "count_per_page": min(count_per_page, 5000),
            "offset": offset,
        }

        if query:
            params["query"] = query

        response = requests.get(f"{self.api_base_url}/servers", params=params)

        if response.status_code == 200:
            return response.json()
        else:
            error_msg = f"Error searching MCP servers: {response.status_code}"
            if response.text:
                try:
                    error_info = response.json()
                    if "error" in error_info:
                        msg = error_info['error'].get('message', '')
                        error_msg = f"{error_msg} - {msg}"
                except Exception:
                    error_msg = f"{error_msg} - {response.text}"

            return {"error": error_msg}

    def get_mcp_server_details(self, server_name: str) -> Dict[str, Any]:
        r"""Get detailed information about a specific MCP server.

        Args:
            server_name (str): The name of the MCP server to retrieve
                details for.

        Returns:
            Dict[str, Any]: Dictionary containing detailed information
                about the specified MCP server.
        """
        # First search for the server by name
        search_results = self.search_mcp_servers(query=server_name)

        if "error" in search_results:
            return search_results

        # Find the exact server match or closest match
        servers = search_results.get("servers", [])

        for server in servers:
            if server.get("name") == server_name:
                return server

        # If no exact match, return the first result or an error
        if servers:
            return servers[0]
        else:
            return {"error": f"No MCP server found with name: {server_name}"}

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.search_mcp_servers),
            FunctionTool(self.get_mcp_server_details),
        ]
