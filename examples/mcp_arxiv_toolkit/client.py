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
import sys

from camel.toolkits.mcp_toolkit import (
    MCPClientSync,
    MCPToolkitSync,
)


def main():
    toolkit = MCPToolkitSync.create(
        config_path="examples/mcp_arxiv_toolkit/mcp_servers_config.json"
    )
    print("Connected to MCP servers.")
    try:
        client = MCPClientSync(toolkit.servers[0])
        print(toolkit.servers)

        tools = client.list_mcp_tools()
        if isinstance(tools, str):
            raise Exception(tools)

        tool_names = [tool.name for tool in tools]
        print("Available tools:", tool_names)

        result = client.call_tool(
            "search_papers", {"query": "attention is all you need"}
        )
        print("\nSearch result summary:")
        print(result.content[0].text)

    finally:
        toolkit.disconnect()


if __name__ == "__main__":
    sys.exit(main())
