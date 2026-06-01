#!/usr/bin/env python3

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

r"""Example of using Evolink models in CAMEL."""

import os

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType


def test_evolink_model() -> None:
    r"""Test an Evolink model using ModelFactory."""

    # You need to set EVOLINK_API_KEY in your environment variables
    # (get one at https://evolink.ai/dashboard/keys) or pass it directly as
    # the api_key parameter.
    api_key = os.environ.get("EVOLINK_API_KEY")
    if not api_key:
        print("Skipping Evolink test - EVOLINK_API_KEY not set")
        return

    # Evolink exposes an OpenAI-compatible API, so the model id is passed as a
    # plain string (e.g. "gpt-5.2", "gemini-3.0-pro", "deepseek-v4-pro").
    model = ModelFactory.create(
        model_platform=ModelPlatformType.EVOLINK,
        model_type="gpt-5.2",
        api_key=api_key,
        model_config_dict=ChatGPTConfig(temperature=0.2).as_dict(),
    )

    agent = ChatAgent(
        system_message="You are a helpful assistant.",
        model=model,
    )

    user_msg = "Say hi to the CAMEL AI community in a friendly way."
    response = agent.step(user_msg)

    print(f"User message: {user_msg}")
    print(f"Agent response: {response.msg.content}")


def main() -> None:
    r"""Main function to test Evolink models."""
    print("Testing Evolink models:")
    print("=" * 40)
    test_evolink_model()


if __name__ == "__main__":
    main()
