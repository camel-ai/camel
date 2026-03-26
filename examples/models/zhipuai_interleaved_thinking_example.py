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
from camel.configs import ZhipuAIConfig
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType, ModelType

"""
Please set the following environment variable:
export ZHIPUAI_API_KEY="your_zhipuai_api_key"

This example demonstrates interleaved thinking with tool calls.
Note: stream must be disabled for interleaved thinking to work.
"""


def calculate_total(
    subtotal: float, discount_rate: float, tax_rate: float, shipping: float
) -> float:
    """Calculate final total after discount, tax, and shipping."""
    discounted = subtotal * (1.0 - discount_rate)
    taxed = discounted * (1.0 + tax_rate)
    return taxed + shipping


calculate_total_tool = FunctionTool(calculate_total)

model = ModelFactory.create(
    model_platform=ModelPlatformType.ZHIPUAI,
    model_type=ModelType.GLM_4_PLUS,
    model_config_dict=ZhipuAIConfig(
        temperature=0.2,
        interleaved_thinking=True,
        tool_choice="required",
    ).as_dict(),
)

agent = ChatAgent(
    system_message=(
        "You are a helpful assistant. Always use the calculate_total tool "
        "for price calculations."
    ),
    model=model,
    tools=[calculate_total_tool],
)

response = agent.step(
    "Order A: subtotal $120, discount 15%, tax 8%, shipping $6. "
    "Use the tool to compute the final total and briefly explain."
)
print(response.msgs[0].content)

response = agent.step(
    "Order B: subtotal $75, same discount and tax rates as before, "
    "shipping $10. Use the tool to compute the final total."
)
print(response.msgs[0].content)
