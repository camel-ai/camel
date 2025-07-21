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
        "What's the content of url "
        "https://www.notion.so/Feature-update-1e029df5473f80cdbd2cf59b87266fbc?pvs=12?",
    )
    print(response.msg.content)

    # disconnect from notion mcp
    await notion_mcp_toolkit.disconnect()


# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
""""
===========================================================================
The "Feature update" page contains multiple exciting updates about 
CAMEL-AI's new features and integrations:

1. CAMEL-AI's BrowserToolkit now supports asynchronous operations. This 
improves efficiency, responsiveness, and performance in multi-task execution.

2. CAMEL-AI fully integrates the Mistral Medium model, enhancing the 
AI model options for various natural language tasks.

3. CAMEL-AI integrates the Playwright MCP Toolkit for enhanced multi-agent 
system capabilities and complex browser automation.

4. CAMEL-AI integrates with MCP Search Agent functionality, adding powerful 
search capabilities through the Model Context Protocol standard.

5. CAMEL-AI supports Agent as MCP Server functionality, enabling CAMEL-AI 
agents to serve as Model Context Protocol servers for other AI systems.

6. CAMEL-AI adds support for Google's Gemini 2.5 Pro Preview model, 
offering cutting-edge AI capabilities.

7. CAMEL-AI integrates with MarkItDown Loader, providing document 
conversion of various file formats into Markdown.
============================================================================
"""
