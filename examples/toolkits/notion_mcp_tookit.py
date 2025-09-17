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
        """create a new page in my notion named 'Camel Introduction' 
and add some content describing Camel as a lightweight multi-agent framework 
that supports role-driven collaboration and modular workflows."""
    )

    print("=== Model Response ===")
    print(response.msg.content)

    # disconnect from notion mcp
    await notion_mcp_toolkit.disconnect()


# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())

"""
===========================================================================
[681981] [Remote→Local] 0
[681981] [Local→Remote] notifications/initialized
[681981] [Local→Remote] tools/list
[681981] [Remote→Local] 1
/home/lyz/Camel/camel/camel/memories/blocks/chat_history_block.py:73: 
UserWarning: The `ChatHistoryMemory` is empty.
  warnings.warn("The `ChatHistoryMemory` is empty.")
[681981] [Local→Remote] tools/call
[681981] [Remote→Local] 2
I have created the page "Camel Introduction" for you. You can view it here: 
https://www.notion.so/2626be7b2793819aaf2cfe686a554bdd
[681981] 
Shutting down...
============================================================================
"""
