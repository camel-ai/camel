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
from camel.agents import ChatAgent

# Create a chat agent with a model
agent = ChatAgent(model="gpt-4o-mini")


# Create an MCP server from the agent
mcp_server = agent.to_mcp(
    name="demo", description="A demonstration of ChatAgent to MCP conversion"
)

# Run the server
if __name__ == "__main__":
    print("Starting MCP server on http://localhost:8000")
    mcp_server.run(transport="streamable-http")
