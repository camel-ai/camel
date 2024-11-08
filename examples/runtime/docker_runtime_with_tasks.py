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

from colorama import Fore

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits.code_execution import CodeExecutionToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import print_text_animated
from camel.runtime import DockerRuntime

# tools
toolkit = CodeExecutionToolkit(verbose=True)

runtime = (
    DockerRuntime("xukunliu/camel")
    .add(
        toolkit.get_tools(),
        "camel.toolkits.CodeExecutionToolkit(unsafe_mode=True, import_white_list=['os', 'sys'])",
        True,
    )
    .add_task("mkdir /home/test")
)

tools = runtime.get_tools()

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
        "You are a personal assistant and programmer. "
        "When asked a question, "
        "write and run Python code to answer the question."
        "Your code will be executed using eval()."
    ),
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
        "List all directories in /home"
    )
    user_msg = BaseMessage.make_user_message(role_name="User", content=prompt)
    print(Fore.YELLOW + f"user prompt:\n{prompt}\n")

    response = agent.step(user_msg)
    for msg in response.msgs:
        print_text_animated(Fore.GREEN + f"Agent response:\n{msg.content}\n")


# TODO: unlock unsafe mode
# This example can not be run in the current version of CAMEL because
# the InternalPythonInterpreter does not support most of the built-in functions.
