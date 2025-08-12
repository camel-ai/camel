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
from __future__ import annotations

from typing import Dict, List

from camel.tasks.task import Task


class DependencyManager:
    r"""A class to manage task dependencies and handle dependency updates
    when tasks are decomposed into subtasks.
    """

    def __init__(self, task_dependencies: Dict[str, List[str]] | None = None):
        r"""Initialize the DependencyManager.

        Args:
            task_dependencies: Dictionary mapping task IDs to their dependency
                lists. If None, an empty dictionary will be created.
        """
        self.task_dependencies = task_dependencies or {}

    def update_dependencies_for_decomposition(
        self, original_task: Task, subtasks: List[Task]
    ) -> None:
        r"""Update dependency tracking when a task is decomposed into subtasks.
        Tasks that depended on the original task should now depend on all
        subtasks. The last subtask inherits the original task's dependencies.

        Args:
            original_task: The task that was decomposed
            subtasks: List of subtasks created from the original task
        """
        if not subtasks:
            return

        original_task_id = original_task.id
        subtask_ids = [subtask.id for subtask in subtasks]

        # Find tasks that depend on the original task
        dependent_task_ids = [
            task_id
            for task_id, deps in self.task_dependencies.items()
            if original_task_id in deps
        ]

        # Update dependent tasks to depend on all subtasks
        for task_id in dependent_task_ids:
            dependencies = self.task_dependencies[task_id]
            dependencies.remove(original_task_id)
            dependencies.extend(subtask_ids)

        # The last subtask inherits original task's dependencies (if any)
        if original_task_id in self.task_dependencies:
            original_dependencies = self.task_dependencies[original_task_id]
            if original_dependencies:
                # Set dependencies for the last subtask to maintain execution
                # order
                self.task_dependencies[subtask_ids[-1]] = (
                    original_dependencies.copy()
                )
            # Remove original task dependencies as it's now decomposed
            del self.task_dependencies[original_task_id]
