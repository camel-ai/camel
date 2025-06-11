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
Simple example showing how to run a Workforce as an MCP server.

To test this example:
1. Install dependencies: pip install mcp camel-ai[all]
2. Run this script: python simple_workforce_mcp.py
3. The server will start on localhost:8001
4. Use an MCP client to connect and test the tools

Example MCP client usage:
- Call process_task with task_content="Analyze market trends"
- Call get_workforce_info to see workforce status
- Call add_single_agent_worker to add new workers
"""

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.societies.workforce import Workforce


def main():
    """Create and run a simple workforce MCP server."""

    # Create a basic workforce
    workforce = Workforce(description="Simple Analysis Team")

    # Add a basic analyst worker
    analyst_msg = BaseMessage.make_assistant_message(
        role_name="Analyst",
        content="You are a helpful analyst who can process various tasks.",
    )
    analyst = ChatAgent(system_message=analyst_msg)
    workforce.add_single_agent_worker(
        description="General purpose analyst", worker=analyst
    )

    print("Creating Workforce MCP server...")
    print("Server will be available at: http://localhost:8001")
    print("Press Ctrl+C to stop the server")

    # Convert to MCP server and run
    mcp_server = workforce.to_mcp(
        name="Simple-Workforce",
        description="A simple workforce for task processing",
        port=8001,
    )

    try:
        # This will start the server and block
        mcp_server.run()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
