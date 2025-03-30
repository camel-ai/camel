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
['file_find_in_content', 'file_find_by_name', 'shell_exec', 'shell_view', 
'shell_wait', 'shell_write_to_process', 'shell_kill_process']
===============================================================================
    """

    res1: CallToolResult = await mcp_client.session.call_tool(
        "shell_exec",
        {
            'id': 'create_log_directory',
            'exec_dir': '/Users/coco/OnePiece/eigent/camel/examples/mcp'
            '/toolkits/terminal_toolkit/',
            'command': "mkdir logs"
        }
    )
    print(res1.content[0].text)

    """
===============================================================================
Command started in session 'create_log_directory'. Initial output: 
===============================================================================    
    """

    res2: CallToolResult = await mcp_client.session.call_tool(
        "shell_exec",
        {
            'id': 'create_log_file',
            'exec_dir': '/Users/coco/OnePiece/eigent/camel/examples/mcp'
            '/toolkits/terminal_toolkit/logs',
            'command': "echo 'INFO: Application started successfully at "
                       "2024-03-30' > app.log"
        }
    )
    print(res2.content[0].text)
    """
===============================================================================
Command started in session 'create_log_file'. Initial output: 
===============================================================================    
    """

    res3: CallToolResult = await mcp_client.session.call_tool(
        "shell_exec",
        {
            'id': 'delete_log_directory',
            'exec_dir': '/Users/coco/OnePiece/eigent/camel/examples/mcp'
            '/toolkits/terminal_toolkit',
            'command': "rm -rf ./logs"
        }
    )
    print(res3.content[0].text)
    """
===============================================================================
Command started in session 'delete_log_directory'. Initial output: 
===============================================================================    
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
