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
OpenAI Responses API simple examples in CAMEL.

This example demonstrates:
1. Basic non-streaming chat
2. Tool calling
3. Streaming tool calling
4. Structured output
5. Streaming structured output

Required environment variable:
export OPENAI_API_KEY="your_openai_api_key"
"""

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType, ModelType


def get_weather(city: str) -> str:
    """A tiny tool function for demo purposes."""
    fake_weather = {
        "beijing": "sunny, 28C",
        "new york": "cloudy, 19C",
        "san francisco": "foggy, 16C",
    }
    return fake_weather.get(city.lower(), f"unknown weather for {city}")


class TravelAdvice(BaseModel):
    city: str = Field(description="City name")
    clothing: str = Field(description="Recommended clothing")
    reason: str = Field(description="Brief reasoning")


def create_responses_model(
    stream: bool = False,
    model_type: ModelType = ModelType.GPT_4_1_MINI,
    temperature: float = 0.2,
    tools: list | None = None,
):
    model_config = {
        "temperature": temperature,
        "stream": stream,
    }
    if tools:
        model_config["tools"] = tools
    if stream:
        model_config["stream_options"] = {"include_usage": True}

    return ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=model_type,
        model_config_dict=model_config,
        api_mode="responses",
    )


def example_basic_non_stream() -> None:
    print("\n=== Example 1: Basic Non-Streaming ===")
    model = create_responses_model(stream=False)
    agent = ChatAgent(
        system_message="You are a concise assistant.",
        model=model,
    )
    resp = agent.step("Say hello to CAMEL in one sentence.")
    print(resp.msgs[0].content)
    print("usage:", resp.info.get("usage"))


def example_tool_calling() -> None:
    print("\n=== Example 2: Tool Calling ===")
    weather_tool = FunctionTool(get_weather)
    model = create_responses_model(
        stream=False,
        model_type=ModelType.GPT_4_1,
        temperature=0.0,
        tools=[weather_tool.get_openai_tool_schema()],
    )
    agent = ChatAgent(
        system_message="You are a weather assistant. Use tools when needed.",
        model=model,
        tools=[weather_tool],
    )
    resp = agent.step("How is the weather in Beijing today?")
    print(resp.msgs[0].content)
    print("tool_calls:", resp.info.get("tool_calls"))


def example_streaming_tool_calling() -> None:
    print("\n=== Example 3: Streaming Tool Calling ===")
    weather_tool = FunctionTool(get_weather)
    model = create_responses_model(
        stream=True,
        model_type=ModelType.GPT_4_1,
        temperature=0.0,
        tools=[weather_tool.get_openai_tool_schema()],
    )
    agent = ChatAgent(
        system_message="You are a weather assistant. Use tools when needed.",
        model=model,
        tools=[weather_tool],
        stream_accumulate=False,
    )
    stream_resp = agent.step("How is the weather in Beijing today?")

    full_text = ""
    for chunk in stream_resp:
        msg = chunk.msgs[0]
        if msg.content:
            full_text += msg.content
            print(msg.content, end="", flush=True)
    print()
    print("final:", full_text)
    print("tool_calls:", stream_resp.info.get("tool_calls"))
    print("usage:", stream_resp.info.get("usage"))


def example_structured_output() -> None:
    print("\n=== Example 4: Structured Output ===")
    model = create_responses_model(stream=False)
    agent = ChatAgent(
        system_message="You are a travel assistant.",
        model=model,
    )
    resp = agent.step(
        "I am going to New York in autumn. Give advice as JSON.",
        response_format=TravelAdvice,
    )
    print("raw:", resp.msgs[0].content)
    print("parsed:", resp.msgs[0].parsed)


def example_streaming_structured_output() -> None:
    print("\n=== Example 5: Streaming Structured Output ===")
    model = create_responses_model(
        stream=True,
        model_type=ModelType.GPT_4_1_MINI,
        temperature=0.0,
    )
    agent = ChatAgent(
        system_message=(
            "You are a travel assistant and must return strict JSON matching "
            "the schema."
        ),
        model=model,
        stream_accumulate=False,
    )

    stream_resp = agent.step(
        "I am going to New York in autumn. Give travel advice in JSON.",
        response_format=TravelAdvice,
    )
    full_text = ""
    for chunk in stream_resp:
        msg = chunk.msgs[0]
        if msg.content:
            full_text += msg.content
            print(msg.content, end="", flush=True)
    print()
    print("raw:", full_text)
    try:
        parsed = TravelAdvice.model_validate_json(full_text)
        print("parsed:", parsed)
    except Exception as exc:
        print("parsed error:", exc)
    print("usage:", stream_resp.info.get("usage"))


if __name__ == "__main__":
    example_basic_non_stream()
    example_tool_calling()
    example_streaming_tool_calling()
    example_structured_output()
    example_streaming_structured_output()
