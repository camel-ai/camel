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

from camel.tasks import Task, TaskState


def demonstrate_basic_task_usage():
    # Create a simple task
    task = Task(
        content=(
            "Weng earns $12 an hour for babysitting. "
            "Yesterday, she just did 51 minutes of babysitting. "
            "How much did she earn?"
        ),
        id="0",
    )
    print("=== Basic Task ===")
    print(task.to_string())

    # Create subtasks manually (since decompose method was removed)
    sub_task_1 = Task(content="Convert 51 minutes to hours", id="0.1")
    sub_task_2 = Task(
        content="Calculate the proportion of 51 minutes to an hour", id="0.2"
    )
    sub_task_3 = Task(
        content=(
            "Multiply the proportion by Weng's hourly rate to find out "
            "how much she earned for 51 minutes of babysitting"
        ),
        id="0.3",
    )

    # Add subtasks to the main task
    task.add_subtask(sub_task_1)
    task.add_subtask(sub_task_2)
    task.add_subtask(sub_task_3)

    print("\n=== Task with Subtasks ===")
    print(task.to_string())

    # Demonstrate task state management
    print("\n=== Task State Management ===")
    print(f"Initial state: {task.state}")

    # Mark subtasks as done
    sub_task_1.set_state(TaskState.DONE)
    sub_task_1.update_result("51 minutes = 0.85 hours")

    sub_task_2.set_state(TaskState.DONE)
    sub_task_2.update_result("Proportion = 0.85/1 = 0.85")

    sub_task_3.set_state(TaskState.DONE)
    sub_task_3.update_result("Earnings = 0.85 * $12 = $10.20")

    print(f"After completing subtasks: {task.state}")
    print("\n=== Task Results ===")
    print(task.get_result())

    # Note: For advanced task management, decomposition, and composition,
    # please use the Workforce system instead of the removed Task methods.


if __name__ == "__main__":
    demonstrate_basic_task_usage()

    print("\n" + "=" * 80)
    print("NOTE: This example demonstrates basic Task functionality.")
    print("For advanced features like task decomposition, composition,")
    print("and management, please use the Workforce system.")
    print("=" * 80)
