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
Streaming Token Counting Example

This example demonstrates how to use the new streaming token counting
capabilities in CAMEL to get accurate token usage data from streaming
API responses across different providers.
"""

import asyncio
import os

from dotenv import load_dotenv
from streaming_token_counting_utils import (
    enable_streaming_usage_for_openai,
    get_streaming_usage_config_for_provider,
    validate_streaming_usage_support,
)

from camel.models import OpenAIModel
from camel.types import ModelType

load_dotenv()


def basic_streaming_example():
    """
    Basic example showing streaming token counting with OpenAI.
    """
    print("=== Basic Streaming Token Counting Example ===")

    messages = [
        {
            "role": "user",
            "content": "Write a short poem about artificial intelligence.",
        }
    ]

    base_config = {"stream": True, "temperature": 0.7, "max_tokens": 150}

    # Enable streaming usage for OpenAI
    streaming_config = enable_streaming_usage_for_openai(base_config)
    print(f"Streaming config: {streaming_config}")

    # Validate configuration
    is_valid = validate_streaming_usage_support("openai", streaming_config)
    print(f"Configuration valid: {is_valid}")

    # Create model with streaming configuration
    model = OpenAIModel(
        model_type=ModelType.GPT_4O_MINI, model_config_dict=streaming_config
    )

    print("\nMaking streaming request...")
    response = model.run(messages)

    counter = model.token_counter
    usage = counter.extract_usage_from_streaming_response(response)

    if usage:
        print("\n✅ Successfully extracted usage from stream:")
        print(f"   Prompt tokens: {usage['prompt_tokens']}")
        print(f"   Completion tokens: {usage['completion_tokens']}")
        print(f"   Total tokens: {usage['total_tokens']}")
    else:
        print("\n❌ No usage data available in stream")


async def async_streaming_example():
    """
    Example showing asynchronous streaming token counting.
    """
    print("\n=== Async Streaming Token Counting Example ===")

    messages = [
        {
            "role": "user",
            "content": "Explain quantum computing in simple terms.",
        }
    ]

    # Configure for async streaming
    config = get_streaming_usage_config_for_provider(
        "openai", {"stream": True, "temperature": 0.5, "max_tokens": 200}
    )

    model = OpenAIModel(
        model_type=ModelType.GPT_4O_MINI, model_config_dict=config
    )

    print("Making async streaming request...")

    # Make async streaming request
    response = await model.arun(messages)

    # Extract usage from async stream
    counter = model.token_counter
    usage = await counter.extract_usage_from_async_streaming_response(response)

    if usage:
        print("\n✅ Successfully extracted usage from async stream:")
        print(f"   Prompt tokens: {usage['prompt_tokens']}")
        print(f"   Completion tokens: {usage['completion_tokens']}")
        print(f"   Total tokens: {usage['total_tokens']}")
    else:
        print("\n❌ No usage data available in async stream")


def multi_provider_example():
    """
    Example showing streaming token counting across different providers.
    """
    print("\n=== Multi-Provider Streaming Example ===")

    providers = ["openai", "anthropic", "mistral", "litellm"]
    base_config = {"stream": True, "temperature": 0.7}

    for provider in providers:
        print(f"\n--- {provider.upper()} Configuration ---")

        provider_config = get_streaming_usage_config_for_provider(
            provider, base_config
        )
        print(f"Config: {provider_config}")

        is_valid = validate_streaming_usage_support(provider, provider_config)
        print(f"Valid: {is_valid}")

        if provider == "openai":
            print("Note: OpenAI requires stream_options.include_usage = true")
        elif provider == "anthropic":
            print(
                "Note: Anthropic includes usage by default in message events"
            )
        elif provider == "mistral":
            print("Note: Mistral includes usage by default in final chunk")
        elif provider == "litellm":
            print("Note: LiteLLM proxies provider-specific usage data")


def error_handling_example():
    """
    Example showing robust error handling for streaming token counting.
    """
    print("\n=== Error Handling Example ===")

    def robust_streaming_usage_extraction(counter, stream):
        """Robust usage extraction with fallback handling."""
        try:
            usage = counter.extract_usage_from_streaming_response(stream)
            if usage:
                return usage
            else:
                print(
                    "⚠️  No usage data in stream, this is expected for some "
                    "configurations"
                )
                return None
        except Exception as e:
            print(f"❌ Failed to extract streaming usage: {e}")
            return None

    config_without_usage = {"stream": True, "temperature": 0.7}

    model = OpenAIModel(
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=config_without_usage,
    )

    messages = [{"role": "user", "content": "Hello!"}]

    print("Making request without stream_options (no usage expected)...")
    response = model.run(messages)

    counter = model.token_counter
    usage = robust_streaming_usage_extraction(counter, response)

    if usage:
        print(f"Unexpected usage data: {usage}")
    else:
        print("✅ Handled missing usage data gracefully")


def comparison_example():
    """
    Example comparing manual vs native token counting approaches.
    """
    print("\n=== Manual vs Native Token Counting Comparison ===")

    messages = [
        {
            "role": "user",
            "content": "Compare manual and native token counting approaches.",
        }
    ]

    print("\n--- Method 1: Native Streaming Usage (Recommended) ---")

    native_config = enable_streaming_usage_for_openai(
        {"stream": True, "temperature": 0.7, "max_tokens": 100}
    )

    model_native = OpenAIModel(
        model_type=ModelType.GPT_4O_MINI, model_config_dict=native_config
    )

    response_native = model_native.run(messages)
    counter = model_native.token_counter
    native_usage = counter.extract_usage_from_streaming_response(
        response_native
    )

    if native_usage:
        print(f"✅ Native usage: {native_usage['total_tokens']} tokens")
    else:
        print("❌ Native usage extraction failed")

    print("\n--- Method 2: Manual Counting (Deprecated) ---")

    manual_tokens = counter.count_tokens_from_messages(messages)
    print(f"⚠️  Manual count (input only): {manual_tokens} tokens")
    print(
        "Note: Manual counting only covers input tokens, not completion tokens"
    )

    # Show the difference
    if native_usage:
        print("\n📊 Comparison:")
        print(f"   Native total: {native_usage['total_tokens']} tokens")
        print(f"   Manual input: {manual_tokens} tokens")
        print(f"   Completion: {native_usage['completion_tokens']} tokens")
        print("   ✅ Native method provides complete and accurate data")


def integration_example():
    """
    Example showing integration with existing CAMEL workflows.
    """
    print("\n=== Integration with CAMEL Workflows ===")

    def create_streaming_agent_with_usage_tracking():
        """Create an agent with streaming and usage tracking enabled."""

        config = enable_streaming_usage_for_openai(
            {"stream": True, "temperature": 0.8, "max_tokens": 200}
        )

        model = OpenAIModel(
            model_type=ModelType.GPT_4O_MINI, model_config_dict=config
        )

        return model

    def process_conversation_with_usage_tracking(model, conversation):
        """Process a conversation and track token usage."""
        total_usage = {
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0,
        }

        for i, message_content in enumerate(conversation):
            print(f"\n--- Turn {i+1} ---")
            print(f"User: {message_content}")

            messages = [{"role": "user", "content": message_content}]
            response = model.run(messages)
            counter = model.token_counter
            usage = counter.extract_usage_from_streaming_response(response)

            if usage:
                for key in total_usage:
                    total_usage[key] += usage[key]

                print(f"Turn usage: {usage['total_tokens']} tokens")
            else:
                print("No usage data for this turn")

        return total_usage

    conversation = [
        "What is machine learning?",
        "How does it differ from traditional programming?",
        "Give me a simple example.",
    ]

    agent = create_streaming_agent_with_usage_tracking()
    total_usage = process_conversation_with_usage_tracking(agent, conversation)

    print("\n📊 Total Conversation Usage:")
    print(f"   Prompt tokens: {total_usage['prompt_tokens']}")
    print(f"   Completion tokens: {total_usage['completion_tokens']}")
    print(f"   Total tokens: {total_usage['total_tokens']}")


def main():
    """
    Run all streaming token counting examples.
    """
    print("🚀 Streaming Token Counting Examples")
    print("=" * 50)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key to run these examples:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        return

    # Verify API key is not empty
    if not api_key.strip():
        print("❌ OPENAI_API_KEY environment variable is empty")
        print("Please set a valid OpenAI API key:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        return

    print(f"✅ OpenAI API key detected (length: {len(api_key)} characters)")

    try:
        # Run synchronous examples
        basic_streaming_example()
        multi_provider_example()
        error_handling_example()
        comparison_example()
        integration_example()

        # Run asynchronous example
        print("\n" + "=" * 50)
        asyncio.run(async_streaming_example())

        print("\n" + "=" * 50)
        print("✅ All examples completed successfully!")
        print("\nKey Takeaways:")
        print("1. Enable stream_options.include_usage for OpenAI streaming")
        print(
            "2. Use extract_usage_from_streaming_response() for accurate "
            "counts"
        )
        print("3. Handle missing usage data gracefully")
        print("4. Prefer native extraction over manual counting")
        print("5. Validate configuration before making requests")

    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        print("Make sure you have:")
        print("1. Valid OpenAI API key")
        print("2. Required dependencies installed")
        print("3. Proper network connectivity")


if __name__ == "__main__":
    main()
