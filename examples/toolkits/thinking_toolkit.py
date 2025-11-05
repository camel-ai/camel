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
from camel.models import ModelFactory
from camel.toolkits import ThinkingToolkit
from camel.types import ModelPlatformType, ModelType

# Create a Model
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
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
===============================================================================
The train's total journey time for traveling 300 miles at 60 mph, with 
3 stops of 15 minutes each, is 5.75 hours. This consists of 5 hours of 
travel time and 0.75 hours (or 45 minutes) of stop time. The conversion 
of stop time from minutes to hours was explicitly noted for clarity.

Tool Calls:
[
    ToolCallingRecord(
        tool_name='plan',
        args={
            'plan': '1. Compute the travel time for 300 miles at 60 mph '
                    'without stops.\n'
                    '2. Determine the total stop time.\n'
                    '3. Sum the travel time and stop time to get the total '
                    'journey duration.'
        },
        result='Plan: 1. Compute the travel time for 300 miles at 60 mph '
               'without stops.\n'
               '2. Determine the total stop time.\n'
               '3. Sum the travel time and stop time to get the total journey '
               'duration.',
        tool_call_id='call_kKYeTFLMGPf0mhimAZ8hapFk'
    ),
    ToolCallingRecord(
        tool_name='think',
        args={
            'thought': 'Using the formula time = distance / speed, where '
                       'distance = 300 miles and speed = 60 mph, we can '
                       'determine the travel time.'
        },
        result='Thought: Using the formula time = distance / speed, where '
               'distance = 300 miles and speed = 60 mph, we can determine '
               'the travel time.',
        tool_call_id='call_t3DXWahikwhc8ps0y2GTE9ko'
    ),
    ToolCallingRecord(
        tool_name='think',
        args={
            'thought': 'The total stop time is calculated as: number of '
                       'stops * time per stop, which is 3 * 15 minutes.'
        },
        result='Thought: The total stop time is calculated as: number of '
               'stops * time per stop, which is 3 * 15 minutes.',
        tool_call_id='call_MM1YlTPmiMhhiy6HWqraKh8E'
    ),
    ToolCallingRecord(
        tool_name='hypothesize',
        args={
            'hypothesis': 'The travel time for 300 miles at 60 mph should '
                          'be 5 hours.'
        },
        result='Hypothesis: The travel time for 300 miles at 60 mph should '
               'be 5 hours.',
        tool_call_id='call_F16dfESrJmUDwieYDA2aCheB'
    ),
    ToolCallingRecord(
        tool_name='hypothesize',
        args={
            'hypothesis': 'The total stop time for 3 stops of 15 minutes '
                          'each should be 45 minutes.'
        },
        result='Hypothesis: The total stop time for 3 stops of 15 minutes '
               'each should be 45 minutes.',
        tool_call_id='call_coxWcLPATfKNdiqQDz853pm4'
    ),
    ToolCallingRecord(
        tool_name='synthesize',
        args={
            'synthesis': 'The total journey time for the train traveling '
                         '300 miles at 60 mph, with 3 stops of 15 minutes '
                         'each, is 5.75 hours. This includes 5 hours of '
                         'travel time and 0.75 hours (or 45 minutes) of '
                         'stop time. The conversion of stop time from '
                         'minutes to hours was explicitly noted for clarity.'
        },
        result='Synthesis: The total journey time for the train traveling '
               '300 miles at 60 mph, with 3 stops of 15 minutes each, is '
               '5.75 hours. This includes 5 hours of travel time and 0.75 '
               'hours (or 45 minutes) of stop time. The conversion of stop '
               'time from minutes to hours was explicitly noted for clarity.',
        tool_call_id='call_9AHg54snm17XN7Mj1UzgSV04'
    )
]
===============================================================================
"""
