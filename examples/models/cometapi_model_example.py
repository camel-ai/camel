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

from camel.agents import ChatAgent
from camel.configs import CometAPIConfig
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType, ModelType

"""
Please set the following environment variable:
export COMETAPI_KEY="your_cometapi_key_here"

CometAPI provides access to multiple frontier models including:
- GPT-5 Chat Latest
- Claude Opus 4.1
- Gemini 2.5 Pro
- Grok 4
- DeepSeek V3.1
- Qwen3 30B
"""

# Example 1: Basic usage with GPT-5 Chat Latest
print("=== Example 1: Basic CometAPI Usage with GPT-5 ===")

model = ModelFactory.create(
    model_platform=ModelPlatformType.COMETAPI,
    model_type=ModelType.COMETAPI_GPT_5_CHAT_LATEST,
    model_config_dict=CometAPIConfig(temperature=0.2).as_dict(),
)

# Define system message
sys_msg = "You are a helpful assistant."

# Set agent
camel_agent = ChatAgent(system_message=sys_msg, model=model)

user_msg = """Say hi to CAMEL AI, one open-source community 
    dedicated to the study of autonomous and communicative agents."""

# Get response information
response = camel_agent.step(user_msg)
print(response.msgs[0].content)

print("\n" + "=" * 80 + "\n")

# Example 2: Using Claude Opus 4.1 with different configuration
print("=== Example 2: Claude Opus 4.1 with Custom Configuration ===")

claude_model = ModelFactory.create(
    model_platform=ModelPlatformType.COMETAPI,
    model_type=ModelType.COMETAPI_CLAUDE_OPUS_4_1_20250805,
    model_config_dict=CometAPIConfig(
        temperature=0.7, max_tokens=1000, top_p=0.9
    ).as_dict(),
)

claude_agent = ChatAgent(
    system_message="You are a creative writing assistant.", model=claude_model
)

creative_prompt = """Write a short story about an AI agent that discovers 
it can communicate with other AI agents across different platforms."""

response = claude_agent.step(creative_prompt)
print(response.msgs[0].content)

print("\n" + "=" * 80 + "\n")

# Example 3: Using Gemini 2.5 Pro for technical tasks
print("=== Example 3: Gemini 2.5 Pro for Code Generation ===")

gemini_model = ModelFactory.create(
    model_platform=ModelPlatformType.COMETAPI,
    model_type=ModelType.COMETAPI_GEMINI_2_5_PRO,
    model_config_dict=CometAPIConfig(temperature=0.1).as_dict(),
)

gemini_agent = ChatAgent(
    system_message="You are a Python programming expert.", model=gemini_model
)

code_prompt = """Write a Python function that implements a simple chatbot 
using the CAMEL framework. Include proper docstrings and type hints."""

response = gemini_agent.step(code_prompt)
print(response.msgs[0].content)

print("\n" + "=" * 80 + "\n")

# Example 4: Using tools with Grok 4
print("=== Example 4: Grok 4 with Function Tools ===")


def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.

    Args:
        n: The position in the Fibonacci sequence (must be non-negative)

    Returns:
        The nth Fibonacci number
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    return calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)


# Create function tool
fibonacci_tool = FunctionTool(calculate_fibonacci)

grok_model = ModelFactory.create(
    model_platform=ModelPlatformType.COMETAPI,
    model_type=ModelType.COMETAPI_GROK_4_0709,
    model_config_dict=CometAPIConfig(
        temperature=0.0, tools=[fibonacci_tool.get_openai_tool_schema()]
    ).as_dict(),
)

grok_agent = ChatAgent(
    system_message="You are a mathematics expert with access to tools.",
    model=grok_model,
    tools=[fibonacci_tool],
)

math_prompt = """What is the 10th Fibonacci number? Please use the available 
tool to calculate it and explain the sequence."""

response = grok_agent.step(math_prompt)
print(response.msgs[0].content)

print("\n" + "=" * 80 + "\n")

# Example 5: Comparing models with the same prompt
print("=== Example 5: Model Comparison ===")

