# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

"""
Example demonstrating the ToolOutputOffloadToolkit.

This toolkit allows agents to manage memory by:
1. Listing recent tool outputs that could be summarized/offloaded
2. Summarizing specific tool outputs and storing originals externally
3. Retrieving original content when needed

This is useful when tool outputs are very large and consume too much
context window space.
"""

import asyncio
import logging

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import HybridBrowserToolkit, ToolOutputOffloadToolkit
from camel.types import ModelPlatformType, ModelType

# Enable debug logging to see what's happening
logging.basicConfig(level=logging.DEBUG)


async def main():
    # Create a browser toolkit that can produce large outputs
    # Use Python mode instead of TypeScript mode for debugging
    browser_toolkit = HybridBrowserToolkit(
        stealth=True,
        headless=False,  # Show browser for debugging
        navigation_timeout=15000,  # 15s navigation timeout
        network_idle_timeout=3000,  # 3s network idle timeout
        page_stability_timeout=3000,  # 3s stability timeout
    )
    print("Browser toolkit created (Python mode)")

    # Create the offload toolkit for managing large tool outputs
    # - min_output_length: Only show outputs >= 1000 chars as offloadable
    offload_toolkit = ToolOutputOffloadToolkit(auto_offload_threshold=500)

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_5_2,
        model_config_dict=ChatGPTConfig(
            temperature=0.0,
        ).as_dict(),
    )

    # Create agent with both toolkits
    # IMPORTANT: Use toolkits_to_register_agent to register the offload toolkit
    # This allows the toolkit to access agent memory for offloading
    system_message = """You are a helpful assistant."""

    agent = ChatAgent(
        system_message=system_message,
        model=model,
        tools=[*browser_toolkit.get_tools(), *offload_toolkit.get_tools()],
        toolkits_to_register_agent=[offload_toolkit],
    )

    # Test with a simpler task first to avoid complex navigation
    response = await agent.astep(
        "search information about camel-ai.org, go to the blog they wrote, "
        "check first 5, give me a summary"
    )
    print(response.msgs[0].content)


if __name__ == "__main__":
    asyncio.run(main())
