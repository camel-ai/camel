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
from camel.toolkits import ThinkingToolkit
from camel.types import ModelPlatformType, ModelType

# Create a Model
model_config_dict = ChatGPTConfig(temperature=0.0).as_dict()
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=model_config_dict,
)

# Initialize the ThinkingToolkit
thinking_toolkit = ThinkingToolkit()
tools = thinking_toolkit.get_tools()

# Set up the ChatAgent with thinking capabilities
sys_msg = (
    "You are an assistant that can break down complex problems and think "
    "through solutions step by step. Use the thinking toolkit to organize "
    "your thoughts, reflect on the problem, and create plans."
)

agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)

# Example: Problem solving with thinking toolkit
print("\nExample: Problem solving with thinking toolkit")
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
================================================================================
The train's total journey time for covering 300 miles at 60 mph, including  
3 stops of 15 minutes each, is 5.75 hours (or 5 hours and 45 minutes).

Tool Calls:
[
    ToolCallingRecord(
        tool_name='plan',
        args={'plan': '1. Compute the travel time for 300 miles at 60 mph '
                      'without stops.\n'
                      '2. Determine the total duration of the stops.\n'
                      '3. Sum the travel time and stop duration to obtain the '
                      'total journey time.'},
        result='Plan: 1. Compute the travel time for 300 miles at 60 mph '
               'without stops.\n'
               '2. Determine the total duration of the stops.\n'
               '3. Sum the travel time and stop duration to obtain the total '
               'journey time.',
        tool_call_id='call_2XY3C9luha0RtJ9fC40Ev8Vn'
    ),
    ToolCallingRecord(
        tool_name='think',
        args={'thought': 'Using the formula time = distance / speed, the '
                         'travel time for 300 miles at 60 mph is 300 / 60 = '
                         '5 hours.'},
        result='Thought: Using the formula time = distance / speed, the '
               'travel time for 300 miles at 60 mph is 300 / 60 = 5 hours.',
        tool_call_id='call_ZtX4soBTgqad3J7vso2EaOJd'
    ),
    ToolCallingRecord(
        tool_name='think',
        args={'thought': 'Each of the 3 stops lasts 15 minutes, so the total '
                         'stop time is 3 * 15 = 45 minutes.'},
        result='Thought: Each of the 3 stops lasts 15 minutes, so the total '
               'stop time is 3 * 15 = 45 minutes.',
        tool_call_id='call_yckRhTcQkrAg8CsWQAtYDTTv'
    ),
    ToolCallingRecord(
        tool_name='think',
        args={'thought': 'Convert 45 minutes to hours: 45 / 60 = 0.75 hours.'},
        result='Thought: Convert 45 minutes to hours: 45 / 60 = 0.75 hours.',
        tool_call_id='call_ypHQ9ifRz3QgUBewUn0kaWge'
    ),
    ToolCallingRecord(
        tool_name='think',
        args={'thought': 'Summing the travel time and stop duration: 5 hours '
                         '+ 0.75 hours = 5.75 hours.'},
        result='Thought: Summing the travel time and stop duration: 5 hours '
               '+ 0.75 hours = 5.75 hours.',
        tool_call_id='call_7ZZ3NWQuudVhHxvdq2Fr54j9'
    ),
    ToolCallingRecord(
        tool_name='reflect',
        args={'reflection': 'The total journey time for the train covering '
                            '300 miles at 60 mph, with 3 stops of 15 minutes '
                            'each,is 5.75 hours (or 5 hours and 45 minutes).'},
        result='Reflection: The total journey time for the train covering '
               '300 miles at 60 mph, with 3 stops of 15 minutes each, is '
               '5.75 hours (or 5 hours and 45 minutes).',
        tool_call_id='call_3gcRxyTefaCNAaONXkYbGO5O'
    )
]
"""
