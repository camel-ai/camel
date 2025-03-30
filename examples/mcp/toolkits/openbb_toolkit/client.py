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
from typing import TYPE_CHECKING, Union

from mcp.types import CallToolResult

from camel.toolkits.mcp_toolkit import MCPToolkit, _MCPServer

if TYPE_CHECKING:
    from mcp import ListToolsResult


async def run_example():
    mcp_toolkit = MCPToolkit(config_path="./mcp_servers_config.json")

    await mcp_toolkit.connect()

    # call the server to list the available tools
    gt_mcp_client: _MCPServer = mcp_toolkit.servers[0]
    res: Union[str, "ListToolsResult"] = await gt_mcp_client.list_mcp_tools()
    if isinstance(res, str):
        raise Exception(res)

    tools = [tool.name for tool in res.tools]
    print(tools)
    """
===============================================================================
['search_equity', 'search_etf', 'search_institution', 'search_filings', 
'screen_market', 'get_available_indices', 'get_stock_quote', 
'get_historical_data', 'get_market_data', 'get_earnings_calendar', 
'get_dividend_calendar', 'get_ipo_calendar', 'get_available_indicators', 
'get_indicator_data', 'get_financial_metrics', 'get_company_profile', 
'get_financial_statement', 'get_financial_attributes', 
'search_financial_attributes', 'get_economic_calendar']
===============================================================================
    """

    # res1: CallToolResult = await gt_mcp_client.session.call_tool(
    #     "list_all_users",
    #     {},
    # )
    # print(res1.content[0].text[:1000])
    """
==============================================================================
[Not Tested]
===============================================================================    
    """

    # res2: CallToolResult = await gt_mcp_client.session.call_tool(
    #     "list_all_pages",
    #     {},
    # )
    # print(res2.content[0].text[:1000])
    """
==============================================================================
[Not Tested]
===============================================================================    
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
