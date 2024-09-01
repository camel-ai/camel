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

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import MATH_FUNCS, WEATHER_FUNCS
from camel.types import ModelPlatformType, ModelType


def main():
    # Set the tools for the external_tools
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

    # Set external_tools
    external_tool_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Tools calling opertor",
            content="You are a helpful assistant",
        ),
        model=model,
        tools=internal_tools,
        external_tools=external_tools,
    )

    usr_msg = BaseMessage.make_user_message(
        role_name="User",
        content="What's the weather today in Chicago?",
    )

    # This will directly call the internal tool
    response = external_tool_agent.step(usr_msg)
    # We will get the weather information here
    print(response.msg.content)

    usr_msg = BaseMessage.make_user_message(
        role_name="User",
        content="What is the sum of the temperature in Chicago and Paris?",
    )
    # This will first automatically execute the internal tool to check the
    # weather in Paris
    # Then it will request the external tool to calculate the sum
    response = external_tool_agent.step(usr_msg)
    # This should be empty
    print(response.msg.content)
    tool_call_request = response.info["tool_call_request"]
    # This will print the info of the external tool request
    print(tool_call_request)


if __name__ == "__main__":
    main()


# flake8: noqa :E501
"""
Output:
The weather in Chicago, US today is as follows:
- Temperature: 25.66°Celsius (feels like 26.34°Celsius)
- Max Temperature: 26.72°Celsius, Min Temperature: 23.93°Celsius
- Wind: 8.01 miles per hour at 71 degrees
- Visibility: 6.21 miles
- Sunrise: 2024-08-30 11:15:00+00:00
- Sunset: 2024-08-31 00:27:34+00:00

ChatCompletionMessageToolCall(id='call_hki911mimz9ro3UIWHekJmBq', function=Function(arguments='{"a":25.66,"b":18.36}', name='add'), type='function')
"""
