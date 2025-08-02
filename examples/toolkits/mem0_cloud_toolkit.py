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

"""
Mem0CloudToolkit Example with CAMEL AI

This example demonstrates how to use the Mem0CloudToolkit to create AI agents
with persistent memory capabilities using Mem0's cloud-based storage.

Features demonstrated:
- Basic toolkit functionality (add, search, retrieve, delete memories)
- CAMEL agent integration with memory tools
- Interactive conversation with memory persistence
- API key setup and error handling

Requirements:
- pip install camel-ai mem0ai
- Set MEM0_API_KEY and GEMINI_API_KEY environment variables
- Mem0 account: https://app.mem0.ai/dashboard/api-keys
- Gemini API key: https://aistudio.google.com/app/apikey

Usage:
    python mem0_cloud_toolkit.py
"""

import os
from getpass import getpass

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import Mem0CloudToolkit
from camel.types import ModelPlatformType, ModelType


def setup_api_keys():
    """Setup API keys - prompt if not found in environment."""
    print("🔑 Setting up API keys...")

    # Mem0 API Key
    if not os.getenv("MEM0_API_KEY"):
        mem0_key = getpass(
            "Enter your Mem0 API key "
            "(from https://app.mem0.ai/dashboard/api-keys): "
        )
        os.environ["MEM0_API_KEY"] = mem0_key
    else:
        print("✅ MEM0_API_KEY found")

    # Gemini API Key
    if not os.getenv("GEMINI_API_KEY"):
        gemini_key = getpass(
            "Enter your Gemini API key "
            "(from https://aistudio.google.com/app/apikey): "
        )
        os.environ["GEMINI_API_KEY"] = gemini_key
    else:
        print("✅ GEMINI_API_KEY found")


def test_toolkit_basic():
    """Test basic toolkit functionality."""
    print("\n🛠️ Testing Mem0CloudToolkit...")

    # Initialize toolkit with unique identifiers
    agent_id = "example-agent"
    user_id = "example-user"

    toolkit = Mem0CloudToolkit(agent_id=agent_id, user_id=user_id)
    print(f"✅ Toolkit initialized for agent: {agent_id}, user: {user_id}")

    # Test 1: Add memories with different types of information
    print("\n📝 Adding memories...")
    result1 = toolkit.add_memory(
        "I prefer working in the morning between 9-11 AM",
        metadata={"category": "work_preference", "type": "schedule"},
    )
    print(f"Memory 1: {result1}")

    result2 = toolkit.add_memory(
        "My favorite programming language is Python",
        metadata={"category": "skill", "type": "programming"},
    )
    print(f"Memory 2: {result2}")

    result3 = toolkit.add_memory(
        "I'm currently working on a machine learning project for healthcare"
    )
    print(f"Memory 3: {result3}")

    # Test 2: Search memories using semantic search
    print("\n🔍 Searching memories...")
    search_result = toolkit.search_memories("work schedule preferences")
    print(f"Search result: {search_result[:100]}...")

    # Test 3: Retrieve all memories
    print("\n📚 Retrieving all memories...")
    all_memories = toolkit.retrieve_memories()
    print(f"All memories: {all_memories[:100]}...")

    return toolkit


def create_agent_with_memory(toolkit):
    """Create CAMEL agent with memory toolkit."""
    print("\n🤖 Creating CAMEL agent with memory...")

    # Get tools from toolkit
    tools = toolkit.get_tools()
    print(f"Available tools: {[tool.get_function_name() for tool in tools]}")

    # Create Gemini model (fast and cost-effective)
    model = ModelFactory.create(
        model_platform=ModelPlatformType.GEMINI,
        model_type=ModelType.GEMINI_1_5_FLASH,
    )

    # System message for the memory assistant
    system_message = (
        "You are a helpful memory assistant powered by Mem0 cloud storage. "
        "When you use memory tools, explain what you did in a friendly way. "
        "You can help users store information, search their memories, and "
        "recall important details from past conversations."
    )

    sys_msg = BaseMessage.make_assistant_message(
        role_name="Memory Assistant",
        content=system_message,
    )

    # Create agent with memory tools
    agent = ChatAgent(sys_msg, model=model, tools=tools)
    print("✅ Agent created successfully!")

    return agent


def test_agent_conversations(agent):
    """Test conversations with the memory-enabled agent."""
    print("\n💬 Testing agent conversations...")

    test_messages = [
        "Remember that I like coffee in the morning and prefer decaf after 2 PM",
        "Store that I'm working on a project called 'Smart Home Assistant' "
        "using Python and IoT sensors",
        "What do you remember about my morning preferences?",
        "What projects am I currently working on?",
        "Search for information about my coffee preferences",
    ]

    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Test {i} ---")
        print(f"👤 User: {message}")

        user_msg = BaseMessage.make_user_message(
            role_name="User", content=message
        )
        response = agent.step(user_msg)

        print(f"🤖 Agent: {response.msg.content}")


def interactive_mode(agent, toolkit):
    """Interactive chat mode with the memory-enabled agent."""
    print("\n🎯 Interactive Mode")
    print("Type your message, 'clear' to delete memories, or 'exit' to quit")
    print("Example commands:")
    print("  - 'Remember that I prefer tea over coffee'")
    print("  - 'What do you know about my preferences?'")
    print("  - 'Search for information about my work projects'")
    print("  - 'clear' (to delete all memories)")
    print("  - 'exit' (to quit)\n")

    while True:
        try:
            user_input = input("> ").strip()

            if user_input.lower() in ["exit", "quit"]:
                print("👋 Goodbye! Your memories are safely stored in Mem0.")
                break

            if user_input.lower() == "clear":
                result = toolkit.delete_memories()
                print(f"🧹 {result}")
                continue

            if not user_input:
                continue

            # Send message to agent
            user_msg = BaseMessage.make_user_message(
                role_name="User", content=user_input
            )
            response = agent.step(user_msg)
            print(f"🤖 {response.msg.content}")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Please check your API keys and internet connection.")


def main():
    """Main function demonstrating Mem0CloudToolkit usage."""
    print("🧠 Mem0 + CAMEL AI Example")
    print("=" * 50)
    print("This example demonstrates persistent memory for AI agents")
    print("using Mem0's cloud storage and CAMEL AI framework.")
    print("=" * 50)

    try:
        # Step 1: Setup API keys
        setup_api_keys()

        # Step 2: Test basic toolkit functionality
        toolkit = test_toolkit_basic()

        # Step 3: Create memory-enabled agent
        agent = create_agent_with_memory(toolkit)

        # Step 4: Test predefined conversations
        test_agent_conversations(agent)

        # Step 5: Interactive mode
        print("\n" + "=" * 50)
        choice = input("Try interactive mode? (y/n): ").strip().lower()
        if choice in ['y', 'yes']:
            interactive_mode(agent, toolkit)

        # Step 6: Cleanup option
        print("\n" + "=" * 50)
        cleanup = input("Clear all example memories? (y/n): ").strip().lower()
        if cleanup in ['y', 'yes']:
            result = toolkit.delete_memories()
            print(f"🧹 {result}")

        print("\n✅ Example completed successfully!")
        print("\nKey takeaways:")
        print("- Mem0CloudToolkit provides persistent memory across sessions")
        print("- Semantic search helps find relevant memories")
        print("- CAMEL agents can use memory tools naturally in conversation")
        print("- Metadata can be added for better memory organization")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you have valid API keys set")
        print("2. Check your internet connection")
        print("3. Ensure mem0ai package is installed: pip install mem0ai")
        print("4. Verify CAMEL AI is installed: pip install camel-ai")


if __name__ == "__main__":
    main()