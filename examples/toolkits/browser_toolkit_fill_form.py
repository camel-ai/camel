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
import logging

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import BrowserToolkit
from camel.types import ModelPlatformType, ModelType

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('browser_dom_debug.log'),  # File output
    ],
)

# Set specific loggers for more detailed output
logging.getLogger('camel.toolkits.browser_toolkit').setLevel(logging.DEBUG)
logging.getLogger('camel.toolkits.browser_toolkit_commons').setLevel(
    logging.DEBUG
)
logging.getLogger('camel.agents').setLevel(logging.INFO)
logging.getLogger('camel.models').setLevel(logging.INFO)


# This example demonstrates using BrowserToolkit with DOM mode (non-visual).
# DOM mode uses structured text representation of page elements instead of
# visual screenshots
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig().as_dict(),
)

web_agent_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig().as_dict(),
)


# Create the BrowserToolkit with DOM mode enabled
print("Initializing BrowserToolkit with DOM mode...")
web_toolkit = BrowserToolkit(
    headless=False,  # Can run headless since we don't need visual feedback
    web_agent_model=web_agent_model,
    channel="chromium",
    use_visual_mode=False,  # Enable DOM mode
)
print(
    f"BrowserToolkit initialized: use_visual_mode="
    f"{web_toolkit.use_visual_mode}"
)

print("Creating ChatAgent with DOM-optimized system message...")
agent = ChatAgent(
    system_message="You are a helpful assistant that can browse the web "
    "efficiently using DOM analysis.",
    model=model,
    tools=[*web_toolkit.get_tools()],
)

print("Starting web automation task...")
print("-" * 60)

response = agent.step(
    "to https://httpbin.org/forms/post fill out the form with test data: "
    "- Customer name: 'John Doe' "
    "- Telephone: '+1-555-0123' "
    "- Email: 'john.doe@example.com' "
    "- Small pizza size "
    "- Add Choose Onion and mushroom toppings "
    "Then submit the form and report the response."
)
print(response.msgs[0].content)
