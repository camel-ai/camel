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
from camel.agents import ChatAgent
from camel.configs import AnthropicConfig
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType


def create_anthropic_model(stream: bool = False):
    r"""Create a Claude Opus 4.7 model with adaptive thinking enabled."""
    model_config = AnthropicConfig(
        max_tokens=16000,
        stream=stream,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        tool_choice={"type": "auto"},
    ).as_dict()

    return ModelFactory.create(
        model_platform=ModelPlatformType.ANTHROPIC,
        model_type=ModelType.CLAUDE_OPUS_4_7,
        model_config_dict=model_config,
    )


math_tools = MathToolkit().get_tools()

camel_agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=create_anthropic_model(),
    tools=math_tools,
)

user_msg = (
    "Use the math_multiply tool to calculate 3 * 7 * 11, then use the "
    "result to explain why the Euclid-style number 4 * (3 * 7 * 11) - 1 "
    "is congruent to 3 modulo 4."
)

response = camel_agent.step(user_msg)
answer = response.msgs[0]

print("Answer:")
print(answer.content)

if response.info and response.info.get("tool_calls"):
    print("\nTool calls:")
    print(response.info["tool_calls"])

if answer.reasoning_content:
    print("\nThinking summary:")
    print(answer.reasoning_content)


streaming_agent = ChatAgent(
    system_message="You are a helpful assistant.",
    model=create_anthropic_model(stream=True),
    tools=math_tools,
    stream_accumulate=False,
)

streaming_msg = (
    "Use the math_add tool to calculate 12345 + 67890, then briefly explain "
    "how the result was obtained."
)

print("\nStreaming answer:")
streaming_response = streaming_agent.step(streaming_msg)

for chunk_response in streaming_response:
    if not chunk_response.msgs:
        continue

    chunk = chunk_response.msgs[0]
    if chunk.reasoning_content:
        print(chunk.reasoning_content, end="", flush=True)
    if chunk.content:
        print(chunk.content, end="", flush=True)

stream_tool_calls = streaming_response.info.get("tool_calls", [])
if stream_tool_calls:
    print("\n\nStreaming tool calls:")
    print(stream_tool_calls)
