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

planning_agent_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig().as_dict(),
)

# Create the BrowserToolkit with DOM mode enabled
print("Initializing BrowserToolkit with DOM mode...")
web_toolkit = BrowserToolkit(
    headless=False,  # Can run headless since we don't need visual feedback
    web_agent_model=web_agent_model,
    planning_agent_model=planning_agent_model,
    channel="chromium",
    use_visual_mode=False,  # Enable DOM mode for faster, text-based analysis
    # DOM mode uses structured text representation of interactive elements
    # instead of screenshots, making it more efficient for many tasks
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
print("ChatAgent created successfully")

# Example task that works well with DOM mode:
# Searching and extracting structured information from Wikipedia
print("Starting web automation task...")
print("Task: Extract Python programming language information from Wikipedia")
print("Mode: DOM-based (non-visual) analysis")
print("-" * 60)

response = agent.step(
    "Navigate to Wikipedia.org and search for 'Python programming language'. "
    "Extract the following information from the main article: "
    "1. The year Python was first released "
    "2. Who created Python "
    "3. The current stable version mentioned "
    "Please provide this information in a structured format."
)

print("Task execution completed!")

print(
    "Task: Navigate to Wikipedia and extract Python programming language info"
)
print("Mode: DOM mode (non-visual, structure-based)")
print("\nResponse from agent:")
print(response.msgs[0].content)

# Example of expected output structure:
# """
# ==========================================================================
# Python Programming Language Information:
#
# 1. **First Release Year:** 1991
# 2. **Creator:** Guido van Rossum
# 3. **Current Stable Version:** Python 3.12.1 (as of latest update)
#
# This information was extracted from the Wikipedia article on Python
# programming language using DOM-based analysis.
# ==========================================================================
# """
