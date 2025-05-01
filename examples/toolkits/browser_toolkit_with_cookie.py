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
import gc
import os
import sys
import time

from playwright.sync_api import sync_playwright

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import BrowserToolkit
from camel.types import ModelPlatformType, ModelType


def save_auth_cookie(cookie_json_path: str, url: str):
    r"""Saves authentication cookies and browser storage state to a JSON file.

    This function launches a browser window and navigates to the specified URL,
    allowing the user to manually authenticate (log in) during a 60-second
    wait period.After authentication, it saves all cookies, localStorage, and
    sessionStorage data to the specified JSON file path, which can be used
    later to maintain authenticated sessions without requiring manual login.

    Args:
        cookie_json_path (str): Path where the authentication cookies and
            storage state will be saved as a JSON file. If the file already
            exists, it will be loaded first and then overwritten with updated
            state. The function checks if this file exists before attempting
            to use it.
        url (str): The URL to navigate to for authentication (e.g., a login
            page).

    Usage:
        1. The function opens a browser window and navigates to the specified
            URL
        2. User manually logs in during the 60-second wait period
        3. Browser storage state (including auth cookies) is saved to the
           specified file
        4. The saved state can be used in subsequent browser sessions to
           maintain authentication

    Note:
        The 60-second sleep is intentional to give the user enough time to
        complete the manual authentication process before the storage state
        is captured.
    """
    playwright = sync_playwright().start()

    # Launch visible browser window using Chromium
    browser = playwright.chromium.launch(headless=False, channel="chromium")

    # Check if cookie file exists before using it
    context_params = {"accept_downloads": True}
    if os.path.exists(cookie_json_path):
        context_params["storage_state"] = cookie_json_path

    context = browser.new_context(**context_params)
    page = context.new_page()
    page.goto(url)  # Navigate to the authentication URL
    # Wait for page to fully load
    page.wait_for_load_state("load", timeout=1000)
    time.sleep(60)  # Wait 60 seconds for user to manually authenticate
    # Save browser storage state (cookies, localStorage, etc.) to JSON file
    context.storage_state(path=cookie_json_path)

    browser.close()  # Close the browser when finished


def ensure_no_running_event_loops():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            print("Detected running event loop, attempting to close it...")
            loop.stop()
            loop.close()
    except RuntimeError:
        # No running event loop
        pass

    # Set new event loop policy to ensure clean state
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    else:
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

    # Create a new event loop but don't start it
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)

    # Force garbage collection to clean up any lingering references
    gc.collect()


# Now we can safely proceed with synchronous code
# NOTE: After saving the cookie, you need to comment out the following line
# and rerun the script, otherwise you would get error due to asyncio event loop
save_auth_cookie(cookie_json_path="cookie.json", url="https://www.amazon.com/")

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

# Create the BrowserToolkit with synchronous operation
web_toolkit = BrowserToolkit(
    headless=False,
    web_agent_model=web_agent_model,
    planning_agent_model=planning_agent_model,
    channel="chromium",
    cookie_json_path="cookie.json",
)

agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=model,
    tools=[*web_toolkit.get_tools()],
)

response = agent.step(
    "Navigate to Amazon.com and identify the current #1 best-selling product"
    " in the gaming category. Please provide the product name, price, and"
    " rating if available.",
)

print(response.msgs[0].content)
"""
==========================================================================
The current #1 best-selling product in the gaming category on Amazon is the 
**AutoFull C3 Gaming Chair**. 

- **Price:** $249.99
- **Rating:** 4.4 stars based on 5,283 ratings.
==========================================================================
"""
