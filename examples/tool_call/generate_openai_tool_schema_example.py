# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

import os

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType, ModelType

# Set OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("API key not found in environment variables.")


# Define a function which does't have a docstring
def get_perfect_square(n: int) -> int:
    return n**2


# Create a model instance
model_config_dict = ChatGPTConfig(temperature=1.0).as_dict()
agent_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=model_config_dict,
)

# Create a FunctionTool with the function
function_tool = FunctionTool(
    get_perfect_square, schema_assistant=agent_model, use_schema_assistant=True
)
print("\nGenerated OpenAI Tool Schema:")
print(function_tool.get_openai_tool_schema())

# Set system message for the assistant
assistant_sys_msg = BaseMessage.make_assistant_message(
    role_name="Assistant", content="You are a helpful assistant."
)

# Create a ChatAgent with the tool
camel_agent = ChatAgent(
    system_message=assistant_sys_msg, model=agent_model, tools=[function_tool]
)
camel_agent.reset()

# Define a user message
user_prompt = "What is the perfect square of 2024?"
user_msg = BaseMessage.make_user_message(role_name="User", content=user_prompt)

# Get response from the assistant
response = camel_agent.step(user_msg)
print("\nAssistant Response:")
print(response.msg.content)

print("""
===============================================================================
Warning: No model provided. Use GPT_4O_MINI to generate the schema for 
the function get_perfect_square. Attempting to generate one using LLM.
Successfully generated the OpenAI tool schema for 
the function get_perfect_square.

Generated OpenAI Tool Schema:
{'type': 'function', 'function': {'name': 'get_perfect_square', 
'description': 'Calculates the perfect square of a given integer.', 
'parameters': {'properties': {'n': {'type': 'integer', 
'description': 'The integer to be squared.'}}, 'required': ['n'], 
'type': 'object'}}}
      
[FunctionCallingRecord(func_name='get_perfect_square', args={'n': 2024}, 
result={'result': 4096576})]
===============================================================================
""")
