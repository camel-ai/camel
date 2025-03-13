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

from camel.extractors import (
    BoxedStrategy,
    Extractor,
    GraphDictionaryStrategy,
    GraphListStrategy,
    GraphNodeListStrategy,
    MathValueStrategy,
)
from camel.logger import get_logger

logger = get_logger(__name__)


def create_graph_theory_extractor(
    _cache_templates=True,
    max_cache_size=5000,
    extraction_timeout=60.0,
    _batch_size=20,
    _monitoring_interval=10.0,
    _cpu_threshold=90.0,
    _memory_threshold=90.0,
) -> Extractor:
    r"""Create an extractor for graph theory and discrete math problems."""
    # Create a pipeline with multiple strategies in a single stage
    # This way, each strategy will be tried until one succeeds
    pipeline = [
        [
            BoxedStrategy(),
            GraphDictionaryStrategy(),
            GraphListStrategy(),
            GraphNodeListStrategy(),
            MathValueStrategy(),
        ]
    ]

    return Extractor(
        pipeline=pipeline,
        cache_templates=_cache_templates,
        max_cache_size=max_cache_size,
        extraction_timeout=extraction_timeout,
        batch_size=_batch_size,
        monitoring_interval=_monitoring_interval,
        cpu_threshold=_cpu_threshold,
        memory_threshold=_memory_threshold,
        default_value=None,
    )


async def example_graph_dictionary_extraction():
    r"""Demonstrate graph dictionary extraction."""
    print("\n=== Example 1: Graph Dictionary Extraction ===")

    # Example LLM response with a graph dictionary
    llm_response = r"""{0: {1: 2, 2: 2, 3: 1},
 1: {0: 2, 2: 2, 3: 1},
 2: {0: 2, 1: 2, 3: 1},
 3: {0: 1, 1: 1, 2: 1}}"""

    # Create a graph theory extractor
    extractor = create_graph_theory_extractor()

    # Set up the extractor
    await extractor.setup()

    try:
        # Extract the graph dictionary
        result = await extractor.extract(llm_response)

        print(f"LLM Response: {llm_response}")
        print(f"Extracted graph dictionary: {result}")

        # Parse the result to get the actual dictionary
        try:
            if result:
                parsed_dict = ast.literal_eval(result)
                print(f"Parsed dictionary: {parsed_dict}")
            else:
                print("No result extracted")
        except (SyntaxError, ValueError) as e:
            print(f"Error parsing result: {e}")

    finally:
        # Clean up the extractor
        await extractor.cleanup()


async def example_graph_list_extraction():
    r"""Demonstrate graph list extraction."""
    print("\n=== Example 2: Graph List Extraction ===")

    # Example LLM response with a graph partition list
    llm_response = r"""[[0, 1], [2, 3, 4, 5]]"""

    # Create a graph theory extractor
    extractor = create_graph_theory_extractor()

    # Set up the extractor
    await extractor.setup()

    try:
        # Extract the graph list
        result = await extractor.extract(llm_response)

        print(f"LLM Response: {llm_response}")
        print(f"Extracted graph list: {result}")

        # Parse the result to get the actual list
        try:
            if result:
                parsed_list = ast.literal_eval(result)
                print(f"Parsed list: {parsed_list}")
            else:
                print("No result extracted")
        except (SyntaxError, ValueError) as e:
            print(f"Error parsing result: {e}")

    finally:
        # Clean up the extractor
        await extractor.cleanup()


async def example_node_list_extraction():
    r"""Demonstrate node list extraction from text."""
    print("\n=== Example 3: Node List Extraction ===")

    # Example LLM response with a text list of nodes
    llm_response = r"""Eric."""

    # Create a graph theory extractor
    extractor = create_graph_theory_extractor()

    # Set up the extractor
    await extractor.setup()

    try:
        # Extract the node list
        result = await extractor.extract(llm_response)

        print(f"LLM Response: {llm_response}")
        print(f"Extracted node list: {result}")

        # Parse the result to get the actual list
        try:
            if result:
                parsed_list = ast.literal_eval(result)
                print(f"Parsed list: {parsed_list}")
            else:
                print("No result extracted")
        except (SyntaxError, ValueError) as e:
            print(f"Error parsing result: {e}")

    finally:
        # Clean up the extractor
        await extractor.cleanup()


async def example_math_value_extraction():
    r"""Demonstrate mathematical value extraction."""
    print("\n=== Example 4: Math Value Extraction ===")

    # Example LLM response with a mathematical value
    llm_response = r"""inf"""

    # Create a graph theory extractor
    extractor = create_graph_theory_extractor()

    # Set up the extractor
    await extractor.setup()

    try:
        # Extract the mathematical value
        result = await extractor.extract(llm_response)

        print(f"LLM Response: {llm_response}")
        print(f"Extracted math value: {result}")

        if not result:
            print("No result extracted")

    finally:
        # Clean up the extractor
        await extractor.cleanup()


async def example_boxed_extraction():
    r"""Demonstrate extraction from boxed content."""
    print("\n=== Example 5: Boxed Content Extraction ===")

    # Example LLM response with boxed content
    llm_response = r"""\boxed{
    {0: {1: 2, 2: 2, 3: 1},
     1: {0: 2, 2: 2, 3: 1},
     2: {0: 2, 1: 2, 3: 1},
     3: {0: 1, 1: 1, 2: 1}}
}"""

    # Create a graph theory extractor
    extractor = create_graph_theory_extractor()

    # Set up the extractor
    await extractor.setup()

    try:
        # Extract from boxed content
        result = await extractor.extract(llm_response)

        print(f"LLM Response: {llm_response}")
        print(f"Extracted result: {result}")

        # Parse the result
        try:
            if result:
                parsed_result = ast.literal_eval(result)
                print(f"Parsed result: {parsed_result}")
            else:
                print("No result extracted")
        except (SyntaxError, ValueError) as e:
            print(f"Error parsing result: {e}")

    finally:
        # Clean up the extractor
        await extractor.cleanup()


async def main():
    r"""Run all examples."""
    print("=== Graph Math Strategies Examples ===")

    await example_graph_dictionary_extraction()
    await example_graph_list_extraction()
    await example_node_list_extraction()
    await example_math_value_extraction()
    await example_boxed_extraction()

    print("\nAll examples completed.")


if __name__ == "__main__":
    asyncio.run(main())
