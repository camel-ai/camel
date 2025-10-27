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
Custom Client Integration Example

Demonstrates using custom OpenAI-compatible clients (e.g., from RL frameworks
like AReaL or rLLM) with CAMEL agents.
"""

import asyncio

from areal.experimental.openai import ArealOpenAI

from camel.agents import ChatAgent
from camel.models import OpenAICompatibleModel


async def async_example():
    # Create model with async client
    areal_client = ArealOpenAI(engine=engine, tokenizer=tokenizer)
    model = OpenAICompatibleModel(
        model_type="model-name",
        async_client=areal_client,
    )

    # Create agent
    agent = ChatAgent(
        system_message="You are a helpful async assistant.",
        model=model,
    )

    user_msg = "Hello, async world!"

    # Use async step
    response = await agent.astep(user_msg)
    print(response.msgs[0].content)


# Run async example
asyncio.run(async_example())
