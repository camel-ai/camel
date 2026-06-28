#!/usr/bin/env python3
r"""
Example usage of PromptLogger with real CAMEL ChatAgent interactions.

This script demonstrates how to integrate PromptLogger with CAMEL agents
to automatically log and visualize real agent-LLM interactions.

Usage:
    python example_llm_log_to_html.py

The script will automatically convert logs to HTML using the llm_log_to_html
module from camel.logging.
"""

import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.logging import (
    disable_agent_logging,
    enable_agent_logging,
    get_logger,
)
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Load environment variables
load_dotenv()

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent


def example_simple_conversation():
    r"""Example 1: Simple conversation with real ChatAgent."""
    print("=" * 70)
    print("Example 1: Simple Conversation with Real Agent")
    print("=" * 70)
    print()

    # Disable any existing logging first
    disable_agent_logging(verbose=False)

    # Enable automatic logging for all agents
    log_path = SCRIPT_DIR / "example_simple_conversation.log"
    enable_agent_logging(str(log_path))

    # Create a ChatAgent
    sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are a helpful AI assistant specialized in Python programming.",
    )

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=ChatGPTConfig(temperature=0.7).as_dict(),
    )

    agent = ChatAgent(
        system_message=sys_msg,
        model=model,
    )

    print("🤖 Agent created. Asking a question...\n")

    # User question
    user_msg = BaseMessage.make_user_message(
        role_name="User",
        content="Write a simple Python function to check if a number is prime.",
    )

    # Get response (this will be automatically logged)
    response = agent.step(user_msg)

    print(f"👤 User: {user_msg.content}\n")
    print(f"🤖 Assistant: {response.msg.content}\n")

    # Get stats
    logger = get_logger()
    if logger:
        stats = logger.get_stats()
        print(f"📊 Logged {stats['total_prompts']} prompts to {stats['log_file']}")
    print()


def example_multi_turn_conversation():
    r"""Example 2: Multi-turn conversation with real agent."""
    print("=" * 70)
    print("Example 2: Multi-turn Conversation")
    print("=" * 70)
    print()

    # Disable any existing logging first
    disable_agent_logging(verbose=False)

    # Enable automatic logging for all agents
    log_path = SCRIPT_DIR / "example_multi_turn.log"
    enable_agent_logging(str(log_path))

    # Create agent
    sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are a helpful coding tutor.",
    )

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=ChatGPTConfig(temperature=0.7).as_dict(),
    )

    agent = ChatAgent(
        system_message=sys_msg,
        model=model,
    )

    print("🤖 Starting multi-turn conversation...\n")

    # Turn 1
    user_msg1 = BaseMessage.make_user_message(
        role_name="User",
        content="How do I read a file in Python?",
    )
    response1 = agent.step(user_msg1)
    print(f"👤 User: {user_msg1.content}")
    print(f"🤖 Assistant: {response1.msg.content}\n")

    # Turn 2
    user_msg2 = BaseMessage.make_user_message(
        role_name="User",
        content="What if the file doesn't exist? How do I handle that?",
    )
    response2 = agent.step(user_msg2)
    print(f"👤 User: {user_msg2.content}")
    print(f"🤖 Assistant: {response2.msg.content}\n")

    # Turn 3
    user_msg3 = BaseMessage.make_user_message(
        role_name="User",
        content="Can you show me a complete example with error handling?",
    )
    response3 = agent.step(user_msg3)
    print(f"👤 User: {user_msg3.content}")
    print(f"🤖 Assistant: {response3.msg.content}\n")

    # Get stats
    logger = get_logger()
    if logger:
        stats = logger.get_stats()
        print(f"📊 Logged {stats['total_prompts']} prompts from multi-turn conversation")
        print(f"   Log file: {stats['log_file']}")
    print()


def main():
    r"""Run all examples with real ChatAgent interactions."""
    print("\n" + "=" * 70)
    print("🎯 PromptLogger Examples with Real CAMEL ChatAgent")
    print("=" * 70)
    print()

    # Run examples
    try:
        example_simple_conversation()
        example_multi_turn_conversation()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("=" * 70)
    print("✅ All examples completed!")
    print("=" * 70)
    print()
    print("📝 Log files created:")
    print("   - example_simple_conversation.log")
    print("   - example_multi_turn.log")
    print()

    # Automatically convert logs to HTML
    print("🎨 Converting logs to HTML...")
    print()

    log_files = [
        SCRIPT_DIR / "example_simple_conversation.log",
        SCRIPT_DIR / "example_multi_turn.log",
    ]

    for log_file in log_files:
        if log_file.exists():
            try:
                print(f"Converting {log_file.name}...")
                result = subprocess.run(
                    [sys.executable, "-m", "camel.logging.llm_log_to_html", str(log_file)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                print(result.stdout)
            except subprocess.CalledProcessError as e:
                print(f"❌ Error converting {log_file.name}: {e}")
                print(e.stderr)

    print()
    print("🎉 All done! HTML viewer files generated in:")
    print(f"   {SCRIPT_DIR}")
    print()


if __name__ == "__main__":
    main()
