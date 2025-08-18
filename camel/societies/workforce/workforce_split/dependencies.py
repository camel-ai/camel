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
            task_dependencies (Dict[str, List[str]], optional): Dictionary
                mapping task IDs to their dependency lists. If None, an empty
                dictionary will be created. (default: :obj:`None`)
        """
        # Create a copy to avoid shared references
        self.task_dependencies = (task_dependencies or {}).copy()

    def get_dependencies(self) -> Dict[str, List[str]]:
        r"""Get all task dependencies.

        Returns:
            Dict[str, List[str]]: Dictionary mapping task IDs to their
            dependency lists.
        """
        return self.task_dependencies.copy()

    def set_dependencies(self, deps: Dict[str, List[str]]) -> None:
        r"""Set all task dependencies.

        Args:
            deps (Dict[str, List[str]]): Dictionary mapping task IDs to
            their dependency lists.
        """
        self.task_dependencies = deps.copy()

    def clear_dependencies(self) -> None:
        r"""Clear all task dependencies."""
        self.task_dependencies.clear()

    def add_dependency(self, task_id: str, dependency_id: str) -> None:
        r"""Add a dependency for a specific task.

        Args:
            task_id (str): The ID of the task that depends on dependency_id.
            dependency_id (str): The ID of the task that task_id depends on.
        """
        if task_id not in self.task_dependencies:
            self.task_dependencies[task_id] = []
        if dependency_id not in self.task_dependencies[task_id]:
            self.task_dependencies[task_id].append(dependency_id)

    def remove_dependency(self, task_id: str, dependency_id: str) -> None:
        r"""Remove a dependency for a specific task.

        Args:
            task_id (str): The ID of the task.
            dependency_id (str): The ID of the dependency to remove.
        """
        if task_id in self.task_dependencies:
            if dependency_id in self.task_dependencies[task_id]:
                self.task_dependencies[task_id].remove(dependency_id)
            # Clean up empty dependency lists
            if not self.task_dependencies[task_id]:
                del self.task_dependencies[task_id]

    def get_task_dependencies(self, task_id: str) -> List[str]:
        r"""Get dependencies for a specific task.

        Args:
            task_id (str): The ID of the task.

        Returns:
            List[str]: List of task IDs that this task depends on.
        """
        return self.task_dependencies.get(task_id, []).copy()

    def has_dependencies(self, task_id: str) -> bool:
        r"""Check if a task has dependencies.

        Args:
            task_id (str): The ID of the task.

        Returns:
            bool: True if the task has dependencies, False otherwise.
        """
        return task_id in self.task_dependencies and bool(
            self.task_dependencies[task_id]
        )

    def remove_task(self, task_id: str) -> None:
        r"""Remove a task and all its dependencies.

        Args:
            task_id (str): The ID of the task to remove.
        """
        # Remove the task's own dependencies
        if task_id in self.task_dependencies:
            del self.task_dependencies[task_id]

        # Remove this task from other tasks' dependency lists
        for deps in self.task_dependencies.values():
            if task_id in deps:
                deps.remove(task_id)

    def _update_dependencies_for_decomposition(
        self, original_task: Task, subtasks: List[Task]
    ) -> None:
        r"""Update dependency tracking when a task is decomposed into subtasks.
        Tasks that depended on the original task should now depend on all
        subtasks. The last subtask inherits the original task's dependencies.

        Args:
            original_task (Task): The task that was decomposed.
            subtasks (List[Task]): List of subtasks created from the original
                task.
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
