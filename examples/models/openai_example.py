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
"""OpenAI model example: multi-turn conversation with tool use and structured
output."""

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType


class Summary(BaseModel):
    total: float = Field(description="The calculated total")
    explanation: str = Field(description="Brief explanation")


model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
)

agent = ChatAgent(model=model, tools=MathToolkit().get_tools())

# Turn 1: Basic chat
response = agent.step("Hi, I need help with some calculations.")
print(response.msgs[0].content)

# Turn 2: Tool use
response = agent.step("What is 123.45 + 678.90?")
print(response.msgs[0].content)

# Turn 3: Follow-up with context
response = agent.step("Now multiply that result by 2.")
print(response.msgs[0].content)

# Turn 4: Structured output
response = agent.step(
    "Summarize all calculations we did.", response_format=Summary
)
print(response.msgs[0].content)
