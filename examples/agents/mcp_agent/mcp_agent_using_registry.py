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
import logging
import os

from camel.agents import MCPAgent
from camel.models import ModelFactory
from camel.types import (
    ACIRegistryConfig,
    BaseMCPRegistryConfig,
    ModelPlatformType,
    ModelType,
    # SmitheryRegistryConfig,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('camel')
logger.setLevel(logging.DEBUG)


async def example_with_registry_config(
    message: str, registry_config: BaseMCPRegistryConfig
):
    r"""Example using MCPAgent with registry configurations."""

    # Create a model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
    )

    # Create MCPAgent with registry configurations
    agent = MCPAgent(
        model=model,
        registry_configs=[registry_config],
    )

    # Use agent with async context manager
    async with agent:
        response = await agent.astep(message)
        print(f"\nResponse from {message}:")
        print(response.msgs[0].content)


async def main():
    r"""Run examples."""
    # smithery_config = SmitheryRegistryConfig(
    #     api_key=os.getenv("SMITHERY_API_KEY"),
    #     profile=os.getenv("SMITHERY_PROFILE"),
    #     os="darwin",
    # )
    aci_config = ACIRegistryConfig(
        api_key=os.getenv("ACI_API_KEY"),
        linked_account_owner_id=os.getenv("ACI_LINKED_ACCOUNT_OWNER_ID"),
    )
    # Registry configuration example
    message = "What MCP tools I can use for connecting to the Gmail?"
    # message = "Use Brave MCP search tools to search info about Camel-AI.org."
    await example_with_registry_config(
        message=message,
        registry_config=aci_config,
        # registry_config=smithery_config,
    )


if __name__ == "__main__":
    asyncio.run(main())

"""
===========================================================================
Response from What MCP tools I can use for connecting to the Gmail?:
I found several MCP tools that can connect to Gmail. Here are the options:

1. **Google Workspace Server** (@rishipradeep-think41/gsuite-mcp)
   - Manage emails and calendar events through Gmail and Calendar APIs
   - [Configure here](https://smithery.ai/server/@rishipradeep-think41/gsuite-mcp/config)

2. **VeyraX MCP** (@VeyraX/veyrax-mcp)
   - Connects to 70+ tools including Gmail and Calendar
   - [Configure here](https://smithery.ai/server/@VeyraX/veyrax-mcp/config)

3. **Google Workspace MCP Server** (google-workspace-server)
   - Interact with Gmail and Calendar APIs
   - [Configure here](https://smithery.ai/server/google-workspace-server/config)

4. **Headless Gmail Server** (@baryhuang/mcp-headless-gmail)
   - Access and send emails through Gmail without local credential setup
   - [Configure here](https://smithery.ai/server/@baryhuang/mcp-headless-gmail/config)

5. **Google Workspace Server** (@rishipradeep-think41/gmail-backupmcp)
   - Another option for managing Gmail and Calendar

Each of these tools requires configuration before it can be used. You'll need 
to click on one of the configuration links above to set up the tool with your 
Gmail credentials. Once you've completed the configuration, let me know which 
tool you've chosen, and I can help you use it to connect to your Gmail account.
===========================================================================
"""

"""
===========================================================================
Response from Use Brave MCP search tools to search info about Camel-AI.org.:
# CAMEL-AI.org: Information and Purpose

Based on my search results, here's what I found about CAMEL-AI.org:

## Organization Overview
CAMEL-AI.org is the first LLM (Large Language Model) multi-agent framework and 
an open-source community. The name CAMEL stands for "Communicative Agents for 
Mind Exploration of Large Language Model Society."

## Core Purpose
The organization is dedicated to "Finding the Scaling Law of Agents" - this 
appears to be their primary research mission, focusing on understanding how 
agent-based AI systems scale and develop.

## Research Focus
CAMEL-AI is a research-driven organization that explores:
- Scalable techniques for autonomous cooperation among communicative agents
- Multi-agent frameworks for AI systems
- Data generation for AI training
- AI society simulations

## Community and Collaboration
- They maintain an active open-source community
- They invite contributors and collaborators through platforms like Slack and 
Discord
- The organization has a research collaboration questionnaire for those 
interested in building or researching environments for LLM-based agents

## Technical Resources
- Their code is available on GitHub (github.com/camel-ai) with 18 repositories
- They provide documentation for developers and researchers at 
docs.camel-ai.org
- They offer tools and cookbooks for working with their agent framework

## Website and Online Presence
- Main website: https://www.camel-ai.org/
- GitHub: https://github.com/camel-ai
- Documentation: https://docs.camel-ai.org/

The organization appears to be at the forefront of research on multi-agent AI 
systems, focusing on how these systems can cooperate autonomously and scale 
effectively.
===========================================================================
"""
