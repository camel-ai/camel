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
from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import BrowserToolkit
from camel.types import ModelPlatformType, ModelType

# This example demonstrates using BrowserToolkit with a persistent user data
# directory.
# The browser will store data (cookies, local storage, etc.) in this directory,
# allowing sessions to persist across runs.

# NOTE:
# 1. If you run this script for the first time, a directory named
# "my_browser_profile"
#    (or whatever you set user_data_dir to) will be created.
# 2. Since headless=False, a browser window will open. If the task involves
# a website
#    that requires login (e.g., Amazon for personalized content or purchase
#    history),
#    you may need to manually log in through the browser window during the
#    first run.
# 3. On subsequent runs, the browser will use the data stored in
# "my_browser_profile",
#    potentially remembering your login session, preferences, etc.

USER_DATA_DIR = "my_browser_profile"  # Directory to store persistent
# browser data

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig(
        temperature=0.0,
    ).as_dict(),
)

web_agent_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig(
        temperature=0.0,
    ).as_dict(),
)

planning_agent_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig(
        temperature=0.0,
    ).as_dict(),
)

# Create the BrowserToolkit with a user_data_dir for persistence
web_toolkit = BrowserToolkit(
    headless=False,  # Set to False to see the browser and interact if needed
    web_agent_model=web_agent_model,
    planning_agent_model=planning_agent_model,
    channel="chromium",
    user_data_dir=USER_DATA_DIR,
    # Specify the user data directory. If set to None, a fresh browser
    # profile will be launched (no cache, no history, no logged-in sessions,
    # etc.).
)

agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=model,
    tools=[*web_toolkit.get_tools()],
)

# Example task:
# If you manually log into Amazon in the browser window that opens,
# subsequent runs might show personalized content or keep you logged in.
response = agent.step(
    "Navigate to Amazon.com and identify the current #1 best-selling product"
    " in the 'Home & Kitchen' category. Please provide the product name, "
    "price,"
    " and rating if available.",
)

print(
    "Task: Navigate to Amazon.com and find the #1 best-seller in 'Home & "
    "Kitchen'."
)
print(f"Using user data directory: {USER_DATA_DIR}")
print("\nResponse from agent:")
print(response.msgs[0].content)

# Example of expected output structure (actual product will vary):
# """
# ==========================================================================
# The current #1 best-selling product in the Home & Kitchen category on
# Amazon is
# the **XYZ Smart Coffee Maker**.
#
# - **Price:** $79.99
# - **Rating:** 4.6 stars based on 12,345 ratings.
# ==========================================================================
# """
