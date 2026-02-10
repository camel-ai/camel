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

import os
from typing import Optional

import pytest
from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType, ModelType

pytestmark = pytest.mark.model_backend

HAS_OPENAI_API_KEY = bool(os.getenv("OPENAI_API_KEY"))


def get_weather(city: str) -> str:
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


class WeatherTravelAdvice(BaseModel):
    city: str = Field(description="City name")
    weather: str = Field(description="Weather summary from tool result")
    clothing: str = Field(description="Recommended clothing")
    reason: str = Field(description="Brief reasoning")


def _create_responses_model(
    *,
    stream: bool = False,
    temperature: float = 0.0,
    tools: Optional[list] = None,
):
    model_config = {
        "temperature": temperature,
        "stream": stream,
    }
    if stream:
        model_config["stream_options"] = {"include_usage": True}
    if tools:
        model_config["tools"] = tools

    return ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4_1_MINI,
        model_config_dict=model_config,
        api_mode="responses",
    )


@pytest.mark.skipif(
    not HAS_OPENAI_API_KEY,
    reason="OPENAI_API_KEY is required for Responses API E2E tests",
)
def test_responses_tool_calling_non_stream():
    weather_tool = FunctionTool(get_weather)
    model = _create_responses_model(
        stream=False,
        temperature=0.0,
        tools=[weather_tool.get_openai_tool_schema()],
    )
    agent = ChatAgent(
        system_message="You are a weather assistant. Must use tool.",
        model=model,
        tools=[weather_tool],
    )
    resp = agent.step("How is the weather in Beijing today?")
    assert resp.info.get("tool_calls")
    assert resp.msgs and resp.msgs[0].content


@pytest.mark.skipif(
    not HAS_OPENAI_API_KEY,
    reason="OPENAI_API_KEY is required for Responses API E2E tests",
)
def test_responses_structured_output_non_stream():
    model = _create_responses_model(stream=False, temperature=0.0)
    agent = ChatAgent(
        system_message="Return strict JSON matching schema.",
        model=model,
    )
    resp = agent.step(
        "I am going to New York in autumn. Give travel advice as JSON.",
        response_format=TravelAdvice,
    )
    parsed = resp.msgs[0].parsed
    assert parsed is not None
    assert isinstance(parsed, TravelAdvice)


@pytest.mark.skipif(
    not HAS_OPENAI_API_KEY,
    reason="OPENAI_API_KEY is required for Responses API E2E tests",
)
def test_responses_tool_calling_and_structured_output_non_stream():
    weather_tool = FunctionTool(get_weather)
    model = _create_responses_model(
        stream=False,
        temperature=0.0,
        tools=[weather_tool.get_openai_tool_schema()],
    )
    agent = ChatAgent(
        system_message=(
            "You are a travel assistant. Must call weather tool and return "
            "strict JSON matching schema."
        ),
        model=model,
        tools=[weather_tool],
    )
    resp = agent.step(
        "I am visiting Beijing tomorrow. Use tool for weather and return "
        "structured travel advice JSON.",
        response_format=WeatherTravelAdvice,
    )
    parsed = resp.msgs[0].parsed
    assert parsed is not None
    assert isinstance(parsed, WeatherTravelAdvice)
    assert resp.info.get("tool_calls")


@pytest.mark.skipif(
    not HAS_OPENAI_API_KEY,
    reason="OPENAI_API_KEY is required for Responses API E2E tests",
)
def test_responses_tool_calling_stream():
    weather_tool = FunctionTool(get_weather)
    model = _create_responses_model(
        stream=True,
        temperature=0.0,
        tools=[weather_tool.get_openai_tool_schema()],
    )
    agent = ChatAgent(
        system_message="You are a weather assistant. Must use tool.",
        model=model,
        tools=[weather_tool],
        stream_accumulate=False,
    )

    stream_resp = agent.step("How is the weather in Beijing today?")
    final_text = ""
    for chunk in stream_resp:
        if chunk.msgs and chunk.msgs[0].content:
            final_text += chunk.msgs[0].content

    assert stream_resp.info.get("tool_calls")
    assert isinstance(final_text, str)


@pytest.mark.skipif(
    not HAS_OPENAI_API_KEY,
    reason="OPENAI_API_KEY is required for Responses API E2E tests",
)
def test_responses_structured_output_stream():
    model = _create_responses_model(stream=True, temperature=0.0)
    agent = ChatAgent(
        system_message="Return strict JSON matching schema.",
        model=model,
        stream_accumulate=False,
    )

    stream_resp = agent.step(
        "I am going to New York in autumn. Give travel advice as JSON.",
        response_format=TravelAdvice,
    )
    full_text = ""
    for chunk in stream_resp:
        if chunk.msgs and chunk.msgs[0].content:
            full_text += chunk.msgs[0].content

    parsed = TravelAdvice.model_validate_json(full_text)
    assert isinstance(parsed, TravelAdvice)
