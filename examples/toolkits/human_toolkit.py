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
from camel.toolkits import HumanToolkit
from camel.types import ModelPlatformType, ModelType

human_toolkit = HumanToolkit()

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=ChatGPTConfig(
        temperature=0.0,
    ).as_dict(),
)

# Example 1: Test Agent with the human toolkit (ask_human_via_console)
print("\nExample 1: Using ask_human_via_console through an agent")
agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=model,
    tools=[*human_toolkit.get_tools()],
)

response = agent.step(
    "Test me on the capital of some country, and comment on my answer."
)

print(response.msgs[0].content)

"""
==========================================================================
What is the capital of France?
Your reply: Paris

That's correct! Paris is indeed the capital of France. Would you like to try
another one?
Your reply: yes

What is the capital of Japan?
Your reply: Tokyo

That's correct! Tokyo is the capital of Japan. Would you like to continue with
another question?
Your reply: no
==========================================================================
"""

# Example 2: Agent using send_message_to_user through tools
print("\nExample 2: Agent using send_message_to_user through tools")
agent_with_message = ChatAgent(
    system_message="You are an assistant that can send messages to the user.",
    model=model,
    tools=[*human_toolkit.get_tools()],
)

response = agent_with_message.step(
    "Send me a notification about an upcoming meeting."
)

print(response.msgs[0].content)

"""
==========================================================================
Agent Message:
🔔 Reminder: You have an upcoming meeting scheduled. Please check your 
calendar for details!

I've sent you a notification about your upcoming meeting. Please check your 
calendar for details!
==========================================================================
"""

# Example 3: Agent using provide_intermediate_information through tools
print("\nExample 3: Agent using provide_intermediate_information")
agent_with_info = ChatAgent(
    system_message="You are an assistant that can send messages to users.",
    model=model,
    tools=[*human_toolkit.get_tools()],
)

response = agent_with_info.step(
    "solve this math problem derivative of x ^ 3, "
    "show me your intermediate workings also"
)

print(response.msgs[0].content)

"""
==========================================================================
Intermediate Information from Agent
Context: To find the derivative of the function f(x) = x^3, we will apply
the power rule of differentiation, which states that if f(x) = x^n, then 
f'(x) = n * x^(n-1). In this case, n = 3.


Intermediate Information from Agent
Context: Using the power rule:
1. Identify n: Here, n = 3.
2. Apply the formula: f'(x) = 3 * x^(3-1).
3. Simplify: f'(x) = 3 * x^2.


Agent Message:
The derivative of x^3 is f'(x) = 3x^2.
The derivative of \( x^3 \) is \( f'(x) = 3x^2 \). 

Heres the breakdown of the steps:

1. **Identify the power**: In this case, the exponent \( n = 3 \).
2. **Apply the power rule**: The power rule states that if \( f(x) = x^n \),
    then the derivative \( f'(x) = n \cdot x^{n-1} \).
3. **Calculate the derivative**: 
   \[
   f'(x) = 3 \cdot x^{3-1} = 3 \cdot x^2
   \]

Thus, the final result is \( f'(x) = 3x^2 \).
==========================================================================
"""
