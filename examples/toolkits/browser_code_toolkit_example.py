# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
"""
Browser Code Toolkit Example

This example demonstrates how to use BrowserCodeToolkit to let Agent control
browser by writing Python code.
"""

import asyncio
import logging

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits.browser_code_toolkit import BrowserCodeToolkit
from camel.types import ModelPlatformType, ModelType

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()],
)

# Set log levels
logging.getLogger('camel.agents').setLevel(logging.INFO)
logging.getLogger('camel.models').setLevel(logging.INFO)
logging.getLogger('camel.toolkits').setLevel(logging.INFO)
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env.test file

USER_DATA_DIR = "User_Data"

# Create model backend
model_backend = ModelFactory.create(
    model_platform=ModelPlatformType.AZURE,
    model_type=ModelType.GPT_4_1,
    model_config_dict={"temperature": 0.0, "top_p": 1},
)

print("=" * 80)
print("Browser Code Toolkit Example")
print("=" * 80)

# ============================================================================
# Example 1: Using default browser tools
# ============================================================================
print("\n[Example 1] Using default browser tools")
print("-" * 80)

toolkit_default = BrowserCodeToolkit(
    browser_mode="typescript",
    sandbox="internal_python",
    headless=False,
    user_data_dir=USER_DATA_DIR,
)
print(f"Enabled tools: {toolkit_default.enabled_tools}\n")

# ============================================================================
# Example 2: Using ALL available browser tools
# ============================================================================
print("\n[Example 2] Using ALL browser tools")
print("-" * 80)

toolkit_all = BrowserCodeToolkit(
    browser_mode="typescript",
    sandbox="internal_python",
    headless=False,
    user_data_dir=USER_DATA_DIR,
    enabled_tools=BrowserCodeToolkit.ALL_TOOLS,
)
print(f"Enabled tools: {toolkit_all.enabled_tools}\n")

# ============================================================================
# Example 3: Custom browser tools selection (Recommended for production)
# ============================================================================
print("\n[Example 3] Using CUSTOM browser tools (Recommended)")
print("-" * 80)

# Select necessary tools based on your task requirements
custom_tools = [
    "browser_open",
    "browser_close",
    "browser_visit_page",
    "browser_back",
    "browser_forward",
    "browser_click",
    "browser_type",
    "browser_enter",
    "browser_get_page_snapshot",
    # "browser_get_som_screenshot",  # Uncomment if you need screenshots
    # "browser_scroll",               # Uncomment if you need scrolling
    # "browser_console_exec",         # Advanced feature
]

toolkit_custom = BrowserCodeToolkit(
    browser_mode="typescript",
    sandbox="internal_python",
    headless=False,
    user_data_dir=USER_DATA_DIR,
    enabled_tools=custom_tools,
    print_code_output=True,  # Print code execution to console (default: True)
    browser_log_to_file=True,  # Generate detailed logs
    stealth=True,  # Enable stealth mode
    viewport_limit=True,  # Limit snapshot to current viewport
)

print(f"Enabled tools: {toolkit_custom.enabled_tools}")
print(f"Using user data directory: {USER_DATA_DIR}")
print()

# ============================================================================
# System Prompt for Agent
# ============================================================================

SYSTEM_PROMPT = """You are a browser automation expert. You can write Python code to control a browser.

CRITICAL RULES:
1. **DO NOT write placeholder code** - Never use comments like "# find ref here" or fake ref values
2. **Work step-by-step** - You CANNOT complete tasks in one code execution
3. **Get information first** - Always call browser.get_snapshot() to see actual ref IDs before using them
4. **Use actual values only** - Only use ref IDs that you have seen in snapshot output

WORKFLOW (MUST FOLLOW):
Step 1: Open browser and get initial snapshot
```python
browser.open()
browser.visit_page("https://example.com")
snapshot = browser.get_snapshot()
print(snapshot)  # You will see the actual ref IDs here
```

Step 2: After seeing the snapshot, write code to interact with ACTUAL refs
```python
# Now you know ref="e15" is the search box from previous output
browser.type(ref="e15", text="search query")
browser.enter()
```

Step 3: Get new snapshot after interaction if needed
```python
snapshot = browser.get_snapshot()
print(snapshot)  # See updated page structure
```

EXECUTION RETURNS:
When you execute code, you will receive:
- The code you executed
- All print() output showing snapshots, results, etc.
- Any error messages

USE THIS OUTPUT to decide your next step!

COMMON MISTAKES TO AVOID:
❌ Writing all code at once without seeing ref IDs
❌ Using placeholder refs like "ref_to_find" or "element_ref"
❌ Assuming ref IDs without checking snapshot
❌ Not reading the execution output from previous step

✅ CORRECT APPROACH:
1. Execute code to get snapshot
2. Read the output to find actual ref IDs
3. Execute new code using those actual ref IDs
4. Repeat until task is complete


"""

