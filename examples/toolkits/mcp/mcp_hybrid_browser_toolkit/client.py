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
import os
import sys

from mcp.types import CallToolResult

from camel.toolkits.mcp_toolkit import MCPClient, MCPToolkit


def _print_result(result: CallToolResult, max_length: int = 500) -> None:
    """Print truncated content; handle empty and non-text parts gracefully."""
    try:
        parts = getattr(result, "content", []) or []
        if not parts:
            print("<empty>")
            return
        texts = []
        for p in parts:
            # Prefer text when available
            text = getattr(p, "text", None)
            if text:
                texts.append(str(text))
                continue
            # Fallbacks for common content shapes
            uri = getattr(p, "uri", None)
            if uri:
                texts.append(f"<image: {uri}>")
                continue
            resource = getattr(p, "resource", None)
            if resource:
                texts.append(f"<resource: {resource}>")
                continue
            texts.append(str(p))
        out = "\n".join(texts)
        print(out[:max_length] + ("..." if len(out) > max_length else ""))
    except Exception as e:
        print(f"<error printing result: {e}>")


async def run_example_async():
    """Example of using HybridBrowserToolkit MCP server asynchronously."""
    server_script = os.path.join(
        os.path.dirname(__file__), "hybrid_browser_toolkit_server.py"
    )
    config = {
        "mcpServers": {
            "hybrid_browser_toolkit": {
                "command": sys.executable,
                "args": [
                    server_script,
                    "--mode",
                    "stdio",
                    "--headless",
                    "--implementation",
                    "python",
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

        # Test opening browser
        print("\n=== Opening Browser ===")
        res1: CallToolResult = await mcp_client.session.call_tool(
            "browser_open", {}
        )
        _print_result(res1)

        # Test visiting a page
        print("\n=== Visiting Google ===")
        res2: CallToolResult = await mcp_client.session.call_tool(
            "browser_visit_page", {"url": "https://www.google.com"}
        )
        _print_result(res2)

        # Test getting page snapshot
        print("\n=== Getting Page Snapshot ===")
        res3: CallToolResult = await mcp_client.session.call_tool(
            "browser_get_page_snapshot", {}
        )
        _print_result(res3)

        # Test closing browser
        print("\n=== Closing Browser ===")
        res4: CallToolResult = await mcp_client.session.call_tool(
            "browser_close", {}
        )
        _print_result(res4)


def run_example_sync():
    """Example of using HybridBrowserToolkit MCP server synchronously."""
    server_script = os.path.join(
        os.path.dirname(__file__), "hybrid_browser_toolkit_server.py"
    )
    config = {
        "mcpServers": {
            "hybrid_browser_toolkit": {
                "command": sys.executable,
                "args": [
                    server_script,
                    "--mode",
                    "stdio",
                    "--headless",
                    "--implementation",
                    "python",
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

        # Test opening browser
        print("\n=== Opening Browser (Sync) ===")
        res1: CallToolResult = mcp_client.call_tool_sync("browser_open", {})
        _print_result(res1)

        # Test visiting a page
        print("\n=== Visiting Example.com (Sync) ===")
        res2: CallToolResult = mcp_client.call_tool_sync(
            "browser_visit_page", {"url": "https://www.example.com"}
        )
        _print_result(res2)

        # Test closing browser
        print("\n=== Closing Browser (Sync) ===")
        res3: CallToolResult = mcp_client.call_tool_sync("browser_close", {})
        _print_result(res3)


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
