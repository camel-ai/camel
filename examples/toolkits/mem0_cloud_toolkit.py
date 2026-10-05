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
Mem0CloudToolkit Example

This example demonstrates how to create AI agents with Mem0-powered memory
where the agent's own memory system uses Mem0 cloud storage for persistence.

Requirements:
- pip install mem0ai
- Set MEM0_API_KEY environment variable
- Mem0 account: https://app.mem0.ai/dashboard/api-keys
"""

import os
from getpass import getpass

from camel.agents import ChatAgent
from camel.memories import ChatHistoryMemory
from camel.memories.context_creators.score_based import (
    ScoreBasedContextCreator,
)
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.storages.key_value_storages.mem0_cloud import Mem0Storage
from camel.toolkits import Mem0CloudToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import OpenAITokenCounter


def setup_api_key():
    """Setup Mem0 API key if not found in environment."""
    if not os.getenv("MEM0_API_KEY"):
        mem0_key = getpass("Enter your Mem0 API key: ")
        os.environ["MEM0_API_KEY"] = mem0_key


def create_agent_with_mem0_memory(user_id="camel_memory"):
    """Create agent where the agent's own memory is Mem0-powered."""
    # Setup Mem0 memory components
    agent_id = "example-agent"

    storage = Mem0Storage(agent_id=agent_id, user_id=user_id)
    token_counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
    context_creator = ScoreBasedContextCreator(
        token_counter=token_counter, token_limit=4096
    )

    # Create Mem0 memory for the agent
    mem0_memory = ChatHistoryMemory(
        context_creator=context_creator,
        storage=storage,
        agent_id=agent_id,
    )

    # Create model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.GEMINI,
        model_type=ModelType.GEMINI_2_5_FLASH,
    )

    # Create agent with Mem0 memory
    sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are a helpful assistant with persistent memory. "
                "When users ask you to 'remember' something or 'search' for memories, "
                "use the appropriate memory tools available to you.",
    )

    agent = ChatAgent(
        system_message=sys_msg,
        model=model,
        memory=mem0_memory,  # Agent's primary memory is Mem0
    )

    # Add memory management tools
    toolkit = Mem0CloudToolkit(agent_id=agent_id, user_id=user_id)
    agent.tools = toolkit.get_tools()

    return agent, toolkit


def main():
    """Main function demonstrating Mem0CloudToolkit with integrated agent memory."""
    print("Mem0CloudToolkit Example")
    print("=" * 40)

    # Setup API key
    setup_api_key()

    # Create agent with Mem0 memory
    agent, toolkit = create_agent_with_mem0_memory()
    print("Agent created with Mem0 memory")

    # Test 1: Agent conversation (automatically stored in Mem0)
    print("\n--- Test 1: Automatic Memory Storage ---")
    response1 = agent.step("My name is Alice and I work at TechCorp")
    print("User: My name is Alice and I work at TechCorp")
    print("Agent:", response1.msg.content)

    # Test 2: Agent remembers from Mem0
    print("\n--- Test 2: Memory Recall ---")
    response2 = agent.step("What's my name and where do I work?")
    print("User: What's my name and where do I work?")
    print("Agent:", response2.msg.content)

    # Test 3: Explicit memory tool usage
    print("\n--- Test 3: Memory Tools ---")
    response3 = agent.step("Remember that I like coffee in the morning")
    print("User: Remember that I like coffee in the morning")
    print("Agent:", response3.msg.content)

    # Test 4: Search memories
    print("\n--- Test 4: Memory Search ---")
    response4 = agent.step("Search for information about my preferences")
    print("User: Search for information about my preferences")
    print("Agent:", response4.msg.content)

    # Interactive loop (optional)
    print("\n--- Interactive Mode ---")
    print("Type 'exit' to quit, 'clear' to clear memories")

    while True:
        user_input = input("\nUser: ").strip()

        if user_input.lower() == 'exit':
            print("Goodbye!")
            break
        elif user_input.lower() == 'clear':
            result = toolkit.clear_memory()
            print("System:", result)
            continue
        elif not user_input:
            continue

        response = agent.step(user_input)
        print("Agent:", response.msg.content)


if __name__ == "__main__":
    main()
