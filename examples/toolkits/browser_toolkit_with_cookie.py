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
from camel.utils import browser_toolkit_save_auth_cookie

# NOTE: After saving the cookie, you need to comment out the following line
# and rerun the script, otherwise you would get error due to asyncio event loop
browser_toolkit_save_auth_cookie(
    cookie_json_path="cookie.json", url="https://www.amazon.com/", wait_time=10
)

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
