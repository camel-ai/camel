# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import FileToolkit, PlanningWorktreeToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = (
    "You are a software engineering assistant that plans before coding. "
    "When asked to implement something, first enter plan mode to outline "
    "the approach, then write the implementation files."
)

# Initialize toolkits — combine planning with file operations
planning_toolkit = PlanningWorktreeToolkit()
file_toolkit = FileToolkit()
tools = planning_toolkit.get_tools() + file_toolkit.get_tools()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.GPT_5_4,
)

# Set agent
camel_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)

# Example: Plan and implement a simple utility module
usr_msg = (
    "I need a Python utility module called `string_utils.py` that provides "
    "two functions: `snake_to_camel(s)` and `camel_to_snake(s)` for "
    "converting between naming conventions. "
    "First enter plan mode and write your implementation plan to the plan "
    "file, then exit plan mode so I can review it before you write the code."
)

# Get response information
response = camel_agent.step(usr_msg)
print(str(response.info['tool_calls']))

'''
===============================================================================

===============================================================================
'''
