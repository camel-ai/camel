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
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType

# Create a streaming-capable model backend
streaming_model = ModelFactory.create(
    model_platform=ModelPlatformType.DEFAULT,
    model_type=ModelType.DEFAULT,
    model_config_dict={
        "stream": True,
        "stream_options": {"include_usage": True},
    },
)

# Initialize MathToolkit for parallel calculation demo
math_toolkit = MathToolkit()

# Create agent with math tools for parallel tool call demonstration
# stream_accumulate=False means each chunk returns only delta (incremental)
# content
agent_with_tools = ChatAgent(
    system_message="You are a helpful math assistant. When asked to perform "
    "multiple calculations, use the math tools to compute each one. "
    "Always use the tools for calculations.",
    model=streaming_model,
    tools=math_toolkit.get_tools(),
    stream_accumulate=False,  # Recommended: get delta content per chunk
)

# User message that triggers parallel tool calls
user_message = (
    "Please calculate the following three operations simultaneously:\n"
    "1. 123.45 + 678.90\n"
    "2. 100 * 3.14159\n"
    "3. 1000 / 7"
)

# Stream the response with tool calls
streaming_response = agent_with_tools.step(user_message)

for chunk_response in streaming_response:
    message = chunk_response.msgs[0]

    # Print reasoning content if available (for models that support it)
    if message.reasoning_content:
        print(message.reasoning_content, end="", flush=True)

    # Print main content (delta mode - each chunk contains only new content)
    if message.content:
        print(message.content, end="", flush=True)

# Print usage statistics
usage = streaming_response.info.get("usage", {})
print(
    f"\n\nUsage: prompt={usage.get('prompt_tokens')}, "
    f"completion={usage.get('completion_tokens')}, "
    f"total={usage.get('total_tokens')}"
)

# Print tool call records if any
tool_calls = streaming_response.info.get("tool_calls", [])
if tool_calls:
    print(f"\nTool calls made: {len(tool_calls)}")
    for i, tool_call in enumerate(tool_calls, 1):
        print(
            f"  {i}. {tool_call.tool_name}({tool_call.args}) = "
            f"{tool_call.result}"
        )
