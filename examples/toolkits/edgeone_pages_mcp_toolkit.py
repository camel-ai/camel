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
from camel.toolkits import EdgeOnePagesMCPToolkit
from camel.types import ModelPlatformType, ModelType


async def main():
    edgeone_pages_mcp_toolkit = EdgeOnePagesMCPToolkit()

    # connect to edgeone pages mcp
    await edgeone_pages_mcp_toolkit.connect()

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    chat_agent = ChatAgent(
        model=model,
        tools=edgeone_pages_mcp_toolkit.get_tools(),
    )

    response = await chat_agent.astep(
        "write a hello world page",
    )

    print("=== Model Response ===")
    print(response.msg.content)

    # disconnect from edgeone pages mcp
    await edgeone_pages_mcp_toolkit.disconnect()


# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())

"""
==============================================================================
I've created a Hello World page for you! The page has been deployed and is now 
live at:

**https://mcp.edgeone.site/share/M-MXzJzHJ3mGc013OQNIM**

The page features:
- A modern, gradient background
- Centered "Hello World!" heading
- Clean, responsive design
- A welcome message below the main heading
==============================================================================
"""
