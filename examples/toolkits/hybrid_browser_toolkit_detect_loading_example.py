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
Test Page Stability Detection using Carbon Code Screenshot Tool

Test Objectives:
1. Verify that the enhanced waitForPageStability correctly waits
   for all three states
2. Observe DOM changes and network request completion after
   interacting with Carbon's code editor and export feature

Prerequisites:
- Internet connection to access https://carbon.now.sh/
"""

import asyncio
import logging

from dotenv import load_dotenv

load_dotenv()

from camel.agents import ChatAgent  # noqa: E402
from camel.models import ModelFactory  # noqa: E402
from camel.toolkits import HybridBrowserToolkit  # noqa: E402
from camel.types import ModelPlatformType, ModelType  # noqa: E402

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ],
)

logging.getLogger('camel.toolkits.hybrid_browser_toolkit').setLevel(
    logging.DEBUG
)

model_backend = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict={"temperature": 0.0, "top_p": 1},
)

# Configure the toolkit
web_toolkit = HybridBrowserToolkit(
    headless=False,
    enabled_tools=[
        "browser_open",
        "browser_close",
        "browser_visit_page",
        "browser_click",
        "browser_type",
        "browser_enter",
        "browser_scroll",
        "browser_get_page_snapshot",
    ],
    browser_log_to_file=True,
    stealth=True,
)

agent = ChatAgent(
    model=model_backend,
    tools=[*web_toolkit.get_tools()],
    max_iteration=15,
)

# Test task: Open Carbon, enter code, and export
TASK_PROMPT = r"""
Please perform the following steps to test page stability detection
using Carbon (code screenshot tool):

1. Open Carbon: https://carbon.now.sh/

2. Clear the existing code in the editor and enter the following code:
   ```python
   def hello_world():
       print("Hello, World!")
       return True

   if __name__ == "__main__":
       hello_world()
   ```
3. Find and click the "Export" button

4. Take a snapshot of the page to verify the current state

"""


async def main() -> None:
    try:
        print("=" * 60)
        print("Carbon Code Screenshot - Page Stability Detection Test")
        print("=" * 60)
        print(f"Enabled tools: {web_toolkit.enabled_tools}")
        print("=" * 60)

        response = await agent.astep(TASK_PROMPT)

        print("\nTool calls:")
        print(str(response.info['tool_calls']))

        print("\nResponse from agent:")
        print(response.msgs[0].content)

    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("\nClosing browser...")
        await web_toolkit.browser_close()
        print("Browser closed.")


if __name__ == "__main__":
    asyncio.run(main())
