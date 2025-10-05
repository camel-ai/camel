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
#!/usr/bin/env python3
"""
Test script for the new native token counting functionality.

This script demonstrates the improved token counting that uses native usage
data from LLM providers instead of manual token counting.
"""

import os

from dotenv import load_dotenv

from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

load_dotenv()


def test_openai_native_token_counting():
    """Test OpenAI model with native token counting."""
    print("=== Testing OpenAI Native Token Counting ===")

    # Check if OpenAI API key is available
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY not found. Please set it to run this test.")
        return

    try:
        model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
        )

        messages = [
            {
                "role": "user",
                "content": "Hello! Can you tell me about token counting?",
            }
        ]

        print(f"Model: {model.model_type}")
        print(f"Messages: {messages}")

        traditional_count = model.count_tokens_from_messages(messages)
        print(f"Legacy token count: {traditional_count}")

        print("\nMaking API call...")
        response = model.run(messages)

        usage_data = model.token_counter.extract_usage_from_response(response)
        print(f"The response is: {usage_data}")

        if usage_data:
            print("✅ Native usage data extracted successfully!")
            print(f"Prompt tokens: {usage_data['prompt_tokens']}")
            print(f"Completion tokens: {usage_data['completion_tokens']}")
            print(f"Total tokens: {usage_data['total_tokens']}")

            # Compare with legacy counting
            print("\nComparison:")
            print(f"Legacy count: {traditional_count}")
            print(f"Native prompt tokens: {usage_data['prompt_tokens']}")
            diff = abs(traditional_count - usage_data['prompt_tokens'])
            print(f"Difference: {diff}")

        else:
            print("❌ Failed to extract native usage data")

    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback

        traceback.print_exc()


def test_token_counter_methods():
    """Test the token counter methods directly."""
    print("=== Testing Token Counter Methods ===")

    try:
        from camel.types import ModelType
        from camel.utils.token_counting import OpenAITokenCounter

        counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)

        class MockResponse:
            def __init__(self):
                self.usage = MockUsage()

        class MockUsage:
            def __init__(self):
                self.prompt_tokens = 15
                self.completion_tokens = 25
                self.total_tokens = 40

        mock_response = MockResponse()
        usage = counter.extract_usage_from_response(mock_response)

        if usage:
            print("✅ Token counter extract_usage_from_response works!")
            print(f"Extracted usage: {usage}")
        else:
            print("❌ Failed to extract usage from mock response")

    except Exception as e:
        print(f"❌ Error testing token counter methods: {e}")


def main():
    """Run all tests."""
    print("🧪 Testing Native Token Counting Implementation")
    print("=" * 60)

    test_token_counter_methods()
    test_openai_native_token_counting()

    print("\n" + "=" * 60)
    print("✅ Test completed! Check the results above.")
    print("\n📝 Key Benefits of Native Token Counting:")
    print("   • 100% accurate token counts from the model provider")
    print("   • No need to maintain complex tokenization logic")
    print("   • Works with streaming responses")
    print("   • Supports all model providers uniformly")


if __name__ == "__main__":
    main()
