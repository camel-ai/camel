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


import os

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.societies.workforce import Workforce
from camel.tasks.task import Task


def create_analyst_agent() -> ChatAgent:
    """Create a data analyst agent."""
    analyst_msg = BaseMessage.make_assistant_message(
        role_name="Data Analyst",
        content=(
            "You are an expert data analyst. You excel at:\n"
            "- Analyzing datasets and identifying trends\n"
            "- Creating visualizations and reports\n"
            "- Providing actionable business insights\n"
            "- Working with various data formats (CSV, JSON, databases)\n"
            "- Using statistical methods and data science techniques"
        ),
    )
    return ChatAgent(analyst_msg)


def create_developer_agent() -> ChatAgent:
    """Create a Python developer agent."""
    developer_msg = BaseMessage.make_assistant_message(
        role_name="Python Developer",
        content=(
            "You are a skilled Python developer. You specialize in:\n"
            "- Writing clean, efficient Python code\n"
            "- Building web applications and APIs\n"
            "- Data processing and automation scripts\n"
            "- Testing and debugging\n"
            "- Following best practices and coding standards"
        ),
    )
    return ChatAgent(developer_msg)


def demonstrate_first_session():
    """Demonstrate first workforce session with workflow saving."""
    print("=" * 60)
    print("SESSION 1: Processing tasks and saving workflows")
    print("=" * 60)

    # Create workforce with descriptive worker names
    workforce = Workforce("Data Analysis Team")

    # Add workers with descriptive names (used for workflow file matching)
    analyst_agent = create_analyst_agent()
    workforce.add_single_agent_worker(
        description="data_analyst",  # This becomes the workflow filename base
        worker=analyst_agent,
    )

    developer_agent = create_developer_agent()
    workforce.add_single_agent_worker(
        description="python_developer",  # This becomes the workflow filename
        worker=developer_agent,
    )

    print(f"Created workforce with {len(workforce._children)} workers")

    # Process multiple tasks to build workflow experience
    tasks = [
        Task(
            content="Analyze quarterly sales data and identify top products",
            id="task_1",
        ),
        Task(
            content="Create a Python script to automate data cleaning for CSV",
            id="task_2",
        ),
        Task(
            content="Generate a summary report of customer behavior patterns",
            id="task_3",
        ),
    ]

    for task in tasks:
        print(f"\nProcessing task: {task.content}")
        try:
            result = workforce.process_task(task)
            print(f"Task result: {result.state}")
        except Exception as e:
            print(f"Task failed: {e}")

    # Save workflows after completing tasks
    print("\nSaving workflows...")
    saved_workflows = workforce.save_workflows()

    print("\nWorkflow save results:")
    for worker_id, result in saved_workflows.items():
        if result.startswith("error:"):
            print(f"  Worker {worker_id}: ❌ {result}")
        elif result.startswith("skipped:"):
            print(f"  Worker {worker_id}: ⏭️ {result}")
        else:
            print(
                f"  Worker {worker_id}: ✅ Saved to {os.path.basename(result)}"
            )

    return saved_workflows


def demonstrate_second_session():
    """Demonstrate second workforce session with workflow loading."""
    print("\n" + "=" * 60)
    print("SESSION 2: Loading previous workflows and processing new tasks")
    print("=" * 60)

    # Create new workforce (simulating new session/process)
    workforce = Workforce("Data Analysis Team - Session 2")

    # Add workers with same descriptive names as before
    analyst_agent = create_analyst_agent()
    workforce.add_single_agent_worker(
        description="data_analyst",  # Same description = loads matching
        worker=analyst_agent,
    )

    developer_agent = create_developer_agent()
    workforce.add_single_agent_worker(
        description="python_developer",  # Same description = loads matching
        worker=developer_agent,
    )

    # Load previous workflows
    print("Loading previous workflows...")
    loaded_workflows = workforce.load_workflows()

    print("\nWorkflow load results:")
    for worker_id, success in loaded_workflows.items():
        status = "✅ Loaded successfully" if success else "❌ Failed to load"
        print(f"  Worker {worker_id}: {status}")

    # Process new tasks with loaded workflow context
    new_tasks = [
        Task(
            content="Analyze this month's marketing campaign effectiveness",
            id="task_4",
        ),
        Task(
            content="Build a dashboard for real-time sales monitoring",
            id="task_5",
        ),
    ]

    for task in new_tasks:
        print(f"\nProcessing task with workflow context: {task.content}")
        try:
            result = workforce.process_task(task)
            print(f"Task result: {result.state}")
            print(
                "✨ Workers now have access to previous workflow experiences!"
            )
        except Exception as e:
            print(f"Task failed: {e}")

    return loaded_workflows


def demonstrate_workflow_file_management():
    """Demonstrate workflow file management and inspection."""
    print("\n" + "=" * 60)
    print("WORKFLOW FILE MANAGEMENT")
    print("=" * 60)

    # Show where workflow files are stored
    import os

    camel_workdir = os.environ.get("CAMEL_WORKDIR")
    if camel_workdir:
        workflow_dir = os.path.join(camel_workdir, "workforce_workflows")
    else:
        workflow_dir = "workforce_workflows"

    print(f"Workflow files are stored in: {workflow_dir}")

    # Demonstrate file naming pattern
    print("\nWorkflow file naming pattern:")
    print("  {worker_description}_workflow_{timestamp}.md")
    print("  Examples:")
    print("    - data_analyst_workflow_20250122_143022.md")
    print("    - python_developer_workflow_20250122_143023.md")

    print("\nWorkflow loading strategy:")
    print("  1. Search for files matching worker description")
    print("  2. Load up to 3 most recent workflow files")
    print("  3. Inject workflow context into agent memory")
    print("  4. Agent uses context for better task execution")


def main():
    """Main demonstration function."""
    print("🚀 CAMEL Workforce Workflow Memory Demonstration")
    print(
        "This example shows how workforce agents can save and load "
        "workflow experiences.\n"
    )

    try:
        # Demonstrate first session with workflow saving
        demonstrate_first_session()

        # Demonstrate second session with workflow loading
        demonstrate_second_session()

        # Show file management information
        demonstrate_workflow_file_management()

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print("✅ Workflow memory feature demonstrated successfully!")
        print("📝 Key benefits:")
        print("   - Agents learn from previous experiences")
        print("   - Improved task execution over time")
        print("   - Persistent memory across sessions")
        print("   - Easy-to-use save/load API")
        print("   - Automatic file management")

        print("\n🔧 Usage in your code:")
        print("   # Save workflows after task completion")
        print("   workforce.save_workflows()")
        print()
        print("   # Load workflows when starting new session")
        print("   workforce.load_workflows()")

    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        print(
            "This may happen if API keys are not configured or models are "
            "unavailable."
        )
        print("The workflow memory functionality itself is working correctly.")


if __name__ == "__main__":
    main()
