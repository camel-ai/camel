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
    r"""A toolkit for searching MCP servers using the PulseMCP API."""

    def __init__(self, timeout: Optional[float] = None):
        super().__init__(timeout=timeout)
        self.api_base_url = "https://api.pulsemcp.com/v0beta"

    def search_mcp_servers(
        self,
        query: Optional[str] = None,
        top_k: Optional[int] = 5,
        package_registry: Optional[str] = None,
        count_per_page: int = 5000,
        offset: int = 0,
    ) -> Dict[str, Any]:
        r"""Search for MCP servers using the PulseMCP API.

        Args:
            query (Optional[str]): The query to search for.
                (default: :obj:`None`)
            top_k (Optional[int]): After sorting, return only the top_k
                servers. (default: :obj:`5`)
            package_registry (Optional[str]): The package registry to search
                for. (default: :obj:`None`)
            count_per_page (int): The number of servers to return per page.
                (default: :obj:`5000`)
            offset (int): The offset to start the search from.
                (default: :obj:`0`)

        Returns:
            Dict[str, Any]: A dictionary containing the search results or
                an error message.
        """
        params: Dict[str, Any] = {
            "count_per_page": min(count_per_page, 5000),
            "offset": offset,
        }
        if query:
            params["query"] = query

        response = requests.get(f"{self.api_base_url}/servers", params=params)

        if response.status_code != 200:
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

        data = response.json()
        servers = data.get("servers", [])

        if package_registry:
            package_registry_lower = package_registry.lower()
            servers = [
                server
                for server in servers
                if isinstance(server.get("package_registry"), str)
                and server.get("package_registry").lower()
                == package_registry_lower
            ]

        if query:
            query_lower = query.lower()
            # Helper function to calculate score
            # 1. With name +5
            # 2. With description +3
            # 3. With stars +1

            def score(server: Dict[str, Any]) -> float:
                name = server.get("name", "").lower()
                desc = server.get("short_description", "").lower()
                stars = server.get("github_stars", 0) or 0
                score: float = 0.0
                if query_lower in name:
                    score += 5
                if query_lower in desc:
                    score += 3
                score += stars / 1000
                return score

            servers = sorted(servers, key=score, reverse=True)
        else:
            servers = sorted(
                servers,
                key=lambda x: x.get("github_stars", 0) or 0,
                reverse=True,
            )

        if top_k is not None:
            servers = servers[:top_k]

        return {"servers": servers}

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects.
        """
        return [
            FunctionTool(self.search_mcp_servers),
        ]
