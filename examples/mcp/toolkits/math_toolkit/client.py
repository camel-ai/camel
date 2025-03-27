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
    math_mcp_client: _MCPServer = mcp_toolkit.servers[0]
    res: Union[str, "ListToolsResult"] = await math_mcp_client.list_mcp_tools()
    if isinstance(res, str):
        raise Exception(res)

    tools = [tool.name for tool in res.tools]
    print(tools)
    """
===============================================================================
['add', 'sub', 'multiply', 'divide', 'round']
===============================================================================
    """

    res1: CallToolResult = await math_mcp_client.session.call_tool(
        "add", {"a": 2008, "b": 2}
    )
    print(res1.content[0].text)
    """
===============================================================================
2010.0
===============================================================================    
    """

    res2: CallToolResult = await math_mcp_client.session.call_tool(
        "divide", {"a": 2008, "b": 0}
    )
    print(res2.content[0].text)
    """
===============================================================================
Error executing tool divide: float division by zero
===============================================================================    
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
