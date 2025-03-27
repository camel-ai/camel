import asyncio
from typing import TYPE_CHECKING, Union

from mcp.types import CallToolResult

from camel.toolkits.mcp_toolkit import MCPToolkit, _MCPServer

if TYPE_CHECKING:
    from mcp import ListToolsResult


async def run_example():
    mcp_toolkit = MCPToolkit(config_path="./mcp_servers_config.json")

    await mcp_toolkit.connect()

    # call the server to list the available tools
    gt_mcp_client: _MCPServer = mcp_toolkit.servers[0]
    res: Union[str, "ListToolsResult"] = await gt_mcp_client.list_mcp_tools()
    if isinstance(res, str):
        raise Exception(res)

    tools = [tool.name for tool in res.tools]
    print(tools)
    """
===============================================================================
['get_github_access_token', 'get_issue_list', 'create_pull_request', 
'get_issue_content', 'get_pull_request_list', 'get_pull_request_code', 
'get_pull_request_comments', 'get_all_file_paths', 'retrieve_file_content']
===============================================================================
    """

    res: CallToolResult = await gt_mcp_client.session.call_tool(
        "get_issue_content", {"issue_number": 2008}
    )
    print(res.content[0].text)
    """
===============================================================================
### Required prerequisites

- [x] I have searched the [Issue Tracker](https://github.com/camel-ai/camel/iss
ues) and [Discussions](https://github.com/camel-ai/camel/discussions) that this
 hasn't already been reported. (+1 or comment there if it has.)
- [ ] Consider asking first in a [Discussion](https://github.com/camel-ai/camel
/discussions/new).

### Motivation

Unify the stdio and sse configuration of MCP Server

### Solution

_No response_

### Alternatives

_No response_

### Additional context

_No response_
===============================================================================    
    """

    res_content: CallToolResult = await gt_mcp_client.session.call_tool(
        "retrieve_file_content",
        {"file_path": "camel/agents/chat_agent.py"},
    )
    print(res_content.content[0].text[:1000])
    """
===============================================================================
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
from __future__ import annotations

import json
import logging
import textwrap
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Type,
===============================================================================    
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