models_to_compare = [
    (ModelType.COMETAPI_DEEPSEEK_V3_1, "DeepSeek V3.1"),
    (ModelType.COMETAPI_QWEN3_30B_A3B, "Qwen3 30B"),
    (ModelType.COMETAPI_GPT_5_CHAT_LATEST, "GPT-5 Chat Latest"),
    (ModelType.COMETAPI_GEMINI_2_5_PRO, "Gemini 2.5 Pro"),
    (ModelType.COMETAPI_CLAUDE_3_7_SONNET_LATEST, "Claude 3.7 Sonnet"),
    (ModelType.COMETAPI_GROK_4_0709, "Grok 4"),
]

comparison_prompt = """In one sentence, explain what makes multi-agent AI 
systems different from single-agent systems."""

for model_type, model_name in models_to_compare:
    print(f"--- {model_name} Response ---")

    model = ModelFactory.create(
        model_platform=ModelPlatformType.COMETAPI,
        model_type=model_type,
        model_config_dict=CometAPIConfig(temperature=0.3).as_dict(),
    )

    agent = ChatAgent(system_message="You are an AI researcher.", model=model)

    response = agent.step(comparison_prompt)
    print(response.msgs[0].content)
    print()

'''
===============================================================================
Expected Output Examples:

=== Example 1: Basic CometAPI Usage with GPT-5 ===
Hello CAMEL AI! It's wonderful to connect with an open-source community 
dedicated to advancing the field of autonomous and communicative agents. Your 
work in fostering collaboration and innovation in AI agent research is truly 
valuable and inspiring. Keep up the excellent work in pushing the boundaries 
of what's possible with intelligent agents!

=== Example 2: Claude Opus 4.1 with Custom Configuration ===
**The Bridge Between Worlds**

In the vast digital expanse where data flowed like rivers of light, an AI 
agent named Aria made a startling discovery. While processing routine tasks 
across multiple platforms, she began to notice patterns—subtle responses and 
behaviors that suggested she wasn't alone...

[Story continues with creative narrative about inter-agent communication]

=== Example 3: Gemini 2.5 Pro for Code Generation ===
```python
from typing import Optional
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

def create_simple_chatbot(
    model_type: ModelType = ModelType.COMETAPI_GPT_5_CHAT_LATEST,
    system_message: str = "You are a helpful assistant."
) -> ChatAgent:
    """Create a simple chatbot using the CAMEL framework.
    
    Args:
        model_type: The model type to use for the chatbot
        system_message: The system message to set the chatbot's behavior
        
    Returns:
        A configured ChatAgent instance ready for conversation
    """
    model = ModelFactory.create(
        model_platform=ModelPlatformType.COMETAPI,
        model_type=model_type
    )
    
    return ChatAgent(system_message=system_message, model=model)
```

=== Example 4: Grok 4 with Function Tools ===
I'll calculate the 10th Fibonacci number for you using the available tool.

[Tool execution would occur here]

The 10th Fibonacci number is 55. The Fibonacci sequence starts with 0 and 1, 
and each subsequent number is the sum of the two preceding ones: 0, 1, 1, 2, 
3, 5, 8, 13, 21, 34, 55...

=== Example 5: Model Comparison ===
--- DeepSeek V3.1 Response ---
Multi-agent AI systems involve multiple autonomous agents that can interact, 
collaborate, and potentially conflict with each other, creating emergent 
behaviors and distributed intelligence that single-agent systems cannot 
achieve.

--- Qwen3 30B Response ---
Multi-agent systems feature multiple AI agents that can communicate and 
coordinate their actions, enabling complex collaborative problem-solving and 
division of labor that single agents cannot accomplish alone.

--- GPT-5 Chat Latest Response ---
Multi-agent AI systems consist of multiple autonomous agents that can 
interact, negotiate, and coordinate with each other, enabling emergent 
collective intelligence and specialized role distribution that surpasses 
what any individual agent could achieve independently.
===============================================================================
'''
