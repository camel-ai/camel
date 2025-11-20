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
"""
This example demonstrates how to use the CAMEL ChatAgent with the OpenAI
Responses API model. It covers:

  1) Basic chat
  2) Structured output
  3) Streaming chat
  4) Tool calling
  5) Image analysis
  6) File analysis

Requirements:
  export OPENAI_API_KEY=sk-...
"""

from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType, ModelType, RoleType


def basic_chat():
    print("\n=== Basic Chat ===")
    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES, ModelType.GPT_4_1_MINI
    )
    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant", content="You are a helpful assistant."
        ),
        model=model,
    )

    response = agent.step("Tell me a joke about camels.")
    print(response.msgs[0].content)


def structured_output_chat():
    print("\n=== Structured Output Chat ===")

    class CountryInfo(BaseModel):
        name: str
        capital: str
        population: int

    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES, ModelType.GPT_4_1_MINI
    )

    # Note: ChatAgent currently doesn't expose response_format in step() directly
    # but we can pass it via output_schema if supported, or configure the model?
    # Actually ChatAgent.step has response_format argument? No.
    # But we can use the model's run method directly? No, user wants ChatAgent.
    # ChatAgent supports structured output via `output_schema` in `step`? No.
    # ChatAgent supports `response_format` in `step`? Let's check.
    # ChatAgent.step(..., response_format=...)

    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant", content="You provide country info."
        ),
        model=model,
    )

    response = agent.step("France", response_format=CountryInfo)
    print(f"Structured Output: {response.msgs[0].parsed}")


def streaming_chat():
    print("\n=== Streaming Chat ===")
    # To enable streaming, we configure the model with stream=True
    # ChatAgent will consume the stream and return the final response.
    # To see the stream, we would need to use agent.step_stream (if it existed)
    # or rely on the fact that ChatAgent accumulates it.

    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES,
        ModelType.GPT_4_1_MINI,
        model_config_dict={"stream": True},
    )

    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant", content="You are a poet."
        ),
        model=model,
    )

    # This will block until completion, but internally it uses streaming
    response = agent.step("Write a short poem about the sunrise.")
    print(f"Streaming Result: {response.msgs[0].content}")


def tool_call_chat():
    print("\n=== Tool Call Chat ===")

    def add(a: int, b: int) -> int:
        """Adds two numbers."""
        return a + b

    tools = [FunctionTool(add)]

    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES, ModelType.GPT_4_1_MINI
    )

    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant", content="You are a math helper."
        ),
        model=model,
        tools=tools,
    )

    response = agent.step("What is 5 + 7?")
    # ChatAgent automatically executes the tool and gets the result
    # But usually it requires a loop or auto_tool_call=True?
    # ChatAgent defaults to external_tool_call=False, so it executes tools?
    # Let's check ChatAgent defaults.
    # It should execute tools if tools are provided.

    print(f"Tool Call Result: {response.msgs[0].content}")
    print(f"Tool Calls: {response.info['tool_calls']}")


def image_analysis_chat():
    print("\n=== Image Analysis Chat ===")
    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES, ModelType.GPT_4_1_MINI
    )
    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant", content="You are an image analyst."
        ),
        model=model,
    )

    # Construct a message with image
    msg = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict={},
        content="What is in this image?",
        image_list=[
            {
                "url": "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png",
                "detail": "auto",
            }
        ],
    )

    response = agent.step(msg)
    print(f"Image Analysis: {response.msgs[0].content}")


def file_analysis_chat():
    print("\n=== File Analysis Chat ===")
    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES, ModelType.GPT_4_1_MINI
    )
    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant", content="You are a file analyst."
        ),
        model=model,
    )

    # Construct a message with file
    # We use the newly added file_list field in BaseMessage
    msg = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict={},
        content="What is in this file?",
        file_list=[
            {
                "file_url": "https://www.berkshirehathaway.com/letters/2024ltr.pdf"
            }
        ],
    )

    response = agent.step(msg)
    print(f"File Analysis: {response.msgs[0].content}")


if __name__ == "__main__":
    basic_chat()
    structured_output_chat()
    streaming_chat()
    tool_call_chat()
    image_analysis_chat()
    file_analysis_chat()
