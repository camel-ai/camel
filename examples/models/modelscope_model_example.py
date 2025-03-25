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
from camel.configs import ModelScopeConfig
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType

model = ModelFactory.create(
    model_platform=ModelPlatformType.MODELSCOPE,
    model_type=ModelType.MODELSCOPE_QWEN_2_5_32B_INSTRUCT,
    model_config_dict=ModelScopeConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=[
        *MathToolkit().get_tools(),
    ],
)
# Let agent step the message
response = agent.step(
    "Assume now is 2024 in the Gregorian calendar, University of Oxford was set up in 1096, estimate the current age of University of Oxford"  # noqa: E501
)

# Check tool calling
print(response)
print(response.info['tool_calls'])
print(response.msgs[0].content)


'''
==============================================================================
msgs=[BaseMessage(role_name='Assistant', role_type=<RoleType.ASSISTANT: 'assistant'>, meta_dict={}, content='The University of Oxford is approximately 928 years old in the year 2024.', video_bytes=None, image_list=None, image_detail='auto', video_detail='low', parsed=None)] terminated=False info={'id': 'chatcmpl-6eeb61bf-1003-9fe3-962e-88ffe5d1704e', 'usage': {'completion_tokens': 22, 'prompt_tokens': 717, 'total_tokens': 739, 'completion_tokens_details': None, 'prompt_tokens_details': None}, 'termination_reasons': ['stop'], 'num_tokens': 80, 'tool_calls': [ToolCallingRecord(tool_name='sub', args={'a': 2024, 'b': 1096}, result=928, tool_call_id='call_05f85b0fdd9241be912883')], 'external_tool_call_requests': None}
[ToolCallingRecord(tool_name='sub', args={'a': 2024, 'b': 1096}, result=928, tool_call_id='call_05f85b0fdd9241be912883')]
The University of Oxford is approximately 928 years old in the year 2024.
==============================================================================
'''  # noqa: E501
