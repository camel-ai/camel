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
Example: Convert CAMEL Toolkit to Skill

This example shows how to:
1. Generate a skill file from a toolkit
2. Use state persistence for stateful skills
"""

from camel.toolkits import MathToolkit, SearchToolkit

# =============================================================================
# Example 1: Basic skill generation
# =============================================================================

math_toolkit = MathToolkit()

# Generate skill file
skill_path = math_toolkit.to_skill(
    output_dir="./examples/toolkits/generated_skills",
    name="math",
    description="Mathematical operations for calculations",
)
print(f"Generated skill: {skill_path}")

# =============================================================================
# Example 2: Custom skill content
# =============================================================================

search_toolkit = SearchToolkit()

custom_content = """# Web Search

Search the web using multiple search engines.

## Tools

### search_google
Search Google for information.

### search_duckduckgo
Search DuckDuckGo for privacy-focused results.

## Usage
Use these tools to find up-to-date information from the web.
"""

skill_path = search_toolkit.to_skill(
    output_dir="./examples/toolkits/generated_skills",
    name="web-search",
    content=custom_content,
)
print(f"Generated skill: {skill_path}")

# =============================================================================
# Example 3: Stateful skill with state persistence
# =============================================================================

# Save state after operations
math_toolkit.save_state(
    state={
        "last_result": 42,
        "history": ["add(1, 2)", "multiply(3, 4)"],
    },
    session_id="calculation-task",
)
print("State saved")

# Later: restore state in a new session
restored_state = math_toolkit.load_state(session_id="calculation-task")
print(f"Restored state: {restored_state}")

# =============================================================================
# Example 4: Browser toolkit with stateful skill
# =============================================================================

# For stateful toolkits like browser, you can persist session data
try:
    from camel.toolkits import HybridBrowserToolkit

    browser = HybridBrowserToolkit(headless=True)

    # Generate skill with custom state instructions
    browser.to_skill(
        output_dir="./examples/toolkits/generated_skills",
        name="browser",
        content="""# Browser Automation

Control a web browser for automation tasks.

## State Management

This skill persists browser state (cookies, current URL) between sessions.
Use `session_id` to resume previous sessions.

## Tools

### browser_open
Start browser and navigate to URL.

### browser_click
Click element by ref ID.

### browser_type
Type text into input field.

### browser_get_page_snapshot
Get interactive elements on current page.

## Example

```
1. browser_open()
2. browser_visit_page(url="https://example.com")
3. snapshot = browser_get_page_snapshot()
4. browser_click(ref="e5")
```
""",
    )

    # Save browser state for resumption
    browser.save_state(
        state={
            "last_url": "https://example.com",
            "cookies_saved": True,
        },
        session_id="browser-task-1",
    )

except ImportError:
    print("HybridBrowserToolkit requires playwright")
