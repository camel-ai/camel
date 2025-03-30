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
    math_mcp_client: _MCPServer = mcp_toolkit.servers[0]
    res: Union[str, "ListToolsResult"] = await math_mcp_client.list_mcp_tools()
    if isinstance(res, str):
        raise Exception(res)

    tools = [tool.name for tool in res.tools]
    print(tools)
    """
===============================================================================
['search_papers', 'get_paper_details', 'get_abstract', 'get_citation_count', 
'get_related_papers']
===============================================================================
    """

    res1: CallToolResult = await math_mcp_client.session.call_tool(
        "get_paper_details",
        {'paper_id': 37840631, 'include_references': True}
    )
    print(res1.content)
    """
===============================================================================
[TextContent(type='text', text='{"id": "37840631", "title": "Chinese guideline 
for lipid management (2023): a new guideline rich in domestic elements for 
controlling dyslipidemia.", "authors": "Li JJ", "journal": "J Geriatr 
Cardiol", "pub_date": "2023 Sep 28", "abstract": "1. J Geriatr Cardiol. 
2023 Sep 28;20(9):618-620. doi: \\n10.26599/1671-5411.2023.09.007.\\n\\n
Chinese guideline for lipid management (2023): a new guideline rich in 
domestic \\nelements for controlling dyslipidemia.\\n\\nLi JJ(1).\\n\\nAuthor 
information:\\n(1)Division of Cardio-Metabolic Center, State Key Laboratory of 
Cardiovascular \\nDisease, Fu Wai Hospital, National Center for Cardiovascular 
Disease, Chinese \\nAcademy of Medical Sciences, Peking Union Medical College, 
Beijing, China.\\n\\nDOI: 10.26599/1671-5411.2023.09.007\\nPMCID: PMC10568543
\\nPMID: 37840631", "doi": "doi: 10.26599/1671-5411.2023.09.007", "keywords": 
[], "mesh_terms": [], "publication_types": ["Journal Article"], "references": 
["35729555", "34734202", "34404993", "31172370", "30586774", "30526649", 
"29434622", "20350253"]}', annotations=None)]
===============================================================================    
    """

    res2: CallToolResult = await math_mcp_client.session.call_tool(
        "get_related_papers", {'paper_id': 37840631, 'max_results': 5}
    )
    print(res2.content[0].text)
    """
===============================================================================
{"id": "37840631", "title": "Chinese guideline for lipid management (2023): a 
new guideline rich in domestic elements for controlling dyslipidemia.", 
"authors": "Li JJ", "journal": "J Geriatr Cardiol", "pub_date": "2023 Sep 28", 
"abstract": "1. J Geriatr Cardiol. 2023 Sep 28;20(9):618-620. doi: \n
10.26599/1671-5411.2023.09.007.\n\nChinese guideline for lipid management 
(2023): a new guideline rich in domestic \nelements for controlling 
dyslipidemia.\n\nLi JJ(1).\n\nAuthor information:\n(1)Division of 
Cardio-Metabolic Center, State Key Laboratory of Cardiovascular \nDisease, 
Fu Wai Hospital, National Center for Cardiovascular Disease, Chinese \nAcademy 
of Medical Sciences, Peking Union Medical College, Beijing, China.\n\nDOI: 
10.26599/1671-5411.2023.09.007\nPMCID: PMC10568543\nPMID: 37840631", "doi": 
"doi: 10.26599/1671-5411.2023.09.007", "keywords": [], "mesh_terms": [], 
"publication_types": ["Journal Article"], "references": null}
===============================================================================    
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
