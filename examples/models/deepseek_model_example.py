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

import os

from camel.agents import ChatAgent
from camel.configs import DeepSeekConfig
from camel.models import ModelFactory
from camel.toolkits import TerminalToolkit
from camel.types import ModelPlatformType, ModelType

"""
please set the below os environment:
export DEEPSEEK_API_KEY=""
"""

base_dir = os.path.dirname(os.path.abspath(__file__))
workspace_dir = os.path.join(
    os.path.dirname(os.path.dirname(base_dir)), "workspace"
)

tools = TerminalToolkit(working_directory=workspace_dir).get_tools()

model = ModelFactory.create(
    model_platform=ModelPlatformType.DEEPSEEK,
    model_type=ModelType.DEEPSEEK_V4_PRO,
    model_config_dict=DeepSeekConfig(
        reasoning_effort="high",
        thinking={"type": "enabled"},
    ).as_dict(),
)

# Define system message
sys_msg = (
    "You are a mission-control system operator. Use the provided terminal "
    "tools for filesystem and log tasks inside the workspace."
)

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model, tools=tools)


def print_step_result(step_name: str, response) -> None:
    r"""Print tool calls and final message for one agent step."""
    print(f"\n{step_name}")
    print("=" * len(step_name))
    print("Tool calls:")
    print(str(response.info["tool_calls"])[:1000])

    if response.msgs:
        message = response.msgs[0]
        if message.reasoning_content:
            print("\nReasoning content:")
            print(message.reasoning_content[:1000])
        print("\nFinal answer:")
        print(message.content)


# Round 1: the model should call terminal tools and return a final answer.
user_msg = (
    f"Create a 'mission_control' directory in '{workspace_dir}', write "
    "'probe=voyager-x status=nominal battery=84' into telemetry.txt inside "
    "that directory, then list the directory contents. Use the terminal "
    "tools."
)
response = camel_agent.step(user_msg)
print_step_result("Round 1", response)

# Round 2: keep the same agent memory.
user_msg = (
    "Using the directory you just created, append 'relay=online' to "
    "telemetry.txt and show the full file content. Use the terminal tools."
)
response = camel_agent.step(user_msg)
print_step_result("Round 2", response)
