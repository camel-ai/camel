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
from camel.toolkits.task_planning_toolkit import TaskPlanningToolkit
from camel.types import ModelPlatformType, ModelType

# Create a Model
model_config_dict = ChatGPTConfig(temperature=0.0).as_dict()
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEEPSEEK,
    model_type=ModelType.DEEPSEEK_CHAT,
    model_config_dict=model_config_dict,
)

# Initialize the ThinkingToolkit
task_planning_toolkit = TaskPlanningToolkit()
tools = task_planning_toolkit.get_tools()


# Set up the ChatAgent with thinking capabilities
sys_msg = (
    "You are an assistant that can decompose the complex task to subTasks,"
    "Use the task_planning tool to decompose your task and rePlan your task"
    "when you find the current subTasks is not reasonable."
)

agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)

# Example: Problem solving with task_planning toolkit
print("\nExample: Problem solving with task_planning toolkit")
print("=" * 80)

usr_msg = """
Help me solve this math problem:
If a train travels at 60 mph and needs to cover 300 miles, 
with 3 stops of 15 minutes each, how long will the journey take?
"""

response = agent.step(usr_msg)
print(response.msgs[0].content)
print("\nTool calls:")
print(response.info['tool_calls'])

"""
Example: Problem Solving with Thinking Toolkit
===============================================================================
The train's total journey time for traveling 300 miles at 60 mph, with 
3 stops of 15 minutes each, is 5.75 hours. This consists of 5 hours of 
travel time and 0.75 hours (or 45 minutes) of stop time. The conversion 
of stop time from minutes to hours was explicitly noted for clarity.

Tool calls:
[
    ToolCallingRecord
        tool_name='decompose_task', 
        args={'tasks': [{'content': 'Calculate the total travel time without 
            stops.', 'id': '1'}, {'content': 'Calculate the total stop time.', 
            'id': '2'}, {'content': 'Add the travel time and stop time to get
             the total journey time.', 'id': '3'}]}, 
        result=[{'content': 'Calculate the total travel time without stops.', 
            'id': '1'}, {'content': 'Calculate the total stop time.', 
            'id': '2'}, {'content': 'Add the travel time and stop time to get 
            the total journey time.', 'id': '3'}], 
        tool_call_id='call_0_824fe110-be29-491d-ada7-5422ddfe5afb')
]

===============================================================================
"""
