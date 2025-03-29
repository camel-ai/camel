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
import tempfile
from typing import TYPE_CHECKING, Union

from mcp.types import CallToolResult

from camel.toolkits.mcp_toolkit import MCPToolkit, _MCPServer

if TYPE_CHECKING:
    from mcp import ListToolsResult


async def run_example():
    # Create a sample Excel file for demonstration
    temp_file = tempfile.NamedTemporaryFile(suffix=".md", delete=False)
    sample_file_path = temp_file.name

    sample_content = """
CAMEL-AI is an open-source community focused on discovering the scaling laws 
of agents for various applications like data generation, world simulation, and 
task automation. 🌟 It provides a framework for creating customizable agents 
and building multi-agent systems, making it easier to tackle real-world tasks. 
You can connect it to different data sources like PostgreSQL, CSVs, and more, 
and it allows you to ask questions in plain English to get instant insights! 📊

If you're into AI, deep learning, or just curious about how agents can 
collaborate and communicate, this could be super interesting! Want to know 
more about a specific feature? 😊
    """

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
['write_to_file']
===============================================================================
    """

    res1: CallToolResult = await mcp_client.session.call_tool(
        "write_to_file",
        {"content": sample_content, "filename": sample_file_path},
    )
    print(res1.content[0].text)
    """
===============================================================================
Content successfully written to file: 
/private/var/folders/cf/z69kcgcx4jq454flxdkvc0180000gn/T/tmpmguuq0hi.md
===============================================================================    
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
