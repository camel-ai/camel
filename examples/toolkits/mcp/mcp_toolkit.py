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


async def main():
    config_path = Path(__file__).parent / "mcp_servers_config.json"
    mcp_toolkit = MCPToolkit(config_path=str(config_path))

    # Connect to all MCP servers.
    await mcp_toolkit.connect()

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

    # Disconnect from all MCP servers and clean up resources.
    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
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
