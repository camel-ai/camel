# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from camel.tasks.task import (
    FunctionToolState,
    FunctionToolTransition,
    Task,
    TaskManagerWithState,
)
from camel.toolkits.toolkits_manager import ToolkitManager

if __name__ == "__main__":
    # Define subtasks with descriptive content and unique IDs
    tasks = [
        Task(content="Search for suitable phone", id="1"),
        Task(content="Place phone order", id="2"),
        Task(content="Make payment", id="3"),
    ]

    # Define task states with specific tools from the ToolkitManager
    states = [
        FunctionToolState(
            name="SearchPhone",
            tools_space=ToolkitManager().search_toolkits('search'),
        ),
        FunctionToolState(
            name="PlaceOrder",
            tools_space=ToolkitManager().search_toolkits('math'),
        ),
        FunctionToolState(
            name="MakePayment",
            tools_space=ToolkitManager().search_toolkits('img'),
        ),
        FunctionToolState(name="Done"),
    ]

    # Define task state transitions with trigger, source, and destination
    transitions = [
        FunctionToolTransition(
            trigger=tasks[0], source=states[0], dest=states[1]
        ),
        FunctionToolTransition(
            trigger=tasks[1], source=states[1], dest=states[2]
        ),
        FunctionToolTransition(
            trigger=tasks[2], source=states[2], dest=states[3]
        ),
    ]

    # Initialize the Task Manager, starting with the initial state of
    # "SearchPhone"
    task_manager = TaskManagerWithState(
        task=tasks[0],
        initial_state=states[0],
        states=states,
        transitions=transitions,
    )

    # Task execution loop until reaching the "Done" state
    while task_manager.current_state != states[-1]:
        # Print the current state and available tools
        print(f"Current State: {task_manager.current_state}")
        print(f"Current Tools: {task_manager.get_current_tools()}")

        # Retrieve and execute the current task if available
        current_task = task_manager.current_task
        if current_task:
            print(f"Executing Task: {current_task.content}")
            # Simulate task execution and update task result
            current_task.update_result('Subtask completed!')
            print(f"Task Result: {current_task.result}")

        # Print updated state after task completion
        print(f"Updated State: {task_manager.current_state}")
