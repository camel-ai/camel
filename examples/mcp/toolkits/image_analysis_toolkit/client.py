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
['image_to_text', 'ask_question_about_image']
===============================================================================
    """

    res1: CallToolResult = await gt_mcp_client.session.call_tool(
        "image_to_text",
        {
            "image_path": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
        },
    )
    print(res1.content[0].text[:1000])
    """
===============================================================================
The image depicts a tranquil natural landscape featuring a wooden pathway that 
runs through a lush green marsh or field. The path is made of planks and 
extends straight into the distance, bordered by tall grasses on either side. 
Beyond the walkway, a variety of shrubbery and trees can be seen, adding to 
the vibrant greenery of the scene. 

Above, the sky is painted in soft blues, adorned with wispy clouds that 
stretch across the horizon. The overall atmosphere conveys a sense of calm and 
serenity, inviting viewers to take a peaceful stroll through this idyllic 
setting. The lighting suggests it may be either early morning or late 
afternoon, enhancing the warm hues of the landscape.
===============================================================================    
    """

    res2: CallToolResult = await gt_mcp_client.session.call_tool(
        "ask_question_about_image",
        {
            "image_path": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
            "question": "What's in this image? You must use image analysis to"
            "help me.",
        },
    )
    print(res2.content[0].text[:1000])
    """
===============================================================================
The image depicts a serene natural landscape featuring a wooden pathway that 
meanders through a lush green field. The path is surrounded by tall grass, 
creating a vibrant, inviting atmosphere. In the background, there are 
scattered trees and shrubs under a blue sky adorned with soft, white clouds. 
The overall scene conveys a sense of tranquility and connection to nature, 
ideal for walking or exploring.
===============================================================================    
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
