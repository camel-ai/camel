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
from camel.toolkits import BrowserToolkit, FileWriteToolkit
from camel.types import ModelPlatformType, ModelType

# Initialize Models (as in the original script)
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

# Initialize Toolkits
browser_toolkit = BrowserToolkit(
    headless=False,  # Changed to True for non-interactive testing
    web_agent_model=web_agent_model,
    planning_agent_model=planning_agent_model,
    channel="chromium",
)

file_write_toolkit = FileWriteToolkit(output_dir="./toolkit_example_outputs")

# Initialize Agent with combined tools
agent = ChatAgent(
    system_message=(
        "You are a helpful assistant that can browse websites, "
        "extract content, and save it to files."
    ),
    model=model,
    tools=[*browser_toolkit.get_tools(), *file_write_toolkit.get_tools()],
)

# Define the multi-step task prompt
task_prompt = (
    "1. Setup the browser. "
    "2. Visit the page 'https://www.camel-ai.org/'. "
    "3. Scroll down the page to the end. "
    "4. Write this summary to a markdown file named "
    "'camel_ai_org_summary.md'. "
    "Tell me the name of the file you created."
)

print(f"Executing task: {task_prompt}\n")

# Execute the task
response = agent.step(task_prompt)

# Print the agent's final response
if response:
    if response.msgs:
        print("Agent's final response:")
        print(response.msgs[0].content)
    else:
        print("No response from agent.")
else:
    print("No response from agent.")

print(
    "\nScript finished. Check the './toolkit_example_outputs' directory "
    "for 'camel_ai_org_summary.md'."
)
