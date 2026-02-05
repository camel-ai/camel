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
E2E tests for ChatAgent with tools:
1. Normal (non-streaming) with tools
2. Structured output with tools
3. Streaming with tools
4. Streaming with structured output and tools #TODO
"""

import pytest
from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import MathToolkit, SearchToolkit
from camel.types import ModelPlatformType, ModelType


@pytest.mark.model_backend
def test_normal_with_tools():
    """Normal (non-streaming) example with parallel tool calls."""
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    agent = ChatAgent(
        system_message="You are a helpful assistant. ",
        model=model,
        tools=[*MathToolkit().get_tools(), SearchToolkit().search_wiki],
    )

    response = agent.step(
        "Calculate: 1) 123.45 + 678.90  2) 100 * 3.14159  3) 1000 / 7, "
        "also search what is the capital of Japan"
    )

    # Verify tool calls were made and results are correct
    tool_calls = response.info.get("tool_calls", [])
    assert len(tool_calls) >= 3, "Should have at least 3 tool calls"

    content = response.msgs[0].content
    assert "802" in content
    assert "314" in content
    assert "142" in content


@pytest.mark.model_backend
def test_structured_output_with_tools():
    """Structured output example with tools."""

    class Result(BaseModel):
        sum_result: str = Field(description="Result of the addition")
        product_result: str = Field(description="Result of the multiplication")
        division_result: str = Field(description="Result of the division")
        capital_result: str = Field(description="Result of the capital search")

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    agent = ChatAgent(
        system_message="You are a helpful assistant. ",
        model=model,
        tools=MathToolkit().get_tools(),
    )

    response = agent.step(
        "Calculate: 1) 123.45 + 678.90  2) 100 * 3.14159  3) 1000 / 7, "
        "also search what is the capital of China",
        response_format=Result,
    )

    # Verify structured response (allow for rounding)
    parsed = response.msgs[0].parsed
    assert "802" in parsed.sum_result
    assert "314" in parsed.product_result
    assert "142" in parsed.division_result


@pytest.mark.model_backend
def test_streaming_with_tools():
    """Streaming example with parallel tool calls."""
    streaming_model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
        model_config_dict={
            "stream": True,
            "stream_options": {"include_usage": True},
        },
    )

    agent = ChatAgent(
        system_message="You are a helpful assistant. ",
        model=streaming_model,
        tools=[*MathToolkit().get_tools(), SearchToolkit().search_wiki],
        stream_accumulate=True,  # Accumulate content
    )

    streaming_response = agent.step(
        "Calculate: 1) 123.45 + 678.90  2) 100 * 3.14159  3) 1000 / 7, "
        "also search what is the capital of France"
    )

    for _ in streaming_response:
        pass  # Consume the stream

    # Verify tool calls were made and results are correct
    tool_calls = streaming_response.info.get("tool_calls", [])
    assert len(tool_calls) >= 3, "Should have at least 3 tool calls"

    content = streaming_response.msgs[0].content
    assert "802" in content
    assert "314" in content
    assert "142" in content
