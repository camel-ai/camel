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

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import PlaywrightMCPToolkit
from camel.types import ModelPlatformType, ModelType


async def main():
    playwright_mcp_toolkit = PlaywrightMCPToolkit()

    # connect to playwright mcp
    await playwright_mcp_toolkit.connect()

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    chat_agent = ChatAgent(
        model=model,
        tools=playwright_mcp_toolkit.get_tools(),
    )

    response = await chat_agent.astep(
        "search for camel-ai using google search, how many stars does it have?"
    )
    print(response.msg.content)

    # disconnect from playwright mcp
    await playwright_mcp_toolkit.disconnect()


# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())

"""
==============================================================================
The GitHub repository for **camel-ai** has **12,338 stars**. If you need more
information or details about the project, feel free to ask!
==============================================================================
"""
