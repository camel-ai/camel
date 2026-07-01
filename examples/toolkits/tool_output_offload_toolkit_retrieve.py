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
Multi-turn example demonstrating the full offload → retrieve cycle.

Turn 1: The agent browses a content-rich page. The large tool output
        triggers the offload hint, so the model calls summarize_and_offload()
        to compress it and save the original to disk.

Turn 2: The user asks for specific details that are NOT in the summary
        (e.g., exact URLs, dates). The model sees the [OFFLOADED OUTPUT]
        marker in memory and calls retrieve_offloaded_tool_output() to
        fetch the full original content from disk.

This showcases the complete lifecycle:
  browse → offload (with model-written summary) → retrieve (on demand)
"""

import os

os.environ["CAMEL_MODEL_LOG_ENABLED"] = "true"
os.environ["CAMEL_LOG_DIR"] = "camel_logs"

import asyncio
import logging

from camel.agents import ChatAgent
from camel.configs import GeminiConfig
from camel.models import ModelFactory
from camel.toolkits import HybridBrowserToolkit, ToolOutputOffloadToolkit
from camel.types import ModelPlatformType, ModelType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    # --- Toolkits ---
    browser_toolkit = HybridBrowserToolkit(
        stealth=True,
        headless=False,  # Show browser for debugging
        navigation_timeout=15000,  # 15s navigation timeout
        network_idle_timeout=3000,  # 3s network idle timeout
        page_stability_timeout=3000,  # 3s stability timeout
    )

    # Use a low threshold so the demo triggers offloading easily
    offload_toolkit = ToolOutputOffloadToolkit(hint_threshold=3000)

    # --- Model ---
    model = ModelFactory.create(
        model_platform=ModelPlatformType.GEMINI,
        model_type=ModelType.GEMINI_3_FLASH,
        model_config_dict=GeminiConfig(temperature=0.0).as_dict(),
    )

    # --- Agent ---
    system_message = (
        "You are a helpful research assistant with web browsing abilities. "
    )

    agent = ChatAgent(
        system_message=system_message,
        model=model,
        tools=[*browser_toolkit.get_tools(), *offload_toolkit.get_tools()],
        toolkits_to_register_agent=[offload_toolkit],
    )

    # ==================== Turn 1 ====================
    # The agent browses a page with lots of content.
    # Expected: large output → hint → model calls summarize_and_offload()
    print("=" * 60)
    print("TURN 1: Browse and summarize (triggers offload)")
    print("=" * 60)

    response = await agent.astep(
        "Go to https://www.camel-ai.org/blog and give me a brief overview "
        "of what the page contains."
    )
    print(f"\n[Agent response]\n{response.msgs[0].content}\n")

    # ==================== Turn 2 ====================
    # Ask for specific details the summary does NOT contain.
    # Expected: model sees [OFFLOADED OUTPUT] in memory →
    #           calls retrieve_offloaded_tool_output() to get full content
    print("=" * 60)
    print("TURN 2: Ask for details (triggers retrieve)")
    print("=" * 60)

    response = await agent.astep(
        "Now I need the exact titles and URLs of the first 5 blog posts "
        "listed on that page. Please give me the precise links."
    )
    print(f"\n[Agent response]\n{response.msgs[0].content}\n")


if __name__ == "__main__":
    asyncio.run(main())
