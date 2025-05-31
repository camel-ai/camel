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
from camel.toolkits import SearchToolkit
from camel.types import ModelPlatformType
from camel.types.enums import ModelType

# Prevent logging since MCP needs to use stdout
root_logger = logging.getLogger()
root_logger.handlers = []
root_logger.addHandler(logging.NullHandler())


# ========================================================================
# CUSTOMIZATION SECTION - YOU CAN MODIFY THIS PART TO DEFINE YOUR OWN AGENT
# ========================================================================

# Define the model - replace with your preferred model configuration
chat_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type="nvidia/llama-3.1-nemotron-70b-instruct:free",
    url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),  # Set this environment variable
)

reasoning_model = ModelFactory.create(
    model_platform=ModelPlatformType.DEEPSEEK,
    model_type=ModelType.DEEPSEEK_REASONER,
    api_key=os.getenv("DEEPSEEK_API_KEY"),  # Set this environment variable
)

search_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4_1_MINI,
    api_key=os.getenv("OPENAI_API_KEY"),  # Set this environment variable
)

# Create a default chat agent - customize as needed
chat_agent = ChatAgent(
    model=chat_model,
    system_message="You are a helpful assistant.",
    # Uncomment to set a specific output language
    # output_language="en",  # or "zh", "es", "fr", etc.
)

chat_agent_description = """
The general agent is a helpful assistant that can answer questions and help
with tasks.
"""

reasoning_agent = ChatAgent(
    model=reasoning_model,
    system_message="You are a helpful assistant.",
)

reasoning_agent_description = """
The reasoning agent is a helpful assistant that can reason about the world.
"""


# Create another agent for searching the web
toolkit = SearchToolkit()
search_agent = ChatAgent(
    model=search_model,
    system_message="You are a helpful assistant.",
    tools=toolkit.get_tools(),  # type: ignore[arg-type]
)

search_agent_description = """
The search agent is a helpful assistant that can search the web.
"""

# Provide a list of agents with names
agents_dict = {
    "general": chat_agent,
    "search": search_agent,
    "reasoning": reasoning_agent,
}

# Provide descriptions for each agent
description_dict = {
    "general": chat_agent_description,
    "search": search_agent_description,
    "reasoning": reasoning_agent_description,
}
