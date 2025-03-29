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
['get_author_detailed_info', 'get_author_publications', 
'get_publication_by_title', 'get_full_paper_content_by_link']
===============================================================================
    """

    res: CallToolResult = await gt_mcp_client.session.call_tool(
        "get_author_detailed_info", {}
    )
    print(res.content[0].text[:1000])
    """
===============================================================================
{"container_type": "Author", "filled": ["basics", "indices", "counts", 
"coauthors", "publications", "public_access"], "scholar_id": "JicYPdAAAAAJ", 
"source": "AUTHOR_PROFILE_PAGE", "name": "Geoffrey Hinton", "url_picture": 
"https://scholar.googleusercontent.com/citations?view_op=view_photo&user=JicYPd
AAAAAJ&citpid=2", "affiliation": "Emeritus Prof. Computer Science, University 
of Toronto", "organization": 8515235176732148308, "interests": ["machine 
learning", "psychology", "artificial intelligence", "cognitive science", 
"computer science"], "email_domain": "@cs.toronto.edu", "homepage": 
"http://www.cs.toronto.edu/~hinton", "citedby": 913598, "citedby5y": 538201, 
"hindex": 188, "hindex5y": 132, "i10index": 494, "i10index5y": 364, 
"cites_per_year": {"1989": 2513, "1990": 3515, "1991": 3724, "1992": 4009, 
"1993": 4485, "1994": 4379, "1995": 3901, "1996": 3808, "1997": 3638, "1998": 
3623, "1999": 3456, "2000": 3185, "2001": 3295, "2002": 3690, "2003": 3687, 
"2004": 3372, "2005": 3822, "200
===============================================================================    
    """

    res_content: CallToolResult = await gt_mcp_client.session.call_tool(
        "get_author_publications",
        {},
    )
    print(res_content.content[0].text)
    """
===============================================================================
Imagenet classification with deep convolutional neural networks
===============================================================================    
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
