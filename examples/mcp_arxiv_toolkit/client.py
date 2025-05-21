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


from camel.toolkits.mcp_toolkit import MCPClient, MCPToolkit

mcp_toolkit = MCPToolkit(
    config_path="examples/mcp_arxiv_toolkit/mcp_servers_config.json"
)

mcp_toolkit.connect_sync()
mcp_client: MCPClient = mcp_toolkit.servers[0]

res = mcp_client.list_mcp_tools_sync()

if isinstance(res, str):
    raise Exception(res)

tools = [tool.name for tool in res.tools]
print(tools)
