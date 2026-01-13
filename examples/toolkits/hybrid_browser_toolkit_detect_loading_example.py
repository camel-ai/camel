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
Test Page Stability Detection for Xiaohongshu "One-Click Format" Feature

Test Objectives:
1. Verify that the enhanced waitForPageStability correctly waits
   for all three states
2. Observe DOM changes and network request completion after
   clicking "One-Click Format"

Prerequisites:
- Must have a logged-in Xiaohongshu account in the User_Data directory
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

# Use a User Data directory that has saved Xiaohongshu login state
USER_DATA_DIR = "User_Data"

model_backend = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict={"temperature": 0.0, "top_p": 1},
)

# Configure the toolkit
web_toolkit = HybridBrowserToolkit(
    headless=False,
    user_data_dir=USER_DATA_DIR,
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

# Test task: Open Xiaohongshu publish page, enter content,
# click one-click format
TASK_PROMPT = r"""
Please perform the following steps to test Xiaohongshu's
"One-Click Format" feature:

1. First, open the Xiaohongshu Creator Center publish page: https://creator.xiaohongshu.com/publish/publish

2. Click on the "Write Long Article" tab, then click "New Creation"

3. Enter the following test content in the body area:
    Title: test
    Body:
    "This is a test text to verify the one-click format feature.

   First paragraph content goes here.

   Second paragraph content goes here.

   Third paragraph content goes here."


4. Find and click the "One-Click Format" button

5. After completion, click the button on the left of preview button

"""


async def main() -> None:
    try:
        print("=" * 60)
        print("Xiaohongshu One-Click Format Feature - Page Stability Test")
        print("=" * 60)
        print(f"Using User Data directory: {USER_DATA_DIR}")
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
