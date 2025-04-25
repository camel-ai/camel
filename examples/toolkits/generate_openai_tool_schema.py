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
from camel.toolkits import FunctionTool


# Define a function which doesn't have a docstring
def get_perfect_square(n: int) -> int:
    return n**2


# Create a FunctionTool with the function
function_tool = FunctionTool(
    get_perfect_square,
    synthesize_schema=True,
)
print("\nGenerated OpenAI Tool Schema:")
print(function_tool.get_openai_tool_schema())

# Set system message for the assistant
assistant_sys_msg = "You are a helpful assistant."

# Create a ChatAgent with the tool
camel_agent = ChatAgent(
    system_message=assistant_sys_msg, tools=[function_tool]
)
camel_agent.reset()

# Define a user message
user_prompt = "What is the perfect square of 2024?"
user_msg = user_prompt

# Get response from the assistant
response = camel_agent.step(user_msg)
print("\nAssistant Response:")
print(response.msg.content)

"""
===============================================================================
Warning: No model provided. Use `gpt-4o-mini` to generate the schema.

Generated OpenAI Tool Schema:
{'type': 'function', 'function': {'name': 'get_perfect_square', 'description':
'Calculates the perfect square of a given integer.', 'parameters':
{'properties': {'n': {'type': 'integer', 'description': 'The integer to be
squared.'}}, 'required': ['n'], 'type': 'object'}}}

Assistant Response:
The perfect square of 2024 is 4,096,576.
===============================================================================
"""
