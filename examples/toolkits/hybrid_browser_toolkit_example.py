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
import asyncio
import logging

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import HybridBrowserToolkit
from camel.types import ModelPlatformType, ModelType

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ],
)

logging.getLogger('camel.agents').setLevel(logging.INFO)
logging.getLogger('camel.models').setLevel(logging.INFO)
logging.getLogger('camel.models').setLevel(logging.INFO)
logging.getLogger('camel.toolkits.hybrid_browser_toolkit').setLevel(
    logging.DEBUG
)
USER_DATA_DIR = "User_Data"

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env.test file

model_backend = ModelFactory.create(
    model_platform=ModelPlatformType.AZURE,
    model_type=ModelType.GPT_4_1,
    model_config_dict={"temperature": 0.0, "top_p": 1},
)

# Example 1: Use default tools (basic functionality)
# web_toolkit_default = HybridBrowserToolkit(
#     headless=False,
#     user_data_dir=USER_DATA_DIR
# )
# print(f"Default tools: {web_toolkit_default.enabled_tools}")

# Example 2: Use all available tools
# web_toolkit_all = HybridBrowserToolkit(
#     headless=False,
#     user_data_dir=USER_DATA_DIR,
#     enabled_tools=HybridBrowserToolkit.ALL_TOOLS
# )
# print(f"All tools: {web_toolkit_all.enabled_tools}")

# Example 3: Use custom tools selection
custom_tools = [
    "browser_open",
    "browser_close",
    "browser_visit_page",
    "browser_back",
    "browser_forward",
    "browser_click",
    "browser_type",
    "browser_switch_tab",
    "browser_enter",
    "browser_get_page_snapshot",
    "browser_get_som_screenshot",  # remove it to achieve faster operation
    # "browser_press_key",
    # "browser_console_view",
    # "browser_console_exec",
    # "browser_mouse_drag",
]

web_toolkit_custom = HybridBrowserToolkit(
    headless=False,
    user_data_dir=USER_DATA_DIR,
    enabled_tools=custom_tools,
    browser_log_to_file=True,  # generate detailed log file in ./browser_log
    stealth=True,  # Using stealth mode during browser operation
    enable_reasoning=True,
    viewport_limit=True,
    default_start_url="https://www.google.com/travel/flights/",
    # Limit snapshot to current viewport to reduce context
)
print(f"Custom tools: {web_toolkit_custom.enabled_tools}")
# Use the custom toolkit for the actual task
agent = ChatAgent(
    model=model_backend,
    tools=[*web_toolkit_custom.get_tools()],
)

TASK_PROMPT = r"""
Visit the website "https://www.google.com/travel/flights/" using a browser and search for a round-trip journey from Edinburgh to Manchester on January 28th, 2026, departing and returning on the same day. Find and extract the lowest price available for this itinerary. Return the lowest price option as a plain text summary including outbound and return departure times, total price, and airline details.      
填写日期的时候先点击日期框，然后再分别输入去程和返程日期，用正确格式如：2026-01-28
enter可以作为确认，也可以用来执行搜索

如果遇到element not found, 可以用browser_get_page_snapshot获得最新snapshot
如果想看截屏，可以用browser_get_som_screenshot, 如果看到截屏中你的任务没有完成或者有问题，你需要对应的修改
确保起点终点，还有时间正确
"""


async def main() -> None:
    try:
        response = await agent.astep(TASK_PROMPT)
        print("Task:", TASK_PROMPT)
        print(f"Using user data directory: {USER_DATA_DIR}")
        print(f"Enabled tools: {web_toolkit_custom.enabled_tools}")
        print("\nResponse from agent:")
        print(response.msgs[0].content if response.msgs else "<no response>")
    finally:
        # Ensure browser is closed properly
        print("\nClosing browser...")
        await web_toolkit_custom.browser_close()
        print("Browser closed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
