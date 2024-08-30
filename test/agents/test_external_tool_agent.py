# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import ast

import pytest
from pydantic import BaseModel, Field

from camel.agents import ExternalToolAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import MATH_FUNCS, WEATHER_FUNCS
from camel.types import ModelPlatformType, ModelType


@pytest.fixture
def external_tool_agent():
    internal_tools = [*WEATHER_FUNCS]
    external_tools = [*MATH_FUNCS]
    tool_list = internal_tools + external_tools

    model_config_dict = ChatGPTConfig(
        tools=tool_list,
        temperature=0.0,
    ).as_dict()

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_3_5_TURBO,
        model_config_dict=model_config_dict,
    )

    external_tool_agent = ExternalToolAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Tools calling opertor",
            content="You are a helpful assistant",
        ),
        model=model,
        external_tools=external_tools,
        internal_tools=internal_tools,
    )

    return external_tool_agent


@pytest.mark.model_backend
def test_internal_tool_with_structured_output(external_tool_agent):
    class TemperatureResponse(BaseModel):
        f_temp: str = Field(description="temperature in Fahrenheit")
        c_temp: str = Field(description="temperature in Celsius")

    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content="Tell me the temperature in Chicago in both Celsius and "
        "Fehrenheit.",
    )

    response = external_tool_agent.step(
        user_msg, output_schema=TemperatureResponse
    )

    response_content_dict = ast.literal_eval(response.msg.content)
    joke_response_keys = set(
        TemperatureResponse.model_json_schema()["properties"].keys()
    )

    response_content_keys = set(response_content_dict.keys())

    assert joke_response_keys.issubset(
        response_content_keys
    ), f"Missing keys: {joke_response_keys - response_content_keys}"

    for key in joke_response_keys:
        assert (
            key in response_content_dict
        ), f"Key {key} not found in response content"


@pytest.mark.model_backend
def test_external_tool(external_tool_agent):
    usr_msg = BaseMessage.make_user_message(
        role_name="User",
        content="What's the sum of 8 and 9?",
    )

    response = external_tool_agent.step(usr_msg)
    assert not response.msg.content

    tool_call_request = response.info["tool_call_request"]
    assert tool_call_request.function.name == "add"


@pytest.mark.model_backend
def test_mixed_tool(external_tool_agent):
    usr_msg = BaseMessage.make_user_message(
        role_name="User",
        content="What's the sum of the temperature in Chicago and Paris?",
    )

    response = external_tool_agent.step(usr_msg)
    assert not response.msg.content

    tool_call_request = response.info["tool_call_request"]
    assert tool_call_request.function.name == "add"
