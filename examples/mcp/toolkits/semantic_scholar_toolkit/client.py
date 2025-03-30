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
['fetch_paper_data_title', 'fetch_paper_data_id', 'fetch_bulk_paper_data', 
'fetch_recommended_papers', 'fetch_author_data']
===============================================================================
    """

    res: CallToolResult = await gt_mcp_client.session.call_tool(
        "fetch_paper_data_title",
        {
            'paper_title': 'Construction of the Literature Graph in Semantic '
            'Scholar',
            'fields': [
                'title',
                'abstract',
                'authors',
                'year',
                'citationCount',
                'paperId',
            ],
        },
    )
    print(res.content[0].text[:1000])
    """
===============================================================================
{"total": 1, "offset": 0, "data": [{"paperId": 
"649def34f8be52c8b66281af98ae884c09aef38b", "title": "Construction of the 
Literature Graph in Semantic Scholar", "abstract": "We describe a deployed 
scalable system for organizing published scientific literature into a 
heterogeneous graph to facilitate algorithmic manipulation and discovery. The 
resulting literature graph consists of more than 280M nodes, representing 
papers, authors, entities and various interactions between them (e.g., 
authorships, citations, entity mentions). We reduce literature graph 
construction into familiar NLP tasks (e.g., entity extraction and linking), 
point out research challenges due to differences from standard formulations of 
these tasks, and report empirical results for each task. The methods described 
in this paper are used to enable semantic features in 
www.semanticscholar.org.", "year": 2018, "citationCount": 383, 
"openAccessPdf": {"url": "https://www.aclweb.org/anthology/N18-3011.pdf", 
"status": "HYBRID
===============================================================================    
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
