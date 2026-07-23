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

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import MemantoToolkit
from camel.types import ModelPlatformType, ModelType


def run_memanto_toolkit_example() -> None:
    r"""Demonstrates a ChatAgent using MemantoToolkit for memory tools.

    Prerequisites:
        1. Install Memanto: ``pip install memanto``
        2. Start the server: ``memanto serve``
        3. Create the agent once: ``memanto agent create my-camel-agent``
        4. Set ``OPENAI_API_KEY`` for the ChatAgent model backend.
    """
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    agent = ChatAgent(
        system_message=(
            "You are an assistant that can store and recall long-term "
            "memories using Memanto tools."
        ),
        model=model,
    )

    toolkit = MemantoToolkit(agent_id="my-camel-agent")
    for tool in toolkit.get_tools():
        agent.add_tool(tool)

    print("\n--- Remember a preference ---")
    remember_msg = (
        "Please remember that the user prefers concise Python examples."
    )
    response = agent.step(remember_msg)
    print(f"[Agent] {response.msgs[0].content}")

    print("\n--- Recall the preference ---")
    recall_msg = "What do you remember about the user's coding preferences?"
    response = agent.step(recall_msg)
    print(f"[Agent] {response.msgs[0].content}")


if __name__ == "__main__":
    run_memanto_toolkit_example()
