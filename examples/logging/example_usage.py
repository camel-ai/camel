#!/usr/bin/env python3
r"""
Example usage of PromptLogger and HTML log viewer.

This script demonstrates how to integrate PromptLogger with CAMEL agents
to automatically log and visualize agent-LLM interactions.

Usage:
    python example_usage.py

After running, convert the log to HTML:
    python llm_log_to_html.py example_agent_log.log
"""

from prompt_logger import PromptLogger


def example_basic_logging():
    r"""Example 1: Basic prompt logging."""
    print("=" * 60)
    print("Example 1: Basic Prompt Logging")
    print("=" * 60)

    # Initialize logger
    logger = PromptLogger("example_agent_log.log")

    # Simulate a conversation
    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant specialized in "
            "solving coding problems.",
        },
        {
            "role": "user",
            "content": "Write a Python function to calculate Fibonacci numbers.",
        },
    ]

    # Log the prompt
    prompt_num = logger.log_prompt(
        messages, model_info="gpt-4", iteration=1
    )
    print(f"✅ Logged prompt #{prompt_num}")

    # Simulate assistant response
    messages.append(
        {
            "role": "assistant",
            "content": "Here's a Python function to calculate Fibonacci "
            "numbers:\n\ndef fibonacci(n):\n    if n <= 1:\n        "
            "return n\n    return fibonacci(n-1) + fibonacci(n-2)",
        }
    )

    # Log the updated conversation
    prompt_num = logger.log_prompt(
        messages, model_info="gpt-4", iteration=2
    )
    print(f"✅ Logged prompt #{prompt_num}")

    # Get stats
    stats = logger.get_stats()
    print(f"\n📊 Logging Statistics:")
    print(f"   Total prompts: {stats['total_prompts']}")
    print(f"   Log file: {stats['log_file']}")
    print(f"   File exists: {stats['file_exists']}")
    print()


def example_with_tool_calls():
    r"""Example 2: Logging with tool calls."""
    print("=" * 60)
    print("Example 2: Logging with Tool Calls")
    print("=" * 60)

    logger = PromptLogger("example_with_tools.log")

    # Conversation with tool usage
    messages = [
        {"role": "system", "content": "You are a helpful assistant with "
         "access to tools."},
        {
            "role": "user",
            "content": "What's the weather like in San Francisco?",
        },
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_abc123",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"location": "San Francisco, CA"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_abc123",
            "content": '{"temperature": 65, "condition": "sunny"}',
        },
        {
            "role": "assistant",
            "content": "The weather in San Francisco is currently sunny "
            "with a temperature of 65°F.",
        },
    ]

    prompt_num = logger.log_prompt(messages, model_info="gpt-4", iteration=1)
    print(f"✅ Logged conversation with tool calls (prompt #{prompt_num})")
    print()


def example_multi_turn_conversation():
    r"""Example 3: Multi-turn conversation logging."""
    print("=" * 60)
    print("Example 3: Multi-turn Conversation")
    print("=" * 60)

    logger = PromptLogger("example_multi_turn.log")

    # Initial messages
    messages = [
        {"role": "system", "content": "You are a helpful coding assistant."}
    ]

    # Turn 1
    messages.append({"role": "user", "content": "How do I read a file in "
                     "Python?"})
    logger.log_prompt(messages, model_info="gpt-4", iteration=1)

    messages.append(
        {
            "role": "assistant",
            "content": "You can use the `open()` function with a context "
            "manager:\n```python\nwith open('file.txt', 'r') as f:\n    "
            "content = f.read()\n```",
        }
    )
    logger.log_prompt(messages, model_info="gpt-4", iteration=2)

    # Turn 2
    messages.append(
        {"role": "user", "content": "What if the file doesn't exist?"}
    )
    logger.log_prompt(messages, model_info="gpt-4", iteration=3)

    messages.append(
        {
            "role": "assistant",
            "content": "You should use a try-except block to handle "
            "FileNotFoundError:\n```python\ntry:\n    with "
            "open('file.txt', 'r') as f:\n        content = f.read()\nexcept "
            "FileNotFoundError:\n    print('File not found')\n```",
        }
    )
    logger.log_prompt(messages, model_info="gpt-4", iteration=4)

    stats = logger.get_stats()
    print(f"✅ Logged {stats['total_prompts']} prompts from multi-turn "
          f"conversation")
    print()


def example_integration_with_camel_agent():
    r"""Example 4: Integration pattern with CAMEL ChatAgent."""
    print("=" * 60)
    print("Example 4: Integration Pattern with CAMEL Agent")
    print("=" * 60)
    print()
    print("To integrate with CAMEL ChatAgent, you can monkey-patch the "
          "_get_model_response method:")
    print()
    print(
        """
```python
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from prompt_logger import PromptLogger

# Initialize logger
logger = PromptLogger("agent_conversation.log")

# Store original method
original_get_response = ChatAgent._get_model_response

# Create patched method
def logged_get_response(self, messages, **kwargs):
    # Log before sending to model
    openai_messages = [msg.to_openai_message() for msg in messages]
    logger.log_prompt(
        openai_messages,
        model_info=str(self.model_config.model_type),
        iteration=logger.prompt_counter
    )

    # Call original method
    return original_get_response(self, messages, **kwargs)

# Apply patch
ChatAgent._get_model_response = logged_get_response

# Now use the agent normally
agent = ChatAgent(
    system_message=BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="You are a helpful assistant."
    )
)

# All interactions will be automatically logged
user_msg = BaseMessage.make_user_message(
    role_name="User",
    content="Hello!"
)
response = agent.step(user_msg)

# Convert to HTML after execution:
# python llm_log_to_html.py agent_conversation.log
```
    """
    )
    print()


def main():
    r"""Run all examples."""
    print("\n🎯 PromptLogger Examples\n")

    example_basic_logging()
    example_with_tool_calls()
    example_multi_turn_conversation()
    example_integration_with_camel_agent()

    print("=" * 60)
    print("✅ All examples completed!")
    print("=" * 60)
    print()
    print("📝 Log files created:")
    print("   - example_agent_log.log")
    print("   - example_with_tools.log")
    print("   - example_multi_turn.log")
    print()
    print("🎨 Convert to HTML with:")
    print("   python llm_log_to_html.py <log_file>")
    print()


if __name__ == "__main__":
    main()
