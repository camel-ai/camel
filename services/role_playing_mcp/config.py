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
from typing import Dict

from camel.models import ModelFactory
from camel.societies import RolePlaying
from camel.types import ModelPlatformType, ModelType, TaskType

# Prevent logging since MCP needs to use stdout
root_logger = logging.getLogger()
root_logger.handlers = []
root_logger.addHandler(logging.NullHandler())

# =====================================================================
# CUSTOMIZATION SECTION - YOU CAN MODIFY THIS PART TO DEFINE ROLEPLAYING
# =====================================================================

# Define default models to use
default_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4_1_MINI,
    api_key=os.getenv("OPENAI_API_KEY"),  # Set this environment variable
)

# Alternative OpenRouter model for higher capabilities
openrouter_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
    model_type="anthropic/claude-3-opus:20240229",
    url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),  # Set this environment variable
)

# Define default role playing scenarios
DEFAULT_ROLE_SCENARIOS = {
    "code_collaboration": {
        "assistant_role_name": "Senior Software Engineer",
        "user_role_name": "Software Product Manager",
        "task_prompt": (
            "Collaborate on designing and implementing a simple todo list "
            "application."
        ),
        "task_type": TaskType.CODE,
        "model": default_model,
    },
    "creative_writing": {
        "assistant_role_name": "Creative Writer",
        "user_role_name": "Book Editor",
        "task_prompt": (
            "Work on developing a short story concept with compelling "
            "characters and plot."
        ),
        "task_type": TaskType.AI_SOCIETY,
        "model": default_model,
    },
    "business_planning": {
        "assistant_role_name": "Business Consultant",
        "user_role_name": "Entrepreneur",
        "task_prompt": "Develop a business plan for a new technology startup.",
        "task_type": TaskType.AI_SOCIETY,
        "model": default_model,
    },
    "scientific_discussion": {
        "assistant_role_name": "Research Scientist",
        "user_role_name": "Science Journalist",
        "task_prompt": (
            "Discuss recent advancements in artificial intelligence and "
            "their implications."
        ),
        "task_type": TaskType.AI_SOCIETY,
        "model": openrouter_model,
    },
}

# Set up default role playing configuration
default_assistant_role = "AI Assistant"
default_user_role = "Human User"
default_task_prompt = "Have a helpful and informative conversation."
default_task_type = TaskType.AI_SOCIETY

# Create a default instance of RolePlaying
role_playing = RolePlaying(
    assistant_role_name=default_assistant_role,
    user_role_name=default_user_role,
    task_prompt=default_task_prompt,
    with_task_specify=True,
    with_task_planner=False,
    task_type=default_task_type,
    model=default_model,
)

# Map of active role playing sessions
active_sessions: Dict[str, RolePlaying] = {}
