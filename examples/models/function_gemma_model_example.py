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

"""
FunctionGemma Model Example

This example demonstrates how to use the FunctionGemma model with CAMEL.
FunctionGemma is a specialized Gemma model fine-tuned for function calling.

Prerequisites:
1. Install Ollama: https://ollama.ai
2. Pull the FunctionGemma model: ollama pull functiongemma
3. Ensure Ollama server is running on http://localhost:11434
"""

from camel.agents import ChatAgent
from camel.configs import FunctionGemmaConfig
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType


# define a simple tool
def add(a: int, b: int) -> int:
    """Add two numbers together.

    Args:
        a: The first number.
        b: The second number.

    Returns:
        The sum of a and b.
    """
    return a + b


# create the tool
add_tool = FunctionTool(add)

# create the FunctionGemma model
model = ModelFactory.create(
    model_platform=ModelPlatformType.FUNCTION_GEMMA,
    model_type="functiongemma",
    url="http://localhost:11434",
    model_config_dict=FunctionGemmaConfig(num_predict=256).as_dict(),
)

# create a chat agent with the tool
agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=model,
    tools=[add_tool],
)

# ask the agent to use the tool
response = agent.step("What is 15 + 27?")
print(response.msgs[0].content)

"""
===============================================================================
The sum of 15 + 27 is 42.
===============================================================================
"""
