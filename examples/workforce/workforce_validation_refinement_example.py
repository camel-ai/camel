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
import os

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.societies import Workforce
from camel.tasks import Task
from camel.toolkits import ArxivToolkit
from camel.types import ModelPlatformType


async def main():
    # Create a model instance for the workforce agents

    model = ModelFactory.create(
        model_platform=ModelPlatformType.AZURE,
        model_type="gpt-4.1",
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        url=os.getenv("AZURE_OPENAI_BASE_URL"),
        api_version="2024-12-01-preview",
    )
    tools = ArxivToolkit().get_tools()

    # Create workforce agents
    coordinator_agent = ChatAgent(model=model)
    task_agent = ChatAgent(model=model)

    # Create worker agents - these will work in parallel
    researcher1 = ChatAgent("You are AI researcher", model=model, tools=tools)

    researcher2 = ChatAgent("You are ML researcher", model=model, tools=tools)

    researcher3 = ChatAgent(
        "You are CS engineer researcher", model=model, tools=tools
    )

    # Initialize Workforce with validation and refinement enabled
    workforce = Workforce(
        description="Research Team with Validation",
        coordinator_agent=coordinator_agent,
        task_agent=task_agent,
        max_refinement_iterations=2,  # Allow up to 2 refinement iterations
    )
    workforce.add_single_agent_worker("AI researcher", researcher1)
    workforce.add_single_agent_worker("ML researcher", researcher2)
    workforce.add_single_agent_worker("CS researcher", researcher3)

    # Create a task that will be decomposed into parallel subtasks
    # The task explicitly requires 5 unique papers
    task = Task(
        content=(
            "Find 5 unique research papers on NLP systems. "
            "For each paper, provide: title, authors, year, and a brief "
        ),
        id="research_task_1",
    )

    print("=" * 80)
    print("WORKFORCE VALIDATION AND ITERATIVE REFINEMENT EXAMPLE")
    print("=" * 80)
    print("\nTask:", task.content)
    print("\nThe workforce will:")
    print("1. Decompose the task into parallel subtasks")
    print("2. Execute subtasks in parallel")
    print("3. Validate and deduplicate results")
    print("4. If duplicates found or requirements not met, create")
    print("   additional targeted subtasks")
    print(
        "5. Repeat until requirements are satisfied or max iterations reached"
    )
    print("\n" + "=" * 80 + "\n")

    try:
        # Process the task with the workforce
        result = await workforce.process_task_async(task)

        print("\n" + "=" * 80)
        print("FINAL RESULT")
        print("=" * 80)
        print("\nTask State:", result.state.value)
        print("\nResult:")
        print(result.result)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Stop the workforce
        workforce.stop()


if __name__ == "__main__":
    # Run the main example
    asyncio.run(main())

    # Uncomment to run additional examples:
    # asyncio.run(simple_deduplication_example())
    # asyncio.run(disable_validation_example())
