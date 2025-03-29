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
['get_news', 'get_stories', 'get_web_search', 'search_reddit', 'query_finance']
===============================================================================
    """

    res: CallToolResult = await mcp_client.session.call_tool(
        "get_news", {"query": "President of United States"}
    )
    print(res.content[0].text[:1000])
    """
===============================================================================
<doc>
[1]:
Title: Can Elon Musk Become President of the United States?
Summary: Elon Musk, the American billionaire, has been appointed to lead the 
Department of Government Efficiency in Donald Trump's upcoming administration, 
sparking speculation about his potential presidential ambitions. However, 
according to the US Constitution, the President must be a natural-born citizen 
of the United States. As Musk was born in South Africa and became a Canadian 
citizen through his mother, he does not meet this requirement. While he 
acquired US citizenship in 2002, this does not make him a natural-born 
citizen. Additionally, the Constitution requires the President to be at least 
35 years old and a resident of the United States for at least 14 years. Musk 
can, however, hold other government positions, as the requirement of being a 
natural-born citizen only applies to the President and Vice President. Many 
non-US-born citizens have held prominent government positions in the past, 
including Henry
===============================================================================    
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
