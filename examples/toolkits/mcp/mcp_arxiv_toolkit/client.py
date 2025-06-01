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


async def run_example_http():
    config = {
        "mcpServers": {
            "arxiv_toolkit": {
                "url": "http://localhost:8000/mcp/",
                "mode": "streamable-http",
            }
        }
    }
    mcp_toolkit = MCPToolkit(config_dict=config, timeout=60)

    async with mcp_toolkit:
        # call the server to list the available tools
        mcp_client: MCPClient = mcp_toolkit.clients[0]
        res = await mcp_client.list_mcp_tools()
        if isinstance(res, str):
            raise Exception(res)

        # call the server to list the available tools
        mcp_client: MCPClient = mcp_toolkit.clients[0]
        res = await mcp_client.list_mcp_tools()
        if isinstance(res, str):
            raise Exception(res)

        tools = [tool.name for tool in res.tools]
        print(tools)
        """
===============================================================================
['search_papers', 'download_papers']
===============================================================================
        """
        res1: CallToolResult = await mcp_client.session.call_tool(
            "search_papers", {"query": "attention is all you need"}
        )
        print(res1.content[0].text[:1000])
        """
===============================================================================
{"title": "Attention Is All You Need But You Don't Need All Of It For 
Inference of Large Language Models", "published_date": "2024-07-22", 
"authors": ["Georgy Tyukin", "Gbetondji J-S Dovonon", "Jean Kaddour", 
"Pasquale Minervini"], "entry_id": "http://arxiv.org/abs/2407.15516v1", 
"summary": "The inference demand for LLMs has skyrocketed in recent months, 
and serving\nmodels with low latencies remains challenging due to the 
quadratic input length\ncomplexity of the attention layers. In this work, we 
investigate the effect of\ndropping MLP and attention layers at inference time 
on the performance of\nLlama-v2 models. We find that dropping dreeper 
attention layers only marginally\ndecreases performance but leads to the best 
speedups alongside dropping entire\nlayers. For example, removing 33\\% of 
attention layers in a 13B Llama2 model\nresults in a 1.8\\% drop in average 
performance over the OpenLLM benchmark. We\nalso observe that skipping layers 
except the latter layers reduces perform
===============================================================================    
        """


async def run_example_stdio():
    config = {
        "mcpServers": {
            "arxiv_toolkit": {
                "command": sys.executable,
                "args": [
                    "examples/toolkits/mcp/mcp_arxiv_toolkit/arxiv_toolkit_server.py",
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

        # call the server to list the available tools
        mcp_client: MCPClient = mcp_toolkit.clients[0]
        res = await mcp_client.list_mcp_tools()
        if isinstance(res, str):
            raise Exception(res)

        tools = [tool.name for tool in res.tools]
        print(tools)
        res1: CallToolResult = await mcp_client.session.call_tool(
            "search_papers", {"query": "attention is all you need"}
        )
        print(res1.content[0].text[:1000])


if __name__ == "__main__":
    asyncio.run(run_example_http())
    asyncio.run(run_example_stdio())
