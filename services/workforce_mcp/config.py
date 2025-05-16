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
import os

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.toolkits import (
    CodeExecutionToolkit,
    SearchToolkit,
    ThinkingToolkit,
)
from camel.types import ModelPlatformType
from camel.types.enums import ModelType

# Prevent logging since MCP needs to use stdout
root_logger = logging.getLogger()
root_logger.handlers = []
root_logger.addHandler(logging.NullHandler())

# ========================================================================
# CUSTOMIZATION SECTION - YOU CAN MODIFY THIS PART TO DEFINE YOUR WORKFORCE
# ========================================================================

# Define models for different components
coordinator_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type="nvidia/llama-3.1-nemotron-70b-instruct:free",
    url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),  # Set this environment variable
)

task_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type="nvidia/llama-3.1-nemotron-70b-instruct:free",
    url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),  # Set this environment variable
)

worker_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4_1_MINI,
    api_key=os.getenv("OPENAI_API_KEY"),  # Set this environment variable
)

# Define the base workforce
workforce = Workforce(
    description="A versatile workforce system for solving various tasks",
    coordinator_agent_kwargs={"model": coordinator_model},
    task_agent_kwargs={"model": task_model},
    new_worker_agent_kwargs={
        "model": worker_model,
        "tools": [
            SearchToolkit().search_duckduckgo,
            *CodeExecutionToolkit().get_tools(),
            *ThinkingToolkit().get_tools(),
        ],
    },
)

# Create a default worker for general tasks
general_worker = ChatAgent(
    model=worker_model,
    system_message=(
        "You are a versatile worker that can handle various general tasks."
    ),
    tools=[
        SearchToolkit().search_duckduckgo,
        *ThinkingToolkit().get_tools(),
    ],
)

# Create a worker for coding tasks
coding_worker = ChatAgent(
    model=worker_model,
    system_message=(
        "You are a coding expert that can implement solutions "
        "in various programming languages."
    ),
    tools=[
        *CodeExecutionToolkit().get_tools(),
        *ThinkingToolkit().get_tools(),
    ],
)

# Create a worker for research tasks
research_worker = ChatAgent(
    model=worker_model,
    system_message=(
        "You are a research expert that can find and analyze "
        "information from various sources."
    ),
    tools=[
        SearchToolkit().search_duckduckgo,
        *ThinkingToolkit().get_tools(),
    ],
)

# Add workers to the workforce
workforce.add_single_agent_worker("General Worker", general_worker)
workforce.add_single_agent_worker("Coding Worker", coding_worker)
workforce.add_single_agent_worker("Research Worker", research_worker)

# Add a role-playing worker for creative tasks
workforce.add_role_playing_worker(
    description="Creative Collaboration Team",
    assistant_role_name="Creative Director",
    user_role_name="Content Creator",
    assistant_agent_kwargs={"model": worker_model},
    user_agent_kwargs={"model": worker_model},
    chat_turn_limit=5,
)
