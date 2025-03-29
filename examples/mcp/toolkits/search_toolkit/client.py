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
import json

from mcp.types import CallToolResult

from camel.toolkits.mcp_toolkit import MCPToolkit, _MCPServer


async def run_example():
    mcp_toolkit = MCPToolkit(config_path="./mcp_servers_config.json")

    await mcp_toolkit.connect()

    # call the server to list the available tools
    search_mcp_client: _MCPServer = mcp_toolkit.servers[0]
    res = await search_mcp_client.list_mcp_tools()
    if isinstance(res, str):
        raise Exception(res)

    tools = [tool.name for tool in res.tools]
    print(tools)
    """
===============================================================================
['search_wiki', 'search_linkup', 'search_duckduckgo', 'search_brave', 
'search_google', 'query_wolfram_alpha', 'tavily_search', 'search_bocha', 
'search_baidu', 'search_bing']
===============================================================================
    """

    res1: CallToolResult = await search_mcp_client.session.call_tool(
        "search_wiki", {"entity": "Shanghai"}
    )
    print(res1.content[0].text)
    """
===============================================================================
Shanghai is a direct-administered municipality and the most populous urban 
area in China. The city is located on the Chinese shoreline on the southern 
estuary of the Yangtze River, with the Huangpu River flowing through it. The 
population of the city proper is the second largest in the world after 
Chongqing, with around 24.87 million inhabitants in 2023, while the urban area 
is the most populous in China, with 29.87 million residents. As of 2022, the 
Greater Shanghai metropolitan area was estimated to produce a gross 
metropolitan product (nominal) of nearly 13 trillion RMB ($1.9 trillion). 
Shanghai is one of the world's major centers for finance, business and 
economics, research, science and technology, manufacturing, transportation, 
tourism, and culture.
===============================================================================    
    """

    res2: CallToolResult = await search_mcp_client.session.call_tool(
        "search_baidu",
        {"query": "MCP(Model Context Protocol)", "max_results": 5}
    )
    data = json.loads(res2.content[0].text)
    print(data)
    """
===============================================================================
{'results': [{'result_id': 1, 'title': '深入解析ModelContextProtocol(MCP):无缝连
接 LLM 与...', 'description': '2025年3月14日接下来,让我们看看如何开发一个MCP客户端,该客
置环境 # 创建项目目录uv initmcp-clientcd mcp-client # 创建虚拟环...微信公众平台\ue62b
\ue680播报\ue67d暂停', 'url': 'http://www.baidu.com/link?url=A9j_emTPVsuLBzFC1tJ
S2MvCNw7ZfxNxaRO0qUBG8rfsAPRdnk-HwHgaGgTrNAnILWE55ikCBMHiFs4w65dgxt8N--8EMa_9QT
MKaw4y6d9j9Vc2HgEKInbxqC_3zsS96A0lVQ9QAzrO3a2R7R38qsOdl61cokFyAHVC7pfH9pykndOtB
BFD26mZ9uNb6j60U_2S30eesOgiMH0qssxRKkgkph86emaGGGqmNodupcyCy6KATKST3KWWljsitq'
}, {'result_id': 2, 'title': '什么是MCP(ModelContextProtocol)?对话、意图识别、
服务...', 'descriptl': 'http://www.baidu.com/link?url=PxHUKUPSRiryWJtW3yUZ0A53AI
nej9LXlAPS952tLiL05FfCcPch2AotE6nwryV3FfNf6FAw4cPkJ-K8WoPpfWNJp78xAVL6e4VvxSNoI
5O'}, {'result_id': 3, 'title': '...MCP(模型上下文协议)什么是 MCP?MCP(ModelContext
Pr...', 'description': '', 'url': 'http://www.baidu.com/link?url=f2yHiiRmgEO0TS
VgBCT0xFM-leNYVOs3MRL4en6o44RJzk0o-LG4iRAd0f5QXEzjIXQ9Xf0UjBgq'}, 
{'result_id': 4, 'title': '一文看懂:MCP(大模型上下文协议) - 知乎', 'description': 
'5天前MCP(ModelContextProtocol,模型上下文协议) ,2的一种开放标准,旨在统一大型语言模型
(LLM)与外部数据源和工具之间的通信协议。MCP 的主要目的在于解决...知乎\ue62b\ue680播报
\ue67d暂停', 'url': 'http://www.baidu.com/link?VDluaH28bP-f_TLNAAIypK47cc8plxjrg
dr7KTosa'}]}
===============================================================================    
    """

    await mcp_toolkit.disconnect()


if __name__ == "__main__":
    asyncio.run(run_example())
