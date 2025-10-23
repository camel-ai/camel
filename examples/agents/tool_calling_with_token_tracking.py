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

"""
This example demonstrates how to track token usage for each individual tool
call in a ChatAgent step.

Starting from version 0.2.79, each ToolCallingRecord includes token_usage
information, allowing you to monitor the cost of each tool call separately.
"""

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType

# Create a ChatAgent with math tools
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_5_MINI,
)

agent = ChatAgent(
    system_message="You are a helpful math assistant.",
    model=model,
    tools=MathToolkit().get_tools(),
)

# Send a message that will trigger multiple tool calls
user_message = BaseMessage.make_user_message(
    role_name="User",
    content="Calculate the result of (5 * 3) - 10",
)

print("User:", user_message.content)
print("\n" + "=" * 60 + "\n")

# Step the agent
response = agent.step(user_message)

# Display the response
print("Assistant:", response.msgs[0].content)
print("\n" + "=" * 60 + "\n")

# Check tool calls and their token usage
if response.info.get('tool_calls'):
    print("Tool Calls with Token Usage:")
    print("-" * 60)

    for i, tool_call in enumerate(response.info['tool_calls'], 1):
        print(f"\nTool Call #{i}:")
        print(f"  Tool Name: {tool_call.tool_name}")
        print(f"  Arguments: {tool_call.args}")
        print(f"  Result: {tool_call.result}")

        if tool_call.token_usage:
            print("  Token Usage:")
            prompt_tokens = tool_call.token_usage['prompt_tokens']
            completion_tokens = tool_call.token_usage['completion_tokens']
            total_tokens = tool_call.token_usage['total_tokens']
            print(f"    - Prompt Tokens: {prompt_tokens}")
            print(f"    - Completion Tokens: {completion_tokens}")
            print(f"    - Total Tokens: {total_tokens}")
        else:
            print("  Token Usage: Not available")

    print("\n" + "=" * 60 + "\n")

    # Calculate total tokens across all tool calls
    total_prompt = sum(
        tc.token_usage['prompt_tokens']
        for tc in response.info['tool_calls']
        if tc.token_usage
    )
    total_completion = sum(
        tc.token_usage['completion_tokens']
        for tc in response.info['tool_calls']
        if tc.token_usage
    )
    total_overall = sum(
        tc.token_usage['total_tokens']
        for tc in response.info['tool_calls']
        if tc.token_usage
    )

    print("Summary:")
    print(f"  Total Tool Calls: {len(response.info['tool_calls'])}")
    print(f"  Total Prompt Tokens: {total_prompt}")
    print(f"  Total Completion Tokens: {total_completion}")
    print(f"  Total Tokens (all tools): {total_overall}")
