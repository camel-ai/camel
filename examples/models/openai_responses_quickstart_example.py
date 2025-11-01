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
"""OpenAI Responses API — quickstart with ModelFactory.

This example shows how to:
  1) Create the Responses backend via ModelFactory
  2) Make a basic non-streaming request
  3) Do structured output parsing with a Pydantic schema

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


if __name__ == "__main__":
    basic_request()
    structured_output()
