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

from mcp.types import CallToolResult

from camel.toolkits.mcp_toolkit import MCPToolkit, _MCPServer


async def run_example():
    mcp_toolkit = MCPToolkit(config_path="./mcp_servers_config.json")

    await mcp_toolkit.connect()

    # call the server to list the available tools
    search_mcp_client: _MCPServer = mcp_toolkit.servers[0]
    res = await search_mcp_client.list_mcp_tools()
    if isinstance(res, str):
        raise Exception(res)

    tools = [tool.name for tool in res.tools]
    print(tools)
    """
===============================================================================
['generate_3d_preview', 'refine_3d_model', 'get_task_status', 
'wait_for_task_completion', 'generate_3d_model_complete']
===============================================================================
    """

    prompt = "A figuring of Tin tin the cartoon character"
    art_style = "realistic"
    negative_prompt = "low quality, low resolution, low poly, ugly"

    res1: CallToolResult = await search_mcp_client.session.call_tool(
        "generate_3d_model_complete",
        {
            "prompt": prompt,
            "art_style": art_style,
            "negative_prompt": negative_prompt,
        },
    )
    print(res1.content[0].text[:1000])
    """
===============================================================================
Starting 3D model generation...
Status after 0s: PENDING
Status after 11s: IN_PROGRESS
Status after 22s: IN_PROGRESS
Status after 32s: SUCCEEDED
Status after 0s: PENDING
Status after 11s: IN_PROGRESS
Status after 21s: IN_PROGRESS
Status after 32s: IN_PROGRESS
Status after 43s: IN_PROGRESS
Status after 53s: IN_PROGRESS
Status after 64s: IN_PROGRESS
Status after 74s: IN_PROGRESS
Status after 85s: IN_PROGRESS
Status after 95s: IN_PROGRESS
Status after 106s: IN_PROGRESS
Status after 117s: SUCCEEDED

Final Response: {'id': '01939144-7dea-73c7-af06-efa79c83243f', 'mode': 
'refine', 'name': '', 'seed': 1733308970, 'art_style': 'realistic', 
'texture_richness': 'high', 'prompt': 'A figuring of Tin tin the cartoon 
character', 'negative_prompt': 'low quality, low resolution, low poly, ugly', 
'status': 'SUCCEEDED', 'created_at': 1733309005313, 'progress': 100, 
'started_at': 1733309006267, 'finished_at': 1733309113474, 'task_error': None, 
'model_urls': {'glb': 'https://assets.meshy.ai/5e05026a
===============================================================================    
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
