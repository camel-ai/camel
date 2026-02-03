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
"""OpenAI Responses API — quickstart with ModelFactory.

This example shows how to:
  1) Create the Responses backend via ModelFactory
  2) Make a basic non-streaming request
  3) Do structured output parsing with a Pydantic schema
  4) Make a tool call request
  5) Stream responses (text and tool calls)
  6) Analyze an image (multimodal input)
  7) Analyze a file (PDF input)

Requirements:
  export OPENAI_API_KEY=sk-...
"""

from __future__ import annotations

from pydantic import BaseModel

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


def basic_request() -> None:
    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES, ModelType.GPT_4_1_MINI
    )
    messages = [
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "Give me one sentence about the ocean."},
    ]
    resp = model.run(messages)
    # Responses backend returns CamelModelResponse
    print("Response ID:", resp.id)
    print("Text:\n", resp.output_messages[0].content)


class Country(BaseModel):
    name: str
    capital: str


def structured_output() -> None:
    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES, ModelType.GPT_4_1_MINI
    )
    messages = [
        {
            "role": "user",
            "content": "Extract country and capital from: 'Paris is the capital of France.'",  # noqa:E501
        }
    ]
    resp = model.run(messages, response_format=Country)
    parsed = resp.output_messages[0].parsed
    print("Parsed:", parsed)


def streaming_request() -> None:
    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES,
        ModelType.GPT_4_1_MINI,
        model_config_dict={"stream": True},
    )
    messages = [
        {"role": "system", "content": "Stream your reply word by word."},
        {
            "role": "user",
            "content": "Describe a sunrise over mountains in one short paragraph.",  # noqa:E501
        },
    ]

    stream = model.run(messages)
    print("Streaming response:")
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print("\n")


def tool_call_request() -> None:
    from camel.toolkits import FunctionTool

    def add(a: int, b: int) -> int:
        """Adds two numbers."""
        return a + b

    add_tool = FunctionTool(add)

    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES, ModelType.GPT_4_1_MINI
    )

    tools = [add_tool.get_openai_tool_schema()]
    messages = [{"role": "user", "content": "What is 5 + 7?"}]

    resp = model.run(messages, tools=tools)
    print("Tool Calls:", resp.tool_call_requests)
    if resp.tool_call_requests:
        for tool_call in resp.tool_call_requests:
            print(f"Function: {tool_call.name}, Args: {tool_call.args}")


def image_analysis_request() -> None:
    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES, ModelType.GPT_4_1_MINI
    )

    # Using Responses API style input types (input_text, input_image)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "what is in this image?"},
                {
                    "type": "input_image",
                    "image_url": "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png",
                },
            ],
        }
    ]

    resp = model.run(messages)
    print("Image Analysis Result:\n", resp.output_messages[0].content)


def file_analysis_request() -> None:
    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES, ModelType.GPT_4_1_MINI
    )

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "what is in this file?"},
                {
                    "type": "input_file",
                    "file_url": "https://www.berkshirehathaway.com/letters/2024ltr.pdf",
                },
            ],
        }
    ]

    resp = model.run(messages)
    print("File Analysis Result:\n", resp.output_messages[0].content)


if __name__ == "__main__":
    basic_request()
    structured_output()
    streaming_request()
    tool_call_request()
    image_analysis_request()
    file_analysis_request()
