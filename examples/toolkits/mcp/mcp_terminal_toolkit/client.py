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
import sys

from mcp.types import CallToolResult

from camel.toolkits.mcp_toolkit import MCPClient, MCPToolkit


async def run_example_async():
    """Example of using Terminal Toolkit MCP server asynchronously."""
    config = {
        "mcpServers": {
            "terminal_toolkit": {
                "command": sys.executable,
                "args": [
                    "examples/toolkits/mcp/mcp_terminal_toolkit/terminal_toolkit_server.py",
                    "--mode",
                    "stdio",
                ],
            }
        }
    }
    mcp_toolkit = MCPToolkit(config_dict=config, timeout=60)
    async with mcp_toolkit:
        mcp_client: MCPClient = mcp_toolkit.clients[0]
        res = await mcp_client.list_mcp_tools()
        if isinstance(res, str):
            raise Exception(res)

        tools = [tool.name for tool in res.tools]
        print(f"Available tools: {tools}")

        res1: CallToolResult = await mcp_client.session.call_tool(
            "shell_exec", {"id": "test_session", "command": "ls -l"}
        )
        print(res1.content[0].text[:1000])


def run_example_sync():
    """Example of using Terminal Toolkit MCP server synchronously."""
    config = {
        "mcpServers": {
            "terminal_toolkit": {
                "command": sys.executable,
                "args": [
                    "examples/toolkits/mcp/mcp_terminal_toolkit/terminal_toolkit_server.py",
                    "--mode",
                    "stdio",
                ],
            }
        }
    }
    mcp_toolkit = MCPToolkit(config_dict=config, timeout=60)
    with mcp_toolkit:
        mcp_client: MCPClient = mcp_toolkit.clients[0]
        res = mcp_client.list_mcp_tools_sync()
        if isinstance(res, str):
            raise Exception(res)

        tools = [tool.name for tool in res.tools]
        print(f"Available tools: {tools}")

        res1: CallToolResult = mcp_client.call_tool_sync(
            "shell_exec", {"id": "test_session_sync", "command": "ls -a"}
        )
        print(res1.content[0].text[:1000])


if __name__ == "__main__":
    print("Choose mode:")
    print("1. Async example")
    print("2. Sync example")

    choice = input("Enter your choice (1 or 2): ").strip()

    if choice == "1":
        print("Running async example...")
        asyncio.run(run_example_async())
    elif choice == "2":
        print("Running sync example...")
        run_example_sync()
    else:
        print("Invalid choice. Running async example by default...")
        asyncio.run(run_example_async())
