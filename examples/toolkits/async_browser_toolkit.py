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
import sys

sys.path.append("..")

from dotenv import load_dotenv

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.tasks import Task
from camel.toolkits import AsyncBrowserToolkit, FunctionTool
from camel.types import ModelPlatformType, ModelType

load_dotenv("../.env")

web_agent_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
    model_config_dict={"temperature": 0},
)

planning_agent_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
    model_config_dict={"temperature": 0},
)

web_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
    model_config_dict={"temperature": 0},
)

browser_simulator_toolkit = AsyncBrowserToolkit(
    headless=False,
    cache_dir="tmp/browser",
    web_agent_model=web_agent_model,
    planning_agent_model=planning_agent_model,
)

web_agent = ChatAgent(
    """
You are a helpful assistant that can search the web, simulate browser 
actions, and provide relevant information to solve the given task.
""",
    model=web_model,
    tools=[FunctionTool(browser_simulator_toolkit.browse_url)],
)

# Create custom agents for the workforce
task_agent = ChatAgent(
    "You are a helpful task planner.",
    model=ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict={"temperature": 0},
    ),
)

coordinator_agent = ChatAgent(
    "You are a helpful coordinator.",
    model=ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict={"temperature": 0},
    ),
)

workforce = Workforce(
    "Gaia Workforce",
    task_agent=task_agent,
    coordinator_agent=coordinator_agent,
)

workforce.add_single_agent_worker(
    """
    An agent that can search the web, simulate browser actions, 
    and provide relevant information to solve the given task.""",
    worker=web_agent,
)

question = (
    "Navigate to Amazon.com and identify the current #1 best-selling "
    "product in the gaming category. Please provide the product name,"
    "price, and rating if available."
)
task = Task(
    content=question,
    id="0",
)

task_result = workforce.process_task(task)
print(task_result.result)

"""
==========================================================================
The current #1 best-selling product in the gaming category on Amazon is 
'Minecraft: Switch Edition - Nintendo Switch'. The price is $35.97, and 
it has a rating of 4.8 stars based on 1,525 ratings.
==========================================================================
"""
