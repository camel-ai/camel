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
import ast
import asyncio

from camel.extractors.base import BaseExtractor
from camel.extractors.python_strategies import (
    BoxedStrategy,
    PythonDictStrategy,
    PythonListStrategy,
)
from camel.logger import get_logger

logger = get_logger(__name__)


def create_list_extractor(
    _cache_templates=True,
    max_cache_size=5000,
    extraction_timeout=60.0,
    _batch_size=20,
    _monitoring_interval=10.0,
    _cpu_threshold=90.0,
    _memory_threshold=90.0,
) -> "BaseExtractor":
    r"""Create an extractor for Python lists."""
    # Create a pipeline with two stages
    pipeline = [
        [BoxedStrategy()],  # Stage 1: Extract boxed content
        [PythonListStrategy()],  # Stage 2: Extract and normalize Python list
    ]

    return BaseExtractor(
        pipeline=pipeline,
        cache_templates=_cache_templates,
        max_cache_size=max_cache_size,
        extraction_timeout=extraction_timeout,
        batch_size=_batch_size,
        monitoring_interval=_monitoring_interval,
        cpu_threshold=_cpu_threshold,
        memory_threshold=_memory_threshold,
        default_value="[]",
    )


def create_dict_extractor(
    _cache_templates=True,
    max_cache_size=5000,
    extraction_timeout=60.0,
    _batch_size=20,
    _monitoring_interval=10.0,
    _cpu_threshold=90.0,
    _memory_threshold=90.0,
) -> "BaseExtractor":
    r"""Create an extractor for Python dictionaries."""
    # Create a pipeline with two stages
    pipeline = [
        [BoxedStrategy()],  # Stage 1: Extract boxed content
        [PythonDictStrategy()],  # Stage 2: Extract and normalize Python dict
    ]

    return BaseExtractor(
        pipeline=pipeline,
        cache_templates=_cache_templates,
        max_cache_size=max_cache_size,
        extraction_timeout=extraction_timeout,
        batch_size=_batch_size,
        monitoring_interval=_monitoring_interval,
        cpu_threshold=_cpu_threshold,
        memory_threshold=_memory_threshold,
        default_value="{}",
    )


async def example_list_extraction():
    r"""Demonstrate list extraction."""
    print("\n=== Example 1: List extraction ===")

    # Example LLM response with a list in \boxed{} format
    llm_response = r"\boxed{[3, 1, 2, 'apple']}"

    # Create a list extractor
    extractor = create_list_extractor()

    # Set up the extractor
    await extractor.setup()

    try:
        # Extract the list
        result = await extractor.extract(llm_response)

        print(f"LLM Response: {llm_response}")
        print(f"Extracted list string: {result}")

        # Parse the result to get the actual list
        try:
            parsed_list = ast.literal_eval(result)
            print(f"Parsed list: {parsed_list}")
        except (SyntaxError, ValueError) as e:
            print(f"Error parsing result: {e}")

    finally:
        # Clean up the extractor
        await extractor.cleanup()


async def example_dict_extraction():
    r"""Demonstrate dictionary extraction."""
    print("\n=== Example 2: Dictionary extraction ===")

    # Example LLM response with a dictionary in \boxed{} format
    llm_response = r"\boxed{{'apple': 5, 'banana': 3, 'cherry': 8}}"

    # Create a dictionary extractor
    extractor = create_dict_extractor()

    # Set up the extractor
    await extractor.setup()

    try:
        # Extract the dictionary
        result = await extractor.extract(llm_response)

        print(f"LLM Response: {llm_response}")
        print(f"Extracted dictionary string: {result}")

        # Parse the result to get the actual dictionary
        try:
            parsed_dict = ast.literal_eval(result)
            print(f"Parsed dictionary: {parsed_dict}")
        except (SyntaxError, ValueError) as e:
            print(f"Error parsing result: {e}")

    finally:
        # Clean up the extractor
        await extractor.cleanup()


async def main():
    r"""Run all examples."""
    print("=== Python Strategies Examples ===")

    await example_list_extraction()
    await example_dict_extraction()

    print("\nAll examples completed.")


if __name__ == "__main__":
    asyncio.run(main())

"""
===============================================================================
=== Python Strategies Examples ===

=== Example 1: List extraction ===
LLM Response: \boxed{[3, 1, 2, 'apple']}
Extracted list string: [1, 2, 3, 'apple']
Parsed list: [1, 2, 3, 'apple']

=== Example 2: Dictionary extraction ===
LLM Response: \boxed{{'apple': 5, 'banana': 3, 'cherry': 8}}
Extracted dictionary string: {'apple': 5, 'banana': 3, 'cherry': 8}
Parsed dictionary: {'apple': 5, 'banana': 3, 'cherry': 8}

All examples completed.
===============================================================================
"""
