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
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import print_text_animated

# tools
toolkit = CodeExecutionToolkit(verbose=True)
tools = toolkit.get_tools()

# set up LLM model
assistant_model_config = ChatGPTConfig(
    temperature=0.0,
)

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict=assistant_model_config.as_dict(),
)


# set up agent
assistant_sys_msg = BaseMessage.make_assistant_message(
    role_name="Teacher",
    content=(
        "You are a personal math tutor and programmer. "
        "When asked a math question, "
        "write and run Python code to answer the question."
    ),
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
user_msg = BaseMessage.make_user_message(role_name="User", content=prompt)
print(Fore.YELLOW + f"user prompt:\n{prompt}\n")

response = agent.step(user_msg)
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

agent_with_e2b = ChatAgent(
    assistant_sys_msg,
    model,
    tools=CodeExecutionToolkit(verbose=True, sandbox="e2b").get_tools(),
)
agent_with_e2b.reset()

print(Fore.YELLOW + f"user prompt:\n{prompt}\n")

response_with_e2b = agent_with_e2b.step(user_msg)
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


time_consuming_code = '''
import time
time.sleep(100)
'''

code_execution_tool_kit = CodeExecutionToolkit(
    sandbox='internal_python', import_white_list=['sympy'], unsafe_mode=True
)

result = code_execution_tool_kit.execute_code_with_timeout(
    time_consuming_code, timeout=5
)

print(result)
"""
===============================================================================
Timed out, execution terminated.
===============================================================================
"""
