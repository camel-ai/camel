#!/usr/bin/env python3
"""
Simple Mem0CloudToolkit Test Script with Gemini

This is a minimal test script similar to the Jupyter notebook - simple and to the point.
Uses Gemini instead of OpenAI for cost-effectiveness.

Requirements:
- pip install camel-ai mem0ai
- Set MEM0_API_KEY and GEMINI_API_KEY environment variables

Usage:
    python test_mem0_simple.py
"""

import os
from getpass import getpass

# Import CAMEL components
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
        mem0_key = getpass("Enter your Mem0 API key (from https://app.mem0.ai/dashboard/api-keys): ")
        os.environ["MEM0_API_KEY"] = mem0_key
    else:
        print("✅ MEM0_API_KEY found")
    
    # Gemini API Key
    if not os.getenv("GEMINI_API_KEY"):
        gemini_key = getpass("Enter your Gemini API key (from https://aistudio.google.com/app/apikey): ")
        os.environ["GEMINI_API_KEY"] = gemini_key
    else:
        print("✅ GEMINI_API_KEY found")


def test_toolkit_basic():
    """Test basic toolkit functionality."""
    print("\n🛠️ Testing Mem0CloudToolkit...")
    
    # Initialize toolkit
    agent_id = "simple-test-agent"
    user_id = "simple-test-user"
    
    toolkit = Mem0CloudToolkit(agent_id=agent_id, user_id=user_id)
    print(f"✅ Toolkit initialized for agent: {agent_id}, user: {user_id}")
    
    # Test 1: Add memory
    print("\n📝 Adding memories...")
    result1 = toolkit.add_memory("I prefer working in the morning between 9-11 AM")
    print(f"Memory 1: {result1}")
    
    result2 = toolkit.add_memory("My favorite programming language is Python")  
    print(f"Memory 2: {result2}")
    
    # Test 2: Search memories
    print("\n🔍 Searching memories...")
    search_result = toolkit.search_memories("work schedule")
    print(f"Search result: {search_result[:100]}...")
    
    # Test 3: Get all memories
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
    
    # Create Gemini model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.GEMINI,
        model_type=ModelType.GEMINI_1_5_FLASH,  # Fast and cheap
    )
    
    # System message
    system_message = (
        "You are a helpful memory assistant. When you use memory tools, "
        "explain what you did in a friendly way."
    )
    
    sys_msg = BaseMessage.make_assistant_message(
        role_name="Memory Assistant",
        content=system_message,
    )
    
    # Create agent
    agent = ChatAgent(sys_msg, model=model, tools=tools)
    print("✅ Agent created successfully!")
    
    return agent


def test_agent_conversations(agent):
    """Test some conversations with the memory agent."""
    print("\n💬 Testing agent conversations...")
    
    test_messages = [
        "Remember that I like coffee in the morning",
        "Store that I'm working on a project called 'Smart Home'",
        "What do you remember about my morning preferences?",
        "What projects am I working on?"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Test {i} ---")
        print(f"👤 User: {message}")
        
        user_msg = BaseMessage.make_user_message(role_name="User", content=message)
        response = agent.step(user_msg)
        
        print(f"🤖 Agent: {response.msg.content}")


def interactive_mode(agent, toolkit):
    """Simple interactive mode."""
    print("\n🎯 Interactive Mode")
    print("Type your message, 'clear' to delete memories, or 'exit' to quit\n")
    
    while True:
        try:
            user_input = input("> ").strip()
            
            if user_input.lower() in ["exit", "quit"]:
                print("👋 Goodbye!")
                break
                
            if user_input.lower() == "clear":
                result = toolkit.delete_memories()
                print(f"🧹 {result}")
                continue
                
            if not user_input:
                continue
                
            # Send to agent
            user_msg = BaseMessage.make_user_message(role_name="User", content=user_input)
            response = agent.step(user_msg)
            print(f"🤖 {response.msg.content}")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    """Main function - simple and straightforward."""
    print("🧠 Mem0 + CAMEL AI Simple Test")
    print("=" * 40)
    
    try:
        # Step 1: Setup API keys
        setup_api_keys()
        
        # Step 2: Test toolkit
        toolkit = test_toolkit_basic()
        
        # Step 3: Create agent
        agent = create_agent_with_memory(toolkit)
        
        # Step 4: Test conversations
        test_agent_conversations(agent)
        
        # Step 5: Interactive mode
        print("\n" + "=" * 40)
        choice = input("Try interactive mode? (y/n): ").strip().lower()
        if choice in ['y', 'yes']:
            interactive_mode(agent, toolkit)
        
        # Step 6: Cleanup option
        cleanup = input("Clear all test memories? (y/n): ").strip().lower()
        if cleanup in ['y', 'yes']:
            result = toolkit.delete_memories()
            print(f"🧹 {result}")
        
        print("\n✅ Test completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure you have the required API keys and packages installed.")


if __name__ == "__main__":
    main()