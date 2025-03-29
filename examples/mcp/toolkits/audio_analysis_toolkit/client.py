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
['audio2text', 'ask_question_about_audio']
===============================================================================
    """

    res1: CallToolResult = await mcp_client.session.call_tool(
        "audio2text", {"audio_path": "example_audio.mp3"}
    )
    print(res1.content[0].text)
    """
===============================================================================
CamelAI.org is an open-source community dedicated to the study of autonomous 
and communicative agents. We believe that studying these agents on a large 
scale offers valuable insights into their behaviors, capabilities, and 
potential risks. To facilitate research in this field, we provide, implement, 
and support various types of agents, tasks, prompts, models, datasets, and 
simulated environments. Join us via Slack, Discord, or WeChat in pushing the 
boundaries of building AI society.
===============================================================================    
    """

    res2: CallToolResult = await mcp_client.session.call_tool(
        "ask_question_about_audio",
        {
            "audio_path": "example_audio.mp3",
            "question": "What is the main topic of the audio?",
        },
    )
    print(res2.content[0].text)
    """
===============================================================================
It sounds like Camel AI is an open-source community focused on the study and 
development of autonomous and communicative agents. Their work includes a wide 
range of resources such as agents, tasks, prompts, models, datasets, and 
simulated environments aimed at facilitating research in this field. They also 
encourage collaboration and discussion through platforms like Slack, Discord, 
and WeChat. If you're interested in AI and collaborative research, Camel AI 
appears to be a community that could provide valuable insights and 
opportunities to contribute to the advancement of AI technology.
===============================================================================
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
