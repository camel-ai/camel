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

from colorama import Fore

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import print_text_animated

# tools
toolkit = CodeExecutionToolkit(verbose=True)
tools = toolkit.get_tools()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)


# set up agent
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


# set up agent

prompt = (
    "Weng earns $12 an hour for babysitting. "
    "Yesterday, she just did 51 minutes of babysitting. How much did she earn?"
)
print(Fore.YELLOW + f"user prompt:\n{prompt}\n")

response = agent.step(prompt)
for msg in response.msgs:
    print_text_animated(Fore.GREEN + f"Agent response:\n{msg.content}\n")

# ruff: noqa: E501
"""
===============================================================================
user prompt:
Weng earns $12 an hour for babysitting. Yesterday, she just did 51 minutes of babysitting. How much did she earn?

Executed the code below:
```py
hourly_rate = 12
minutes_worked = 51
hourly_earnings = hourly_rate / 60 * minutes_worked
hourly_earnings
```
> Executed Results:
10.200000000000001
Agent response:
Weng earned $10.20 for babysitting for 51 minutes at a rate of $12 per hour.
===============================================================================
"""

# Example 3: Using E2B Code Interpreter (Cloud-based)
# Note: Requires E2B_API_KEY environment variable to be set
agent_with_e2b = ChatAgent(
    assistant_sys_msg,
    model,
    tools=CodeExecutionToolkit(verbose=True, sandbox="e2b").get_tools(),
)

# Configure E2B with environment variables:
# export E2B_API_KEY="your_api_key_here"
# export E2B_DOMAIN="your-custom-e2b-provider.com"  # Optional, for custom E2B-compatible providers

print(Fore.YELLOW + f"user prompt:\n{prompt}\n")

response_with_e2b = agent_with_e2b.step(prompt)
for msg in response_with_e2b.msgs:
    print_text_animated(Fore.GREEN + f"Agent response:\n{msg.content}\n")

# ruff: noqa: E501
"""
===============================================================================
user prompt:
Weng earns $12 an hour for babysitting. Yesterday, she just did 51 minutes of babysitting. How much did she earn?

Executed the code below:
```py
hourly_wage = 12
minutes_worked = 51
# Convert minutes to hours
hours_worked = minutes_worked / 60
# Calculate earnings
earnings = hourly_wage * hours_worked
earnings
```
> Executed Results:
10.2
Agent response:
Weng earned $10.20 for 51 minutes of babysitting.
===============================================================================
"""
