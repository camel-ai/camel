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
from camel.toolkits import NotionMCPToolkit
from camel.types import ModelPlatformType, ModelType


async def main():
    notion_mcp_toolkit = NotionMCPToolkit(timeout=60)

    # connect to notion mcp
    await notion_mcp_toolkit.connect()

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    chat_agent = ChatAgent(
        model=model,
        tools=notion_mcp_toolkit.get_tools(),
    )

    response = await chat_agent.astep(
        """create a new page in my notion named 'CAMEL-AI Notion MCP Toolkit 
        Test'""",
    )
    print(response.msg.content)

    # disconnect from notion mcp
    await notion_mcp_toolkit.disconnect()


# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
""""
===========================================================================
I have created a new page in your Notion named 'CAMEL-AI Notion MCP Toolkit 
Test'. You can access it here: https://www.notion.so/
23720ddf035c8146812bf34c9b8d30c5 Is there anything else you would like to do 
with this page?
============================================================================
"""
