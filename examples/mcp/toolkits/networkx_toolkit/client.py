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
['add_edge', 'add_node', 'clear_graph', 'compute_centrality', 
'deserialize_graph', 'export_to_file', 'get_edges', 'get_nodes', 
'import_from_file', 'serialize_graph', 'get_shortest_path']
===============================================================================
    """

    await mcp_client.session.call_tool(
        "add_node", {'node_id': 'A', "attributes": {}}
    )
    await mcp_client.session.call_tool(
        "add_node", {'node_id': 'B', "attributes": {}}
    )
    await mcp_client.session.call_tool(
        "add_node", {'node_id': 'C', "attributes": {}}
    )
    await mcp_client.session.call_tool(
        "add_node", {'node_id': 'D', "attributes": {}}
    )
    await mcp_client.session.call_tool(
        "add_node", {'node_id': 'E', "attributes": {}}
    )
    await mcp_client.session.call_tool(
        "add_node", {'node_id': 'F', "attributes": {}}
    )
    await mcp_client.session.call_tool(
        "add_node", {'node_id': 'G', "attributes": {}}
    )

    res1: CallToolResult = await mcp_client.session.call_tool("get_nodes", {})
    print(res1.content)
    """
===============================================================================
[
    TextContent(type='text', text='A', annotations=None), 
    TextContent(type='text', text='B', annotations=None), 
    TextContent(type='text', text='C', annotations=None), 
    TextContent(type='text', text='D', annotations=None), 
    TextContent(type='text', text='E', annotations=None), 
    TextContent(type='text', text='F', annotations=None), 
    TextContent(type='text', text='G', annotations=None)
]
===============================================================================    
    """

    await mcp_client.session.call_tool(
        "add_edge", {'source': 'A', 'target': 'B', 'attributes': {'weight': 2}}
    )
    await mcp_client.session.call_tool(
        "add_edge", {'source': 'B', 'target': 'C', 'attributes': {'weight': 3}}
    )
    await mcp_client.session.call_tool(
        "add_edge", {'source': 'C', 'target': 'D', 'attributes': {'weight': 4}}
    )
    await mcp_client.session.call_tool(
        "add_edge", {'source': 'D', 'target': 'E', 'attributes': {'weight': 5}}
    )
    await mcp_client.session.call_tool(
        "add_edge", {'source': 'E', 'target': 'F', 'attributes': {'weight': 6}}
    )
    await mcp_client.session.call_tool(
        "add_edge", {'source': 'F', 'target': 'G', 'attributes': {'weight': 7}}
    )
    await mcp_client.session.call_tool(
        "add_edge", {'source': 'G', 'target': 'A', 'attributes': {'weight': 8}}
    )
    await mcp_client.session.call_tool(
        "add_edge", {'source': 'B', 'target': 'E', 'attributes': {'weight': 2}}
    )
    await mcp_client.session.call_tool(
        "add_edge", {'source': 'C', 'target': 'F', 'attributes': {'weight': 3}}
    )
    await mcp_client.session.call_tool(
        "add_edge", {'source': 'D', 'target': 'A', 'attributes': {'weight': 1}}
    )
    res2: CallToolResult = await mcp_client.session.call_tool("get_edges", {})
    print(res2.content)
    """
===============================================================================
[
    TextContent(type='text', text='A', annotations=None), 
    TextContent(type='text', text='B', annotations=None), 
    
    TextContent(type='text', text='B', annotations=None), 
    TextContent(type='text', text='C', annotations=None), 
    
    TextContent(type='text', text='B', annotations=None), 
    TextContent(type='text', text='E', annotations=None), 
    
    TextContent(type='text', text='C', annotations=None), 
    TextContent(type='text', text='D', annotations=None), 
    
    TextContent(type='text', text='C', annotations=None), 
    TextContent(type='text', text='F', annotations=None), 
    
    TextContent(type='text', text='D', annotations=None), 
    TextContent(type='text', text='E', annotations=None), 
    
    TextContent(type='text', text='D', annotations=None), 
    TextContent(type='text', text='A', annotations=None), 
    
    TextContent(type='text', text='E', annotations=None), 
    TextContent(type='text', text='F', annotations=None), 
    
    TextContent(type='text', text='F', annotations=None), 
    TextContent(type='text', text='G', annotations=None), 
    
    TextContent(type='text', text='G', annotations=None), 
    TextContent(type='text', text='A', annotations=None)
]
===============================================================================    
    """

    res3: CallToolResult = await mcp_client.session.call_tool(
        "get_shortest_path", {"source": "A", "target": "F", "weight": "weight"}
    )
    print(res3.content)
    """
===============================================================================  
[
    TextContent(type='text', text='A', annotations=None), 
    TextContent(type='text', text='B', annotations=None), 
    TextContent(type='text', text='C', annotations=None), 
    TextContent(type='text', text='F', annotations=None)
]
===============================================================================  
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
