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
['ask_question_about_video']
===============================================================================
    """

    video_url = "https://www.youtube.com/watch?v=kQ_7GtE529M"
    question = "What is shown in the first few seconds of this video?"

    res: CallToolResult = await gt_mcp_client.session.call_tool(
        "ask_question_about_video",
        {
            "video_path": video_url,
            "question": question,
            "num_frames": 5,
        },
    )
    print(res.content[0].text[:1000])
    """
===============================================================================
### Visual Analysis

1. **Identified Entities**:
   - **Wolves**: Multiple wolves are visible, characterized by their grayish 
   fur, slender bodies, and pack behavior.
   - **Bison**: A bison is present, identifiable by its large size, shaggy 
   brown fur, and distinctive hump on its back.

2. **Key Attributes**:
   - **Wolves**: 
     - Size: Smaller than the bison.
     - Color: Predominantly gray with some variations in shades.
     - Behavior: They appear to be moving in a coordinated manner, indicative 
     of pack hunting behavior.
   - **Bison**:
     - Size: Large and robust.
     - Color: Dark brown, with a thick coat.
     - Behavior: The bison is stationary or moving slowly, likely in a 
     defensive posture.

3. **Contextual Patterns**:
   - The wolves are shown surrounding the bison, suggesting a predatory 
   interaction.
   - The snowy environment indicates a cold habitat, likely a tundra or 
   open plains.

### Audio Integration

- **No audio transcription available**: Therefore, the analys
===============================================================================    
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
