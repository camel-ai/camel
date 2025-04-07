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

from camel.toolkits.mcp_toolkit import MCPClient, MCPToolkit


async def run_example():
    mcp_toolkit = MCPToolkit(
        config_path="examples/mcp_notion_toolkit/mcp_servers_config.json"
    )

    await mcp_toolkit.connect()

    # call the server to list the available tools
    mcp_client: MCPClient = mcp_toolkit.servers[0]
    res = await mcp_client.list_mcp_tools()
    if isinstance(res, str):
        raise Exception(res)

    tools = [tool.name for tool in res.tools]
    print(tools)
    """
===============================================================================
['list_all_pages', 'list_all_users', 'get_notion_block_text_content']
===============================================================================
    """

    # List all pages in the Notion workspace
    res1: CallToolResult = await mcp_client.session.call_tool(
        "list_all_pages", {}
    )
    print("\nPages in Notion workspace:")
    print(res1)
    
    # If you have a Notion page, you can get its content
    # Uncomment and replace with a valid block_id to test
    """
    block_id = "your_page_id_here"  # Replace with a real ID
    res3: CallToolResult = await mcp_client.session.call_tool(
        "get_notion_block_text_content", {"block_id": block_id}
    )
    print("\nContent of Notion block:")
    print(res3)
    """

    # Get a list of all users
    res2: CallToolResult = await mcp_client.session.call_tool(
        "list_all_users", {}
    )
    print("\nUsers in Notion workspace:")
    print(res2.content[0].text if res2.content else "No users found")

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(run_example())
    except Exception as e:
        print(f"Error running example: {e}")
