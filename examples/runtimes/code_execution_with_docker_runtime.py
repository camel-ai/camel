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
from camel.runtimes import DockerRuntime
from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import print_text_animated

# tools
toolkit = CodeExecutionToolkit(verbose=True)

# change to your own docker image
runtime = DockerRuntime("xukunliu/camel").add(
    toolkit.get_tools(),
    "camel.toolkits.CodeExecutionToolkit",
    dict(verbose=True),
    redirect_stdout=True,
)

tools = runtime.get_tools()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.GPT_4O,
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

with runtime as r:
    r.wait()
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
