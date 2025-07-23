import asyncio
import sys

from mcp.types import CallToolResult

from camel.toolkits.mcp_toolkit import MCPClient, MCPToolkit


async def run_example_stdio():
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


if __name__ == "__main__":
    asyncio.run(run_example_stdio()) 