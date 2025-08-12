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

from collections import deque
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.tasks.task import Task, validate_task_content

logger = get_logger(__name__)


class TaskManager:
    """A class to manage task operations for workforce systems."""

    def __init__(self):
        """Initialize the TaskManager."""
        pass

    def get_pending_tasks(self, pending_tasks: deque) -> List[Task]:
        """Get current pending tasks for human review."""
        return list(pending_tasks)

    def get_completed_tasks(self, completed_tasks: List[Task]) -> List[Task]:
        """Get completed tasks."""
        return completed_tasks.copy()

    def find_task_by_id(
        self, tasks: List[Task], task_id: str
    ) -> Optional[Task]:
        """Find a task in a list of tasks by ID.

        Args:
            tasks: List of tasks to search through
            task_id: The ID of the task to find

        Returns:
            The task if found, None otherwise
        """
        return next((task for task in tasks if task.id == task_id), None)

    def modify_task_content(
        self, task_id: str, new_content: str, pending_tasks: deque
    ) -> bool:
        """Modify the content of a pending task."""
        # Validate the new content first
        if not validate_task_content(new_content, task_id):
            logger.warning(
                f"Task {task_id} content modification rejected: "
                f"Invalid content. Content preview: '{new_content}'"
            )
            return False

        task = self.find_task_by_id(list(pending_tasks), task_id)
        if task:
            task.content = new_content
            logger.info(f"Task {task_id} content modified.")
            return True
        logger.warning(f"Task {task_id} not found in pending tasks.")
        return False

    def add_task(
        self,
        content: str,
        pending_tasks: deque,
        task_id: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
        insert_position: int = -1,
    ) -> Task:
        """Add a new task to the pending queue."""
        new_task = Task(
            content=content,
            id=task_id or f"human_added_{len(pending_tasks)}",
            additional_info=additional_info,
        )
        if insert_position == -1:
            pending_tasks.append(new_task)
        else:
            # Convert deque to list, insert, then back to deque
            tasks_list = list(pending_tasks)
            tasks_list.insert(insert_position, new_task)
            # Note: This modifies the original deque in place
            pending_tasks.clear()
            pending_tasks.extend(tasks_list)

        logger.info(f"New task added: {new_task.id}")
        return new_task

    def remove_task(self, task_id: str, pending_tasks: deque) -> bool:
        """Remove a task from the pending queue."""
        task = self.find_task_by_id(list(pending_tasks), task_id)
        if task:
            pending_tasks.remove(task)
            logger.info(f"Task {task_id} removed.")
            return True
        logger.warning(f"Task {task_id} not found in pending tasks.")
        return False

    def reorder_tasks(self, task_ids: List[str], pending_tasks: deque) -> bool:
        """Reorder pending tasks according to the provided task IDs list."""
        # Create a mapping of task_id to task
        tasks_dict = {task.id: task for task in pending_tasks}

        # Check if all provided IDs exist
        invalid_ids = [
            task_id for task_id in task_ids if task_id not in tasks_dict
        ]
        if invalid_ids:
            logger.warning(
                f"Task IDs not found in pending tasks: {invalid_ids}"
            )
            return False

        # Check if we have the same number of tasks
        if len(task_ids) != len(pending_tasks):
            logger.warning(
                "Number of task IDs doesn't match pending tasks count."
            )
            return False

        # Reorder tasks
        reordered_tasks = deque([tasks_dict[task_id] for task_id in task_ids])
        # Clear and repopulate the original deque
        pending_tasks.clear()
        pending_tasks.extend(reordered_tasks)

        logger.info("Tasks reordered successfully.")
        return True
