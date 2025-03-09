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
import asyncio

from camel.extractors.python_strategies.list_extractor import ListExtractor


async def example_basic_extraction():
    """Demonstrate basic extraction using the extract method."""
    print("\n=== Example 1: Basic extraction ===")

    # Example LLM response with a list in \boxed{} format
    llm_response = r"\boxed{[3, 1, 2, 'apple']}"

    # Create an extractor instance with default parameters
    extractor = ListExtractor()

    # Set up the extractor
    await extractor.setup()

    # Extract the list
    result = await extractor.extract(llm_response)

    print(f"LLM Response: {llm_response}")
    print(f"Extracted list string: {result}")

    # Clean up the extractor
    await extractor.cleanup()


async def example_multiple_extractions():
    """Demonstrate multiple extractions using the same extractor instance."""
    print("\n=== Example 2: Multiple extractions ===")

    # Create an extractor instance
    extractor = ListExtractor()

    # Set up the extractor
    await extractor.setup()

    # Example responses
    responses = [
        r"\boxed{[5, 4, 6]}",
        r"\boxed{['cat', 'dog', 'bird']}",
        r"\boxed{[10, 20, 30]}",
        r"This response has no list",
    ]

    for i, response in enumerate(responses, 1):
        print(f"\nProcessing response {i}: {response}")

        # Extract the list
        result = await extractor.extract(response)

        print(f"Extracted list string: {result}")

    # Clean up the extractor
    await extractor.cleanup()


async def main():
    """Run all examples."""
    print("=== ListExtractor Examples ===")

    await example_basic_extraction()
    await example_multiple_extractions()

    print("\nAll examples completed.")


if __name__ == "__main__":
    asyncio.run(main())

"""
=== ListExtractor Examples ===

=== Example 1: Basic extraction ===
LLM Response: \boxed{[3, 1, 2, 'apple']}
Extracted list string: [1, 2, 3, 'apple']
Parsed list: [1, 2, 3, 'apple']

=== Example 2: Multiple extractions ===

Processing response 1: \boxed{[5, 4, 6]}
Extracted list string: [4, 5, 6]
Parsed list: [4, 5, 6]

Processing response 2: \boxed{['cat', 'dog', 'bird']}
Extracted list string: ['bird', 'cat', 'dog']
Parsed list: ['bird', 'cat', 'dog']

Processing response 3: \boxed{[10, 20, 30]}
Extracted list string: [10, 20, 30]
Parsed list: [10, 20, 30]

Processing response 4: This response has no list
Extracted list string: []
Parsed list: []

All examples completed.
"""
