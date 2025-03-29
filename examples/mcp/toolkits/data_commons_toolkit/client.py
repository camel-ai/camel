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
    mcp_client: _MCPServer = mcp_toolkit.servers[0]
    res: Union[str, "ListToolsResult"] = await mcp_client.list_mcp_tools()
    if isinstance(res, str):
        raise Exception(res)

    tools = [tool.name for tool in res.tools]
    print(tools)
    """
===============================================================================
['query_data_commons', 'get_triples', 'get_stat_time_series', 
'get_property_labels', 'get_property_values', 'get_places_in', 
'get_stat_value', 'get_stat_all']
===============================================================================
    """

    geoId06_name_query = '''
SELECT ?name ?dcid 
WHERE {
    ?a typeOf Place .
    ?a name ?name .
    ?a dcid ("geoId/06" "geoId/21" "geoId/24") .
    ?a dcid ?dcid
}
'''
    res1: CallToolResult = await mcp_client.session.call_tool(
        "query_data_commons",
        {"query_string": geoId06_name_query},
    )
    print(res1.content[0].text)
    """
===============================================================================
{"?name": "California", "?dcid": "geoId/06"}
===============================================================================    
    """

    dcids = ["geoId/06", "geoId/21", "geoId/24"]
    res2: CallToolResult = await mcp_client.session.call_tool(
        "get_triples",
        {"dcids": dcids},
    )
    print(res2.content[0].text[:1000])
    """
===============================================================================   
{"geoId/06": [["geoId/06", "administrativeCapital", "geoId/0664000"], 
["geoId/06", "alternateName", "CA"], 
["geoId/06", "archinformLocationId", "2810"], 
["geoId/06", "area", "SquareMile163695"], 
["geoId/06", "babelnetId", "00014403n"], 
["geoId/06", "bbcThingsId", "c404c0a9-608c-4cc1-b172-ee027e024f76"], 
["geoId/06", "brockhausEncylcopediaOnlineId", "kalifornien-20"], 
["geoId/06", "containedInPlace", "country/USA"], 
["geoId/06", "containedInPlace", "usc/PacificDivision"], 
["geoId/06", "czechNkcrAutId", "ge134103"], 
["geoId/06", "encyclopediaBritannicaOnlineId", "place/California-state"], 
["geoId/06", "encyclopediaLarousseId", "autre-region/wd/110876"], 
["geoId/06", "encyclopediaUniversalisId", "californie"], 
["geoId/06", "fastId", "1204928"], 
["geoId/06", "finlandYsoId", "105835"], 
["geoId/06", "fips104", "US06"], 
["geoId/06", "fips52AlphaCode", "CA"], 
["geoId/06", "franceIdRefId", "026363275"], 
["geoId/06", "franceNationalLibraryId", "118625808"], ...
===============================================================================   
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
