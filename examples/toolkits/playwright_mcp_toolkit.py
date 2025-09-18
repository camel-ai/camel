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

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import PlaywrightMCPToolkit
from camel.types import ModelPlatformType, ModelType


async def main():
    # Create PlaywrightMCPToolkit (now inherits directly from MCPToolkit)
    playwright_mcp_toolkit = PlaywrightMCPToolkit()

    # Connect to playwright mcp (inherited method from MCPToolkit)
    await playwright_mcp_toolkit.connect()

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # Pydantic basemodel as input params format
    class AgentResponse(BaseModel):
        url: str = Field(description="Url of the repository")
        stars: int = Field(description="Stars of the repository")

    chat_agent = ChatAgent(
        model=model,
        tools=playwright_mcp_toolkit.get_tools(),  # Inherited method
    )

    response = await chat_agent.astep(
        "Navigate to https://github.com/camel-ai/camel and get the star count",
        response_format=AgentResponse,
    )

    print("=== Model Response ===")
    print(response.msg.content)

    # Disconnect from playwright mcp (inherited method from MCPToolkit)
    await playwright_mcp_toolkit.disconnect()


# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())

"""
==============================================================================
{
  "url": "https://github.com/camel-ai/camel",
  "stars": 14040
}
==============================================================================
"""
