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
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import MathToolkit, SearchToolkit
from camel.types import ModelPlatformType, ModelType


def main():
    # Set the tools for the external_tools
    internal_tools = SearchToolkit().get_tools()
    external_tools = MathToolkit().get_tools()
    tool_list = internal_tools + external_tools

    model_config_dict = ChatGPTConfig(
        tools=tool_list,
    ).as_dict()

    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
        model_config_dict=model_config_dict,
    )

    # Set external_tools
    external_tool_agent = ChatAgent(
        system_message="You are a helpful assistant",
        model=model,
        tools=internal_tools,
        external_tools=external_tools,
    )

    # This will directly run the internal tool
    response = external_tool_agent.step(
        "When is the release date of the video game Portal?"
    )
    print(response.msg.content)

    usr_msg = "What's the result of the release year of Portal subtracted by"
    "the year that United States was founded?"
    # This will first automatically run the internal tool to check the years
    # Then it will request the external tool to calculate the sum
    response = external_tool_agent.step(usr_msg)
    # This should be empty
    print(response.msg.content)
    external_tool_request = response.info["external_tool_request"]
    # This will print the info of the external tool request
    print(external_tool_request)


if __name__ == "__main__":
    main()


# flake8: noqa :E501
"""
Output:
The video game "Portal" was released in 2007 as part of a bundle called The Orange Box for Windows, Xbox 360, and PlayStation 3.

ChatCompletionMessageFunctionToolCall(id='call_U5Xju7vYtAQAEW4D1M8R1kgs', function=Function(arguments='{"a": 2007, "b": 1776}', name='sub'), type='function')
"""
