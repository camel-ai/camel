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

from camel.agents import ChatAgent
from camel.configs import DeepSeekConfig
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType

"""
please set the below os environment:
export DEEPSEEK_API_KEY=""
"""

tools = MathToolkit().get_tools()

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
    "You are a mission-control assistant for deep-space operations. Use the "
    "provided math tools whenever the user asks for arithmetic."
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


# Round 1: the model should call math tools and then return a final answer.
user_msg = (
    "Mission control: a deep-space probe has 6 solar panels producing "
    "42.5 kWh each and 3 backup cells producing 18.75 kWh each. Use the "
    "math tools to calculate the total available energy."
)
response = camel_agent.step(user_msg)
print_step_result("Round 1", response)

# Round 2: keep the same agent memory.
user_msg = (
    "Using the previous total, reserve 15% for emergency power and subtract "
    "38.5 kWh for the orbital relay. Use the math tools to calculate the "
    "remaining science payload budget."
)
response = camel_agent.step(user_msg)
print_step_result("Round 2", response)
