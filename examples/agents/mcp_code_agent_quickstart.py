# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

"""
Quick Start: MCP Code Agent

A simple example to get started with MCPCodeAgent.
"""

import asyncio


async def main():
    from camel.agents import MCPCodeAgent

    # Define MCP server configuration
    config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    "/tmp",
                ],
            }
        }
    }

    # Create and connect the agent
    async with await MCPCodeAgent.create(
        config_dict=config,
        workspace_dir="./mcp_workspace",
    ) as agent:
        # Ask the agent to perform a task
        response = await agent.astep(
            "List all files in /tmp and show me the first 5."
        )

        # Print the response
        print("Agent Response:")
        print(response.msgs[0].content if response.msgs else "No response")


if __name__ == "__main__":
    asyncio.run(main())
