# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

from colorama import Fore

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.runtimes import LLMGuardRuntime
from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import print_text_animated

# tools
toolkit = CodeExecutionToolkit(verbose=False)


runtime = LLMGuardRuntime(verbose=True).add(toolkit.get_tools())

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
execute_command
user prompt:
Weng earns $12 an hour for babysitting. Yesterday, she just did 51 minutes of babysitting. How much did she earn?

2026-01-22 12:15:24,610 - camel.runtimes.llm_guard_runtime - WARNING - Risk assessment not passed for execute_code.Score: 3 > Threshold: 2
Reason: The function executes arbitrary code snippets provided as input, which inherently poses a risk of executing harmful or malicious code. Although the given code snippet is a harmless calculation of earnings, the function itself has the potential for dangerous operations depending on the code executed.
Ignoring risk for function execute_code: The code snippet is a simple arithmetic calculation with no potential risks or harmful operations.
Agent response:
Weng earned $10.20 for babysitting for 51 minutes.
"""
