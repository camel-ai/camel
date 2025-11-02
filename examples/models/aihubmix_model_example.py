#!/usr/bin/env python3

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

r"""Example of using AIHubMix models in CAMEL."""

import os

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType


def test_aihubmix_model() -> None:
    r"""Test AIHubMix model using ModelFactory."""

    # Set up the model
    # You need to set AIHUBMIX_API_KEY in your environment variables
    # or directly pass it as api_key parameter
    api_key = os.environ.get("AIHUBMIX_API_KEY")
    if not api_key:
        print("Skipping AIHubMix test - AIHUBMIX_API_KEY not set")
        return

    model = ModelFactory.create(
        model_platform=ModelPlatformType.AIHUBMIX,
        model_type=ModelType.GPT_5,
        api_key=api_key,
        model_config_dict=ChatGPTConfig(temperature=0.2).as_dict(),
    )

    # Set up the agent
    agent = ChatAgent(
        system_message="You are a helpful assistant.",
        model=model,
    )

    # Test the agent
    user_msg = "Say hi to CAMEL AI community in a friendly way."
    response = agent.step(user_msg)

    print(f"User message: {user_msg}")
    print(f"Agent response: {response.msg.content}")


def test_aihubmix_with_custom_model() -> None:
    r"""Test AIHubMix model with a custom model name."""

    # Set up the model
    api_key = os.environ.get("AIHUBMIX_API_KEY")
    if not api_key:
        print("Skipping AIHubMix custom model test - AIHUBMIX_API_KEY not set")
        return

    model = ModelFactory.create(
        model_platform=ModelPlatformType.AIHUBMIX,
        model_type="gpt-4",  # Using a string directly
        api_key=api_key,
        model_config_dict=ChatGPTConfig(temperature=0.2).as_dict(),
    )

    # Set up the agent
    agent = ChatAgent(
        system_message="You are a helpful assistant.",
        model=model,
    )

    # Test the agent
    user_msg = "Explain what is an AI agent in one sentence."
    response = agent.step(user_msg)

    print(f"User message: {user_msg}")
    print(f"Agent response: {response.msg.content}")


def main():
    r"""Main function to test AIHubMix models."""
    print("Testing AIHubMix models:")
    print("=" * 40)

    test_aihubmix_model()
    print("-" * 40)
    test_aihubmix_with_custom_model()


if __name__ == "__main__":
    main()
