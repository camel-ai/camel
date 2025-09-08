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
Sub-agent spawning example demonstrating how agents can delegate tasks to
specialized sub-agents while keeping their context clean.
"""

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import SubAgentToolkit
from camel.types import ModelPlatformType, ModelType


def main():
    # create the main agent with sub-agent toolkit
    toolkit = SubAgentToolkit()

    main_agent = ChatAgent(
        system_message="You are a helpful assistant that coordinates tasks "
        "and can spawn specialized sub-agents for complex work.",
        model=ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        ),
        toolkits_to_register_agent=[toolkit],
        tools=toolkit.get_tools(),
    )

    print("=" * 60)
    print("Sub-Agent Spawning Example")
    print("=" * 60)

    # example 1: spawn a fresh sub-agent with custom system prompt
    print("\n1. Testing fresh sub-agent spawning:")
    print("-" * 40)

    task1 = (
        "Please use spawn_sub_agent to create a research assistant that "
        "specializes in explaining scientific concepts. Ask the sub-agent to "
        "explain quantum computing in simple terms. Use "
        "inherit_from_parent=False and provide a system_prompt that makes "
        "the sub-agent act as a science teacher for beginners."
    )

    response1 = main_agent.step(task1)
    print(f"Main agent response: {response1.msg.content}")

    # example 2: spawn a sub-agent that inherits context
    print("\n2. Testing sub-agent with inherited context:")
    print("-" * 40)

    # first, give the main agent some context
    main_agent.step(
        "Remember that I'm working on a machine learning project about "
        "image classification for medical diagnosis. I need help with "
        "different aspects of this project."
    )

    task2 = (
        "Now use spawn_sub_agent to create a sub-agent that inherits your "
        "memory (inherit_from_parent=True) and ask it to suggest what "
        "evaluation metrics would be appropriate for our medical image "
        "classification project."
    )

    response2 = main_agent.step(task2)
    print(f"Main agent response: {response2.msg.content}")

    # example 3: demonstrate context cleanliness
    print("\n3. Testing context cleanliness:")
    print("-" * 40)

    # the main agent should have its original context, not sub-agent details
    context_check = main_agent.step(
        "What was the last thing we discussed about our machine learning "
        "project? Please don't use any tools, just respond based on your "
        "memory."
    )
    print(f"Main agent memory: {context_check.msg.content}")

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
