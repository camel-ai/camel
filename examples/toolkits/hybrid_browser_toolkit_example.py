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

model_backend = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
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
    "open_browser",
    "close_browser",
    "visit_page",
    "get_som_screenshot",  # Add screenshot capability
    "click",
    "type",
]

web_toolkit_custom = HybridBrowserToolkit(
    headless=False, user_data_dir=USER_DATA_DIR, enabled_tools=custom_tools
)
print(f"Custom tools: {web_toolkit_custom.enabled_tools}")


# Use the custom toolkit for the actual task
agent = ChatAgent(
    model=model_backend,
    tools=[*web_toolkit_custom.get_tools()],
    max_iteration=10,
)

TASK_PROMPT = r"""
Open Amazon.com, search for a beautiful keyboard, 
click it and add it to the cart
and use get_som_screenshot to see the final 
picture of keyboard and describe its appearance
"""


async def main() -> None:
    response = await agent.astep(TASK_PROMPT)
    print("Task:", TASK_PROMPT)
    print(f"Using user data directory: {USER_DATA_DIR}")
    print(f"Enabled tools: {web_toolkit_custom.enabled_tools}")
    print("\nResponse from agent:")
    print(response.msgs[0].content if response.msgs else "<no response>")

    try:
        await web_toolkit_custom.close_browser()
    except Exception as err:
        logging.warning(
            "Failed to close " "browser session explicitly: %s", err
        )


if __name__ == "__main__":
    asyncio.run(main())
