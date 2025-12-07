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
Example: Browser Toolkit with Reasoning Support

This example demonstrates how to use the reasoning decorator with the
HybridBrowserToolkit. The reasoning feature allows agents to provide
explanations for their actions, which are stored in the agent's context.

This is particularly useful for:
- Improving agent decision-making by maintaining a chain of thought
- Debugging agent behavior by seeing the reasoning behind actions
- Better handling of actions that require waiting (e.g., after clicking submit)

Usage:
    python browser_toolkit_with_reasoning.py

Requirements:
    - Set OPENAI_API_KEY environment variable
    - playwright installed with browsers (npx playwright install)
"""

import asyncio
import logging

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits.hybrid_browser_toolkit_py import (
    HybridBrowserToolkit,
    ReasoningContextManager,
    enable_reasoning_for_toolkit,
)
from camel.types import ModelPlatformType, ModelType

# Configure logging to see reasoning messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logging.getLogger(
    'camel.toolkits.hybrid_browser_toolkit_py.reasoning_decorator'
).setLevel(logging.DEBUG)

# Example 1: Create toolkit with reasoning enabled at initialization
# This is the recommended approach - simple and clean
print("=" * 60)
print("Example 1: Toolkit with reasoning enabled at initialization")
print("=" * 60)

toolkit = HybridBrowserToolkit(
    headless=True,  # Set to False to see the browser
    enable_reasoning=True,  # Enable reasoning for all browser actions
    enabled_tools=[
        "browser_open",
        "browser_close",
        "browser_visit_page",
        "browser_click",
        "browser_type",
        "browser_enter",
        "browser_wait_user",
    ],
)

print(f"Reasoning enabled: {toolkit._enable_reasoning}")
print(f"Enabled tools: {toolkit.enabled_tools}")


# Example 2: Enable reasoning on an existing toolkit
# Use this when you want to add reasoning to a toolkit after creation
print("\n" + "=" * 60)
print("Example 2: Enable reasoning on existing toolkit")
print("=" * 60)

toolkit2 = HybridBrowserToolkit(headless=True)
toolkit2 = enable_reasoning_for_toolkit(toolkit2)

print(f"Reasoning enabled: {toolkit2._reasoning_enabled}")


# Example 3: Using reasoning in browser actions (manual demonstration)
print("\n" + "=" * 60)
print("Example 3: Demonstrating reasoning in actions")
print("=" * 60)


async def demo_reasoning():
    """Demonstrate how reasoning works with browser actions."""
    print("\nStarting browser session...")

    # Open browser and visit a page
    result = await toolkit.browser_open()
    print(f"Browser opened: {result.get('result', 'No result')}")

    # Visit a page with reasoning (REQUIRED when reasoning is enabled)
    # The reasoning parameter forces the agent to explain why it's
    # performing this action - this is now mandatory, not optional
    result = await toolkit.browser_visit_page(
        url="https://example.com",
        reasoning=(
            "I'm visiting example.com to demonstrate the reasoning feature. "
            "This page is simple and loads quickly."
        ),
    )
    print(f"\nVisited page: {result.get('result', 'No result')}")
    print("Reasoning was stored in context")

    # Close the browser
    await toolkit.browser_close()
    print("\nBrowser closed")


# Run the demonstration
asyncio.run(demo_reasoning())


# Example 4: Full agent integration with reasoning
print("\n" + "=" * 60)
print("Example 4: Full agent integration")
print("=" * 60)


async def demo_agent_with_reasoning():
    """
    Demonstrate using the browser toolkit with reasoning in an agent.

    When the agent uses browser actions with reasoning, the reasoning
    is automatically stored in the agent's context/memory, helping
    maintain a chain of thought.
    """
    # Create model backend
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict={"temperature": 0.0},
    )

    # Create toolkit with reasoning enabled
    browser_toolkit = HybridBrowserToolkit(
        headless=True,
        enable_reasoning=True,
        enabled_tools=[
            "browser_open",
            "browser_close",
            "browser_visit_page",
            "browser_click",
            "browser_type",
            "browser_enter",
        ],
    )

    # Create agent with the toolkit
    # The toolkits_to_register_agent parameter is important - it allows
    # the toolkit to access the agent's memory for storing reasoning
    chat_agent = ChatAgent(
        model=model,
        tools=[*browser_toolkit.get_tools()],
        toolkits_to_register_agent=[browser_toolkit],
        max_iteration=5,
        system_message="""
        You are a web automation assistant. When performing browser
        actions, always provide reasoning for your actions using the
        'reasoning' parameter.

        For example, when clicking a button, explain why you're clicking
        it and what you expect to happen. This helps maintain a clear
        chain of thought.

        If an action requires waiting for page updates (like clicking
        submit), explain this in your reasoning.
        """,
    )

    print("Agent created with reasoning-enabled browser toolkit")
    print("The agent will store its reasoning in context when using browser")
    print("actions, improving decision-making for subsequent actions.")
    print(f"Agent initialized: {chat_agent is not None}")

    # Note: In a real scenario, you would have the agent perform tasks
    # and it would automatically use the reasoning parameter when calling
    # browser actions, with the reasoning stored in its memory.

    # Clean up
    try:
        await browser_toolkit.browser_close()
    except Exception:
        pass


# Uncomment to run the agent demo (requires OPENAI_API_KEY)
# asyncio.run(demo_agent_with_reasoning())


# Example 5: Using ReasoningContextManager for tracking
print("\n" + "=" * 60)
print("Example 5: Using ReasoningContextManager")
print("=" * 60)

# The ReasoningContextManager can be used to collect and track
# reasoning during a browser session
with ReasoningContextManager() as ctx:
    # Add reasoning entries manually (in practice, this is done
    # automatically by the decorator)
    ctx.add_reasoning(
        "browser_click",
        "Clicking login button to access the user dashboard",
    )
    ctx.add_reasoning(
        "browser_type",
        "Entering username to authenticate",
    )
    ctx.add_reasoning(
        "browser_wait_user",
        "Waiting for 2FA verification to complete",
    )

    # Get all reasoning
    all_reasoning = ctx.get_all_reasoning()
    print(f"Collected {len(all_reasoning)} reasoning entries:")
    for entry in all_reasoning:
        print(f"  - {entry['action']}: {entry['reasoning'][:50]}...")

print("\n" + "=" * 60)
print("Examples complete!")
print("=" * 60)
