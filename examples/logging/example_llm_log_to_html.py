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

import os
import subprocess
from pathlib import Path

from dotenv import load_dotenv

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.logging.prompt_logger import PromptLogger
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType

# Load environment variables
load_dotenv()

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent

# Global logger instance
prompt_logger = None


def setup_prompt_logging():
    r"""Set up automatic prompt logging by monkey-patching ChatAgent.

    This function patches ChatAgent's _get_model_response method to
    automatically log all LLM interactions to the PromptLogger.
    """
    global prompt_logger

    # Store the original method
    original_get_model_response = ChatAgent._get_model_response

    def logged_get_model_response(
        self,
        openai_messages,
        num_tokens,
        current_iteration=0,
        response_format=None,
        tool_schemas=None,
        prev_num_openai_messages=0,
    ):
        r"""Wrapper that logs prompts before calling the original method."""
        # Log the prompt if logger is available
        if prompt_logger:
            model_info = f"{self.model_backend.model_type}"
            prompt_logger.log_prompt(
                openai_messages,
                model_info=model_info,
                iteration=current_iteration,
            )

        # Call the original method
        return original_get_model_response(
            self,
            openai_messages,
            num_tokens,
            current_iteration,
            response_format,
            tool_schemas,
            prev_num_openai_messages,
        )

    # Apply the patch
    ChatAgent._get_model_response = logged_get_model_response
    print("✅ ChatAgent patched for automatic prompt logging\n")


def example_simple_conversation():
    r"""Example 1: Simple conversation with real ChatAgent."""
    global prompt_logger

    print("=" * 70)
    print("Example 1: Simple Conversation with Real Agent")
    print("=" * 70)
    print()

    # Initialize logger
    log_path = SCRIPT_DIR / "example_simple_conversation.log"
    prompt_logger = PromptLogger(str(log_path))

    # Create a ChatAgent
    sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are a helpful AI assistant specialized in Python programming.",
    )

    model = ModelFactory.create(
        model_platform=ModelPlatformType.AZURE,
        model_type="gpt-5.1",
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        url=os.getenv("AZURE_OPENAI_BASE_URL"),
        api_version=os.getenv("AZURE_API_VERSION"),
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
    stats = prompt_logger.get_stats()
    print(f"📊 Logged {stats['total_prompts']} prompts to {stats['log_file']}")
    print()


def example_multi_turn_conversation():
    r"""Example 3: Multi-turn conversation with real agent."""
    global prompt_logger

    print("=" * 70)
    print("Example 3: Multi-turn Conversation")
    print("=" * 70)
    print()

    # Initialize logger
    log_path = SCRIPT_DIR / "example_multi_turn.log"
    prompt_logger = PromptLogger(str(log_path))

    # Create agent
    sys_msg = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are a helpful coding tutor.",
    )

    model = ModelFactory.create(
        model_platform=ModelPlatformType.AZURE,
        model_type="gpt-5.1",
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        url=os.getenv("AZURE_OPENAI_BASE_URL"),
        api_version=os.getenv("AZURE_API_VERSION"),
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
    stats = prompt_logger.get_stats()
    print(f"📊 Logged {stats['total_prompts']} prompts from multi-turn conversation")
    print(f"   Log file: {stats['log_file']}")
    print()


def main():
    r"""Run all examples with real ChatAgent interactions."""
    print("\n" + "=" * 70)
    print("🎯 PromptLogger Examples with Real CAMEL ChatAgent")
    print("=" * 70)
    print()

    # Set up logging
    setup_prompt_logging()

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
                    ["python3", "-m", "camel.logging.llm_log_to_html", str(log_file)],
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
