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

import os

from colorama import Fore

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.runtimes import DaytonaRuntime
from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.types import ModelPlatformType, ModelType


def sample_function(x: int, y: int) -> int:
    return x + y


# Initialize toolkit
toolkit = CodeExecutionToolkit(verbose=True)

# Initialize the runtime with the API key
runtime = DaytonaRuntime(
    api_key=os.environ.get('DAYTONA_API_KEY'),
    api_url=os.environ.get('DAYTONA_API_URL'),
    language="python",
)

# Build the sandbox
runtime.build()

# Add toolkit to runtime
runtime.add(
    funcs=FunctionTool(sample_function),
    entrypoint="sample_function_entry",
)

# Get tools from runtime
tools = runtime.get_tools()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)

# Set up agent with system message
assistant_sys_msg = (
    "You are a personal math tutor and programmer. "
    "When asked a math question, "
    "write and run Python code to answer the question."
)

agent = ChatAgent(
    assistant_sys_msg,
    model,
    tools=tools,
)
agent.reset()

# Use the agent with runtime
prompt = (
    "Weng earns $12 an hour for babysitting. "
    "Yesterday, she just did 51 minutes of babysitting. How much did she earn?"
)
print(Fore.YELLOW + f"user prompt:\n{prompt}\n")

response = agent.step(prompt)

print(response)

# Clean up
runtime.stop()


"""
===============================================================================
user prompt:
Weng earns $12 an hour for babysitting. Yesterday, she just did 51 minutes of 
babysitting. How much did she earn?

msgs=[BaseMessage(role_name='Assistant', role_type=<RoleType.ASSISTANT: 
'assistant'>, meta_dict={}, content='Weng earned $10.20 for her 51 minutes of 
babysitting.', video_bytes=None, image_list=None, image_detail='auto', 
video_detail='low', parsed=None)] terminated=False info={'id': 
'chatcmpl-BTDAKaCAYvs6KFsxe9NmmxMHQiaxx', 'usage': {'completion_tokens': 18, 
'prompt_tokens': 122, 'total_tokens': 140, 'completion_tokens_details': 
{'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 
'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 
'cached_tokens': 0}}, 'termination_reasons': ['stop'], 'num_tokens': 99, 
'tool_calls': [ToolCallingRecord(tool_name='sample_function', args={'x': 12, 
'y': 51}, result=63, tool_call_id='call_clugUYSbh37yVAwpggG8Dwe0')], 
'external_tool_call_requests': None}
===============================================================================
"""
