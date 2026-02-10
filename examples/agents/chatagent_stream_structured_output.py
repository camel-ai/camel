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
Example: Streaming + Tool Calls + Structured Output

Demonstrates using ChatAgent in streaming mode with both tools and
response_format (structured output) simultaneously, in both sync and async.
"""

import asyncio

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import MathToolkit
from camel.types import ModelPlatformType, ModelType


class Result(BaseModel):
    sum_result: str = Field(description="Result of the addition")
    product_result: str = Field(description="Result of the multiplication")
    division_result: str = Field(description="Result of the division")
    capital_result: str = Field(description="Result of the capital search")


USER_MESSAGE = (
    "Calculate: 1) 123.45 + 678.90  2) 100 * 3.14159  3) 1000 / 7, "
    "also search what is the capital of Germany"
)


def create_agent() -> ChatAgent:
    streaming_model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
        model_config_dict={
            "stream": True,
            "stream_options": {"include_usage": True},
        },
    )
    return ChatAgent(
        system_message="You are a helpful assistant.",
        model=streaming_model,
        tools=MathToolkit().get_tools(),
        stream_accumulate=False,  # Delta mode
    )


def sync_example():
    """Sync streaming with tools + structured output."""
    print("=== Sync Example ===")
    agent = create_agent()

    streaming_response = agent.step(USER_MESSAGE, response_format=Result)

    content_parts = []
    for chunk in streaming_response:
        if chunk.msgs[0].content:
            content_parts.append(chunk.msgs[0].content)
            print(chunk.msgs[0].content, end="", flush=True)

    print()

    # Print tool call records
    tool_calls = streaming_response.info.get("tool_calls", [])
    if tool_calls:
        print(f"\nTool calls made: {len(tool_calls)}")
        for i, tc in enumerate(tool_calls, 1):
            print(f"  {i}. {tc.tool_name}({tc.args}) = {tc.result}")

    # Check parsed output
    final_msg = streaming_response.msgs[0]
    if final_msg.parsed:
        print(f"\nParsed result: {final_msg.parsed}")


async def async_example():
    """Async streaming with tools + structured output."""
    print("\n=== Async Example ===")
    agent = create_agent()

    content_parts = []
    async for chunk in await agent.astep(USER_MESSAGE, response_format=Result):
        if chunk.msgs[0].content:
            content_parts.append(chunk.msgs[0].content)
            print(chunk.msgs[0].content, end="", flush=True)

    print()
    full_content = "".join(content_parts)
    print(f"\nFull content: {full_content}")


if __name__ == "__main__":
    sync_example()
    asyncio.run(async_example())
