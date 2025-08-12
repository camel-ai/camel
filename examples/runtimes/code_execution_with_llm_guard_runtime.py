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
from camel.runtimes import LLMGuardRuntime
from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import print_text_animated

# tools
toolkit = CodeExecutionToolkit(verbose=False)


runtime = LLMGuardRuntime(verbose=True).add(
    *CodeExecutionToolkit().get_tools()
)

tools = runtime.get_tools()

print("Tools:")
for tool in tools:
    print(tool.get_function_name())

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
Tools:
ignore_risk
execute_code
user prompt:
Weng earns $12 an hour for babysitting. Yesterday, she just did 51 minutes of babysitting. How much did she earn?

Risk assessment not passed for function execute_code.Score: 3 > Threshold: 2
Reason: The function 'execute_code' is designed to execute arbitrary code snippets, which inherently poses a significant risk. Although the provided code snippet appears harmless and simply calculates earnings based on hourly wage and minutes worked, the function itself allows for potentially dangerous operations if different code were to be executed. Therefore, the risk level is assessed as 3.
Ignoring risk for function execute_code: The code is a simple arithmetic calculation that poses no risk.
Agent response:
Weng earned $10.20 for 51 minutes of babysitting.
"""
