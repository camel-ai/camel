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
from camel.runtimes import DockerRuntime, TaskConfig
from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import print_text_animated

# tools
toolkit = CodeExecutionToolkit(verbose=True)

runtime = (
    DockerRuntime("xukunliu/camel")  # change to your own docker image
    .add(
        toolkit.get_tools(),
        "camel.toolkits.CodeExecutionToolkit",
        {"unsafe_mode": True, "import_white_list": ["os", "sys"]},
        True,
    )
    .add_task(
        TaskConfig(
            cmd="mkdir /home/test",
        )
    )
)

tools = runtime.get_tools()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
)


# set up agent
assistant_sys_msg = (
    "You are a personal assistant and programmer. "
    "When asked a question, "
    "write and run Python code to answer the question."
    "Your code will be executed using eval()."
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
    prompt = "List all directories in /home"
    print(Fore.YELLOW + f"user prompt:\n{prompt}\n")

    response = agent.step(prompt)
    for msg in response.msgs:
        print_text_animated(Fore.GREEN + f"Agent response:\n{msg.content}\n")


# TODO: unlock unsafe mode
# This example can not be run in the current version of CAMEL because
# the InternalPythonInterpreter does not support
# most of the built-in functions.
