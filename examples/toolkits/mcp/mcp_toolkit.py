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
"""MCP Server Example

This example demonstrates how to use the MCP (Managed Code Processing) server
with CAMEL agents for file operations.

Setup:
1. Install Node.js and npm

2. Install MCP filesystem server globally:
   ```bash
   npm install -g @modelcontextprotocol/server-filesystem
   ```

Usage:
1. Run this script to start an MCP filesystem server
2. The server will only operate within the specified directory
3. All paths in responses will be relative to maintain privacy
"""

import asyncio
from pathlib import Path

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import MCPToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils.mcp_client import MCPClient


async def mcp_client_example():
    config = {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
    }
    async with MCPClient(config) as client:
        mcp_tools = await client.list_mcp_tools()
        print("Available MCP tools:", [tool.name for tool in mcp_tools.tools])
        call_tool_result = await client.call_tool(
            "list_directory", {"path": "."}
        )
        print("Directory Contents:")
        for i, item in enumerate(call_tool_result.content[0].text.split('\n')):
            if item.strip():
                print(f"  {item}")
                if i >= 4:  # Stop after printing 5 items (0-based index)
                    break


'''
===============================================================================
Available MCP tools: ['read_file', 'read_multiple_files', 'write_file', 
'edit_file', 'create_directory', 'list_directory', 'directory_tree', 
'move_file', 'search_files', 'get_file_info', 'list_allowed_directories']
Directory Contents:
  [DIR] .container
  [FILE] .env
  [DIR] .git
  [DIR] .github
  [FILE] .gitignore
===============================================================================
'''


async def mcp_toolkit_example():
    # Use either config path or config dict to initialize the MCP toolkit.
    # 1. Use config path:
    config_path = Path(__file__).parent / "mcp_servers_config.json"
    # 2. Use config dict:
    # config_dict = {
    #     "mcpServers": {
    #         "filesystem": {
    #             "command": "npx",
    #             "args": [
    #                 "-y",
    #                 "@modelcontextprotocol/server-filesystem@2025.1.14",
    #                 "."
    #             ]
    #         }
    #     },
    #     "mcpWebServers": {}
    # }
    # mcp_toolkit = MCPToolkit(config_dict=config_dict)

    # Connect to all MCP servers.
    async with MCPToolkit(config_path=str(config_path)) as mcp_toolkit:
        sys_msg = "You are a helpful assistant"
        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )
        camel_agent = ChatAgent(
            system_message=sys_msg,
            model=model,
            tools=[*mcp_toolkit.get_tools()],
        )
        user_msg = "List 5 files in the project, using relative paths"
        response = await camel_agent.astep(user_msg)
        print(response.msgs[0].content)
        print(response.info['tool_calls'])


'''
===============================================================================
Here are 5 files in the project using relative paths:

1. `.env`
2. `.gitignore`
3. `CONTRIBUTING.md`
4. `LICENSE`
5. `README.md`
[ToolCallingRecord(tool_name='list_allowed_directories', args={}, 
result='Allowed directories:\n/Users/enrei/Desktop/camel0605/camel', 
tool_call_id='call_xTidk11chOk8j9gjrpNMlKjq'), ToolCallingRecord
(tool_name='list_directory', args={'path': '/Users/enrei/Desktop/camel0605/
camel'}, result='[DIR] .container\n[FILE] .env\n[DIR] .git\n[DIR] .github\n
[FILE] .gitignore\n[DIR] .mypy_cache\n[FILE] .pre-commit-config.yaml\n[DIR] 
pytest_cache\n[DIR] .ruff_cache\n[FILE] .style.yapf\n[DIR] .venv\n[FILE] 
CONTRIBUTING.md\n[FILE] LICENSE\n[FILE] Makefile\n[FILE] README.md\n[DIR] 
apps\n[DIR] camel\n[DIR] data\n[DIR] docs\n[DIR] examples\n[DIR] licenses\n
[DIR] misc\n[FILE] pyproject.toml\n[DIR] services\n[DIR] test\n[FILE] uv.
lock', tool_call_id='call_8eaZP8LQxxvM3cauWWyZ2fJ4')]
===============================================================================
'''


# Same example as above but in sync mode
def mcp_toolkit_example_sync():
    # Use either config path or config dict to initialize the MCP toolkit.
    config_path = Path(__file__).parent / "mcp_servers_config.json"

    # Connect to all MCP servers.
    with MCPToolkit(config_path=str(config_path)) as mcp_toolkit:
        sys_msg = "You are a helpful assistant"
        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        )
        camel_agent = ChatAgent(
            system_message=sys_msg,
            model=model,
            tools=[*mcp_toolkit.get_tools()],
        )
        user_msg = "List 5 files in the project, using relative paths"
        # response = await camel_agent.astep(user_msg)
        response = camel_agent.step(user_msg)
        print(response.msgs[0].content)
        print(response.info['tool_calls'])


'''
===============================================================================
Here are 5 files in the project using relative paths:

1. `.env`
2. `.gitignore`
3. `.pre-commit-config.yaml`
4. `CONTRIBUTING.md`
5. `README.md`
===============================================================================
'''

if __name__ == "__main__":
    asyncio.run(mcp_client_example())
    asyncio.run(mcp_toolkit_example())
    mcp_toolkit_example_sync()

'''
===============================================================================
Here are 5 files in the project using relative paths:

1. `.env`
2. `.gitignore`
3. `CONTRIBUTING.md`
4. `LICENSE`
5. `README.md`
[ToolCallingRecord(tool_name='list_allowed_directories', args={}, 
result='Allowed directories:\n/Users/enrei/Desktop/camel0605/camel', 
tool_call_id='call_xTidk11chOk8j9gjrpNMlKjq'), ToolCallingRecord
(tool_name='list_directory', args={'path': '/Users/enrei/Desktop/camel0605/
camel'}, result='[DIR] .container\n[FILE] .env\n[DIR] .git\n[DIR] .github\n
[FILE] .gitignore\n[DIR] .mypy_cache\n[FILE] .pre-commit-config.yaml\n[DIR] 
pytest_cache\n[DIR] .ruff_cache\n[FILE] .style.yapf\n[DIR] .venv\n[FILE] 
CONTRIBUTING.md\n[FILE] LICENSE\n[FILE] Makefile\n[FILE] README.md\n[DIR] 
apps\n[DIR] camel\n[DIR] data\n[DIR] docs\n[DIR] examples\n[DIR] licenses\n
[DIR] misc\n[FILE] pyproject.toml\n[DIR] services\n[DIR] test\n[FILE] uv.
lock', tool_call_id='call_8eaZP8LQxxvM3cauWWyZ2fJ4')]
===============================================================================
'''
