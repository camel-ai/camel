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

import time
from collections import deque
from typing import Deque, Dict, List, Optional

from camel.logger import get_logger
from camel.societies.workforce.utils import find_task_by_id
from camel.societies.workforce.workforce_split.state import WorkforceState
from camel.tasks.task import Task, TaskState

logger = get_logger(__name__)


class WorkforceSnapshot:
    r"""Snapshot of workforce state for resuming execution."""

    def __init__(
        self,
        main_task: Optional[Task] = None,
        pending_tasks: Optional[Deque[Task]] = None,
        completed_tasks: Optional[List[Task]] = None,
        task_dependencies: Optional[Dict[str, List[str]]] = None,
        assignees: Optional[Dict[str, str]] = None,
        current_task_index: int = 0,
        description: str = "",
    ):
        r"""Initialize a WorkforceSnapshot.

        Args:
            main_task (Task, optional): The main task being processed.
                (default: :obj:`None`)
            pending_tasks (Deque[Task], optional): Queue of pending tasks.
                (default: :obj:`None`)
            completed_tasks (List[Task], optional): List of completed tasks.
                (default: :obj:`None`)
            task_dependencies (Dict[str, List[str]], optional): Task dependency
                mapping. (default: :obj:`None`)
            assignees (Dict[str, str], optional): Task assignee mapping.
                (default: :obj:`None`)
            current_task_index (int, optional): Index of current task.
                (default: :obj:`0`)
            description (str, optional): Description of the snapshot.
                (default: :obj:`""`)
        """
        self.main_task = main_task
        self.pending_tasks = pending_tasks.copy() if pending_tasks else deque()
        self.completed_tasks = (
            completed_tasks.copy() if completed_tasks else []
        )
        self.task_dependencies = (
            task_dependencies.copy() if task_dependencies else {}
        )
        self.assignees = assignees.copy() if assignees else {}
        self.current_task_index = current_task_index
        self.description = description
        self.timestamp = time.time()


class WorkforceSnapshotManager:
    r"""Manager for workforce snapshot operations.

    This class provides functionality to save, list, and restore workforce
    snapshots, as well as resume execution from specific tasks.
    """

    def __init__(self):
        r"""Initialize the WorkforceSnapshotManager."""
        pass

    def save_snapshot(self, workforce_instance, description: str = "") -> None:
        r"""Save current state as a snapshot.

        Args:
            workforce_instance (Any): The workforce instance to save snapshot
                from.
            description (str, optional): Optional description for the snapshot.
                (default: :obj:`""`)
        """
        snapshot = WorkforceSnapshot(
            main_task=workforce_instance._task,
            pending_tasks=workforce_instance._pending_tasks,
            completed_tasks=workforce_instance._completed_tasks,
            task_dependencies=workforce_instance._get_task_dependencies(),
            assignees=workforce_instance._assignees,
            current_task_index=len(workforce_instance._completed_tasks),
            description=description or f"Snapshot at {time.time()}",
        )
        workforce_instance._snapshots.append(snapshot)
        logger.info(f"Snapshot saved: {description}")

    def list_snapshots(self, workforce_instance) -> List[str]:
        r"""List all available snapshots.

        Args:
            workforce_instance (Any): The workforce instance to list snapshots
                from.

        Returns:
            List[str]: List of snapshot information strings.
        """
        snapshots_info = []
        for i, snapshot in enumerate(workforce_instance._snapshots):
            desc_part = (
                f" - {snapshot.description}" if snapshot.description else ""
            )
            info = (
                f"Snapshot {i}: {len(snapshot.completed_tasks)} completed, "
                f"{len(snapshot.pending_tasks)} pending{desc_part}"
            )
            snapshots_info.append(info)
        return snapshots_info

    def _find_task_by_id(self, workforce_instance, task_id: str):
        r"""Find a task by its ID in pending or completed tasks.

        Args:
            workforce_instance (Any): The workforce instance to search in.
            task_id (str): The ID of the task to find.

        Returns:
            Optional[Task]: The found task or None if not found.
        """
        # Search in pending tasks
        pending_task = find_task_by_id(
            list(workforce_instance._pending_tasks), task_id
        )
        if pending_task:
            return pending_task

        # Search in completed tasks
        completed_task = find_task_by_id(
            workforce_instance._completed_tasks, task_id
        )
        if completed_task:
            return completed_task

        return None

    def resume_from_task(self, workforce_instance, task_id: str) -> bool:
        r"""Resume execution from a specific task.

        Args:
            workforce_instance (Any): The workforce instance to resume from.
            task_id (str): The ID of the task to resume from.

        Returns:
            bool: True if successful, False otherwise.
        """
        if workforce_instance._state != WorkforceState.PAUSED:
            logger.warning(
                "Workforce must be paused to resume from specific task."
            )
            return False

        # Find the task in pending tasks
        task = self._find_task_by_id(workforce_instance, task_id)
        if not task:
            logger.warning(f"Task {task_id} not found in pending tasks.")
            return False

        tasks_list = list(workforce_instance._pending_tasks)
        target_index = tasks_list.index(task)
        # Move completed tasks that come after the target task back to pending
        tasks_to_move_back = tasks_list[:target_index]
        remaining_tasks = tasks_list[target_index:]

        # Update pending tasks to start from the target task
        workforce_instance._pending_tasks = deque(remaining_tasks)

        # Move previously "completed" tasks that are after target back to
        # pending and reset their state
        if tasks_to_move_back:
            # Reset state for tasks being moved back to pending
            for task in tasks_to_move_back:
                # Handle all possible task states
                if task.state in [TaskState.DONE, TaskState.OPEN]:
                    task.state = (
                        TaskState.OPEN
                    )  # Reset to OPEN state for reprocessing
                    # Clear result to avoid confusion
                    task.result = None
                    # Reset failure count to give task a fresh start
                    task.failure_count = 0

            logger.info(
                f"Moving {len(tasks_to_move_back)} tasks back to pending "
                f"state."
            )

        logger.info(f"Ready to resume from task: {task_id}")
        return True

    def restore_from_snapshot(
        self, workforce_instance, snapshot_index: int
    ) -> bool:
        r"""Restore workforce state from a snapshot.

        Args:
            workforce_instance (Any): The workforce instance to restore.
            snapshot_index (int): Index of the snapshot to restore from.

        Returns:
            bool: True if successful, False otherwise.
        """
        if not (0 <= snapshot_index < len(workforce_instance._snapshots)):
            logger.warning(f"Invalid snapshot index: {snapshot_index}")
            return False

        if workforce_instance._state == WorkforceState.RUNNING:
            logger.warning(
                "Cannot restore snapshot while workforce is running. "
                "Pause first."
            )
            return False

        snapshot = workforce_instance._snapshots[snapshot_index]
        workforce_instance._task = snapshot.main_task
        workforce_instance._pending_tasks = snapshot.pending_tasks.copy()
        workforce_instance._completed_tasks = snapshot.completed_tasks.copy()
        workforce_instance._set_task_dependencies(
            snapshot.task_dependencies.copy()
        )
        workforce_instance._assignees = snapshot.assignees.copy()

        logger.info(f"Workforce state restored from snapshot {snapshot_index}")
        return True