# Create Agent with system prompt
agent = ChatAgent(
    model=model_backend,
    system_message=BaseMessage.make_assistant_message(
        role_name="Browser Automation Expert",
        content=SYSTEM_PROMPT,
    ),
    tools=toolkit_custom.get_tools(),
    max_iteration=10,
)

# ============================================================================
# Task Prompts
# ============================================================================

# Simple test task
SIMPLE_TASK = r"""
Write Python code to:
1. Open browser
2. Visit https://www.google.com
3. Get the page snapshot and print first 500 characters
4. Close the browser

Use the execute_browser_code tool.
"""

# Complex search task
SEARCH_TASK = r"""
Visit the website "https://www.google.com/travel/flights/" using a browser and search for a round-trip journey from Edinburgh to Manchester on January 28th, 2026, departing and returning on the same day. Find and extract the lowest price available for this itinerary. Return the lowest price option as a plain text summary including outbound and return departure times, total price, and airline details.      
填写日期的时候先点击日期框，然后再分别输入去程和返程日期，用正确格式如：2026-01-28
enter可以作为确认
"""


async def main() -> None:
    """Run the example"""
    try:
        print("\n" + "=" * 80)
        print("Starting Task")
        print("=" * 80)

        # Choose task (change to SEARCH_TASK for complex example)
        task = SEARCH_TASK

        print(f"\nTask:\n{task}\n")
        print("-" * 80)

        # Execute task
        response = await agent.astep(task)

        print("\n" + "=" * 80)
        print("Agent Response")
        print("=" * 80)
        print(response.msgs[0].content if response.msgs else "<no response>")

    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean up resources
        print("\n" + "=" * 80)
        print("Cleanup")
        print("=" * 80)
        print("Closing browser...")
        await toolkit_custom.cleanup()
        print("✓ Browser closed successfully.")


# ============================================================================
# Direct Code Execution Example (Without Agent)
# ============================================================================


async def direct_execution_example():
    """Direct code execution example (without agent)"""
    print("\n" + "=" * 80)
    print("Direct Code Execution Example (Without Agent)")
    print("=" * 80)

    toolkit = BrowserCodeToolkit(
        browser_mode="typescript",
        sandbox="internal_python",
        headless=False,
        user_data_dir=USER_DATA_DIR,
        enabled_tools=[
            "browser_open",
            "browser_visit_page",
            "browser_get_page_snapshot",
            "browser_close",
        ],
    )

    # Write Python code directly
    code = """
# Open browser
print("Opening browser...")
result = browser.open()
print(f"Browser opened: {result.get('result', 'success')}")

# Visit website
print("\\nVisiting Google...")
result = browser.visit_page("https://www.google.com")
print(f"Page loaded: {result.get('result', 'success')}")

# Get page snapshot
print("\\nGetting page snapshot...")
snapshot = browser.get_snapshot()
print(f"Snapshot (first 300 chars):\\n{snapshot[:300]}")

# Close browser
print("\\nClosing browser...")
browser.close()
print("Done!")
"""

    print("Executing code:\n")
    print(code)
    print("\n" + "-" * 80)
    print("Output:\n")

    # Execute code
    result = toolkit.execute_browser_code(code)
    print(result)

    print("\n✓ Direct execution completed.")


if __name__ == "__main__":
    # Run Agent example
    asyncio.run(main())

    # To run direct execution example, uncomment below:
    # asyncio.run(direct_execution_example())
