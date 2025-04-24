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
"""
This example demonstrates how to use the `to_mcp` method to convert
a ChatAgent to an MCP server.
"""

from pathlib import Path

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import FunctionTool, SearchToolkit
from camel.types import ModelPlatformType


def main():
    # Create a model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type="gpt-3.5-turbo",
    )

    # Create a search toolkit
    search_toolkit = SearchToolkit()

    # Create a chat agent with tools
    chat_agent = ChatAgent(
        model=model,
        system_message="You are a helpful assistant that can search the web.",
        tools=[FunctionTool(search_toolkit.search_brave)],
    )

    # Generate MCP server file
    server_name = "SearchAgentMCP"
    output_path = Path(__file__).parent / "mcp_server_output"
    files = chat_agent.to_mcp(
        server_name=server_name,
        agent_name="search",
        description="A helpful assistant that can search the web.",
        output_path=output_path,
    )

    print(f"MCP server files generated at: {output_path}")
    print("Files generated:")
    for filename in files.keys():
        print(f"- {filename}")

    print("\nTo run the MCP server:")
    print(f"1. cd {output_path}")
    print(f"2. python {server_name.lower()}.py")


if __name__ == "__main__":
    main()
