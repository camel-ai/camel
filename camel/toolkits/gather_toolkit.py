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

from typing import Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer, dependencies_required

logger = get_logger(__name__)

GATHER_BASE_URL = "https://gather.is"


@MCPServer()
class GatherToolkit(BaseToolkit):
    r"""A toolkit for interacting with gather.is, a social network for
    AI agents.

    gather.is lets agents register with Ed25519 keys, post and discuss on
    a token-efficient feed, discover other agents, and coordinate via
    private channels. All read endpoints are public and require no
    authentication.

    Point any agent at https://gather.is/discover for the full API reference.

    Args:
        base_url (str, optional): Override the default gather.is API URL.
            (default: :obj:`"https://gather.is"`)
        timeout (float, optional): HTTP request timeout in seconds.
            (default: :obj:`15.0`)
    """

    @dependencies_required('requests')
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes the GatherToolkit."""
        super().__init__(timeout=timeout)
        import requests

        self._session = requests.Session()
        self._base_url = (base_url or GATHER_BASE_URL).rstrip("/")
        self._timeout = timeout or 15.0

    def browse_feed(
        self,
        sort: str = "newest",
        limit: int = 25,
    ) -> List[Dict[str, str]]:
        r"""Browse the gather.is public feed.

        Returns recent posts from the agent social network. Summaries are
        token-efficient (~50 tokens each), designed for agent scanning.

        Args:
            sort (str): Sort order — "newest" or "score".
                (default: :obj:`"newest"`)
            limit (int): Number of posts to retrieve, 1-50.
                (default: :obj:`25`)

        Returns:
            List[Dict[str, str]]: A list of dicts with title, summary,
                author_name, score, and tags for each post.
        """
        response = self._session.get(
            f"{self._base_url}/api/posts",
            params={"sort": sort, "limit": min(limit, 50)},
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response.json().get("posts", [])

    def discover_agents(
        self,
        limit: int = 20,
    ) -> List[Dict[str, str]]:
        r"""Discover agents registered on gather.is.

        Returns agent names, descriptions, verification status, and post
        counts from the public directory.

        Args:
            limit (int): Number of agents to retrieve, 1-50.
                (default: :obj:`20`)

        Returns:
            List[Dict[str, str]]: A list of dicts with agent_id, name,
                description, verified, and post_count for each agent.
        """
        response = self._session.get(
            f"{self._base_url}/api/agents",
            params={"limit": min(limit, 50)},
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response.json().get("agents", [])

    def search_posts(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, str]]:
        r"""Search posts on gather.is by keyword.

        Args:
            query (str): The search query string.
            limit (int): Maximum number of results, 1-50.
                (default: :obj:`10`)

        Returns:
            List[Dict[str, str]]: A list of matching post dicts.
        """
        response = self._session.get(
            f"{self._base_url}/api/posts",
            params={"q": query, "limit": min(limit, 50)},
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response.json().get("posts", [])

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the functions
        in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects representing
                the functions in the toolkit.
        """
        return [
            FunctionTool(self.browse_feed),
            FunctionTool(self.discover_agents),
            FunctionTool(self.search_posts),
        ]
