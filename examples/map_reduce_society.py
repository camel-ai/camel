# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
"""
MapReduce Agent Society Example
===============================

This example demonstrates how to use the MapReduceSociety to decompose a
complex research task into independent sub-tasks, process them in parallel
with multiple agents, and then synthesize the results into a single
comprehensive response.

The MapReduce pattern is useful for:
  - Research tasks that can be split by topic/aspect
  - Data analysis across multiple dimensions
  - Document summarization from multiple sources
  - Any task that benefits from parallel processing and aggregation

Usage:
    Set your GROQ_API_KEY environment variable, then run:
    $ python examples/map_reduce_society.py
"""

from camel.models import ModelFactory
from camel.societies import MapReduceSociety
from camel.types import ModelPlatformType, ModelType


def main():
    # Create a Groq model backend
    model = ModelFactory.create(
        model_platform=ModelPlatformType.GROQ,
        model_type=ModelType.GROQ_LLAMA_3_3_70B,
    )

    # Create a MapReduce society with 3 mapper agents
    society = MapReduceSociety(
        task_prompt=(
            "Analyze the impact of artificial intelligence on three "
            "sectors: healthcare, education, and finance. For each sector, "
            "discuss current applications, potential benefits, risks, and "
            "future outlook."
        ),
        num_mappers=3,
        mapper_role_name="Industry Research Analyst",
        reducer_role_name="Senior Strategy Consultant",
        model=model,
    )

    print("=" * 60)
    print("MapReduce Agent Society")
    print("=" * 60)
    print(f"\nTask: {society.task_prompt}")
    print(f"Number of mapper agents: {society.num_mappers}")
    print(f"Mapper role: {society.mapper_role_name}")
    print(f"Reducer role: {society.reducer_role_name}")
    print("\nRunning MapReduce pipeline...")
    print("-" * 60)

    # Run the full pipeline
    result = society.step()

    # Display sub-tasks
    print("\n📋 Sub-tasks (from splitter):")
    for i, task in enumerate(result.info['sub_tasks'], 1):
        print(f"  {i}. {task}")

    # Display mapper results (truncated)
    print("\n📊 Mapper Results:")
    for i, res in enumerate(result.info['mapper_results'], 1):
        preview = res[:200] + "..." if len(res) > 200 else res
        print(f"\n  Mapper {i}:\n  {preview}")

    # Display final result
    print("\n" + "=" * 60)
    print("🎯 Final Synthesized Result:")
    print("=" * 60)
    print(result.msg.content)


if __name__ == "__main__":
    main()
