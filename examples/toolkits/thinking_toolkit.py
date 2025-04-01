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

# Initialize model and toolkit
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=ChatGPTConfig().as_dict(),
)

thinking_toolkit = ThinkingToolkit()
tools = thinking_toolkit.get_tools()

# Create an agent with the thinking toolkit
sys_msg = (
    "You are a helpful assistant that can think through problems "
    "step by step."
)

agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)

# Example usage
usr_msg = (
    "Help me solve: If a train travels at 60 mph, how long to"
    "cover 180 miles?"
)

response = agent.step(usr_msg)
print(response.msgs[0].content)
print("\nTool calls:")
print(response.info['tool_calls'])

"""
===============================================================================
The train will take 3 hours to cover 180 miles at a speed of 60 mph.

Tool calls:
[
    ToolCallingRecord(
        tool_name='think',
        args={
            'thought': ('To find the time taken to cover a certain distance at'
                      'a constant speed, we can use the formula: time = '
                      'distance / speed. In this case, the distance is 180 '
                      'miles and the speed is 60 mph.')
        },
        result=('Thoughts:\n- To find the time taken to cover a certain '
               'distance at a constant speed, we can use the formula: time = '
               'distance / speed. In this case, the distance is 180 miles and '
               'the speed is 60 mph.'),
        tool_call_id='call_M6QQ0ymwpVNtpXaacWLhWtqA'
    ),
    ToolCallingRecord(
        tool_name='think', 
        args={
            'thought': ('Now, substituting the values into the formula: time ='
                      '180 miles / 60 mph. This can be calculated to find the '
                      'time in hours.')
        },
        result=('Thoughts:\n- To find the time taken to cover a certain '
               'distance at a constant speed, we can use the formula: time = '
               'distance / speed. In this case, the distance is 180 miles and '
               'the speed is 60 mph.\n- Now, substituting the values into the '
               'formula: time = 180 miles / 60 mph. This can be calculated to '
               'find the time in hours.'),
        tool_call_id='call_7CXZctOm3BbBaSq1YeCNql45'
    ),
    ToolCallingRecord(
        tool_name='think',
        args={
            'thought': ('Calculating: time = 180 / 60 = 3 hours. Therefore, it'
                      'will take the train 3 hours to cover 180 miles at a '
                      'speed of 60 mph.')
        },
        result=('Thoughts:\n- To find the time taken to cover a certain '
               'distance at a constant speed, we can use the formula: time = '
               'distance / speed. In this case, the distance is 180 miles and '
               'the speed is 60 mph.\n- Now, substituting the values into the '
               'formula: time = 180 miles / 60 mph. This can be calculated to '
               'find the time in hours.\n- Calculating: time = 180 / 60 = 3 '
               'hours. Therefore, it will take the train 3 hours to cover 180 '
               'miles at a speed of 60 mph.'),
        tool_call_id='call_n1SOosiFYvl2pO6yuq9dLhQb'
    )
]
===============================================================================
"""
