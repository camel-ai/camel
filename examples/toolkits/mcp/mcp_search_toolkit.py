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

import json

from camel.agents import ChatAgent
from camel.toolkits import PulseMCPSearchToolkit

# Create an instance of the MCP search toolkit
search_toolkit = PulseMCPSearchToolkit()

# Example 1: Search for MCP servers with a specific query
print("Example 1: Search for MCP servers related to 'code generation'")
search_results = search_toolkit.search_mcp_servers(
    query="code generation",
    count_per_page=5,  # Limit to 5 results for brevity
)
print(json.dumps(search_results, indent=2))


research_results = search_toolkit.search_mcp_servers(
    query="github",
    count_per_page=5,  # Limit to 5 results for brevity
)
print(json.dumps(research_results, indent=2))

# Example 2: Get details about a specific MCP server
print("Example 2: Get details about a specific MCP server")
server_details = search_toolkit.get_mcp_server_details(
    server_name="github",
)
print(json.dumps(server_details, indent=2))

# Example 3: Using with ChatAgent
print("Example 3: Using with ChatAgent")

agent = ChatAgent(
    system_message="""You are a helpful assistant that can search for and 
    provide information about MCP servers and tools.""",
    tools=[
        *search_toolkit.get_tools(),
    ],
)

user_message = "What are the most popular MCP servers available?"

response = agent.step(input_message=user_message)
print(f"User: {user_message}")
print(f"Agent: {response.msgs[0].content}")
