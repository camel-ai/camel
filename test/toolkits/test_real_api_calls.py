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


import os
from typing import List

import pytest
from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import (
    MathToolkit,
    SearchToolkit,
    WeatherToolkit,
)
from camel.types import ModelPlatformType, ModelType

# Test configurations
SKIP_REAL_API_TESTS = (
    os.getenv("SKIP_REAL_API_TESTS", "true").lower() == "true"
)
requires_real_api = pytest.mark.skipif(
    SKIP_REAL_API_TESTS,
    reason="Real API tests are skipped. Set SKIP_REAL_API_TESTS=false to run.",
)


# Test schemas
class WeatherInfo(BaseModel):
    """Schema for weather information response."""

    temperature: str = Field(description="Current temperature")
    conditions: str = Field(description="Weather conditions")
    location: str = Field(description="Location for the weather data")


class CompanyInfo(BaseModel):
    """Schema for company information response."""

    name: str = Field(description="Company name")
    founded: int = Field(description="Year founded")
    industry: str = Field(description="Primary industry")


class MathResult(BaseModel):
    """Schema for math calculation results."""

    calculation: str = Field(description="The calculation performed")
    result: str = Field(description="The numerical result")
    steps: List[str] = Field(description="Steps taken to solve")


@pytest.fixture
def chat_agent():
    """Create a ChatAgent with tools for testing."""
    tools_list = [
        *SearchToolkit().get_tools(),
        *MathToolkit().get_tools(),
        *WeatherToolkit().get_tools(),
    ]

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
        model_config_dict=ChatGPTConfig(temperature=0.0).as_dict(),
    )

    return ChatAgent(
        system_message="You are a helpful assistant for testing.",
        model=model,
        tools=tools_list,
    )


@requires_real_api
class TestRealAPICallsAndStructuredOutput:
    """Test suite for real API calls and structured outputs."""

    def test_search_with_structured_output(self, chat_agent):
        """Test search tool with structured company information output."""
        query = (
            "What is OpenAI? When was it founded and what industry is it in?"
        )
        response = chat_agent.step(query, response_format=CompanyInfo)
        result = eval(response.msgs[0].content)

        assert isinstance(result, dict)
        assert all(key in result for key in ["name", "founded", "industry"])
        assert isinstance(result["name"], str)
        assert isinstance(result["founded"], int)
        assert isinstance(result["industry"], str)

    def test_weather_with_structured_output(self, chat_agent):
        """Test weather toolkit with structured output."""
        query = "What's the current weather in New York?"
        response = chat_agent.step(query, response_format=WeatherInfo)
        result = eval(response.msgs[0].content)

        assert isinstance(result, dict)
        assert all(
            key in result for key in ["temperature", "conditions", "location"]
        )
        assert isinstance(result["temperature"], str)
        assert isinstance(result["conditions"], str)
        assert isinstance(result["location"], str)

    def test_math_with_structured_steps(self, chat_agent):
        """Test math toolkit with structured output showing steps."""
        query = "Calculate the square root of 144 and show your steps"
        response = chat_agent.step(query, response_format=MathResult)
        result = eval(response.msgs[0].content)

        assert isinstance(result, dict)
        assert all(key in result for key in ["calculation", "result", "steps"])
        assert isinstance(result["calculation"], str)
        assert isinstance(result["result"], str)
        assert isinstance(result["steps"], list)
        assert float(result["result"]) == 12.0
        assert len(result["steps"]) > 0
