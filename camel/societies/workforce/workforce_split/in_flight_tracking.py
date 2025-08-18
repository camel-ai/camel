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

from typing import Dict

from camel.logger import get_logger

logger = get_logger(__name__)


class InFlightTaskTracker:
    r"""A class for tracking in-flight tasks with safety checks and logging."""

    def __init__(self):
        r"""Initialize the InFlightTaskTracker."""
        pass

    def _increment_in_flight_tasks(
        self, in_flight_tasks: int, task_id: str
    ) -> int:
        r"""Safely increment the in-flight tasks counter with logging.

        Args:
            in_flight_tasks (int): Current count of in-flight tasks.
            task_id (str): The ID of the task being tracked.

        Returns:
            int: The updated count of in-flight tasks.
        """
        new_count = in_flight_tasks + 1
        logger.debug(
            f"Incremented in-flight tasks for {task_id}. "
            f"Count: {new_count}"
        )
        return new_count

    def _decrement_in_flight_tasks(
        self, in_flight_tasks: int, task_id: str, context: str = ""
    ) -> int:
        r"""Safely decrement the in-flight tasks counter with safety checks.

        Args:
            in_flight_tasks (int): Current count of in-flight tasks.
            task_id (str): The ID of the task being tracked.
            context (str, optional): Additional context for logging purposes.
                (default: :obj:`""`)

        Returns:
            int: The updated count of in-flight tasks.
        """
        if in_flight_tasks > 0:
            new_count = in_flight_tasks - 1
            logger.debug(
                f"Decremented in-flight tasks for {task_id} ({context}). "
                f"Count: {new_count}"
            )
            return new_count
        else:
            logger.debug(
                f"Attempted to decrement in-flight tasks for {task_id} "
                f"({context}) but counter is already 0. "
                f"Counter: {in_flight_tasks}"
            )
            return in_flight_tasks

    def _cleanup_task_tracking(
        self,
        task_id: str,
        task_start_times: Dict[str, float],
        task_dependencies: Dict[str, list],
        assignees: Dict[str, str],
    ) -> tuple[Dict[str, float], Dict[str, list], Dict[str, str]]:
        r"""Clean up tracking data for a task to prevent memory leaks.

        Args:
            task_id (str): The ID of the task to clean up.
            task_start_times (Dict[str, float]): Dictionary of task start
                times.
            task_dependencies (Dict[str, list]): Dictionary of task
                dependencies.
            assignees (Dict[str, str]): Dictionary of task assignees.

        Returns:
            tuple[Dict[str, float], Dict[str, list], Dict[str, str]]: Updated
                dictionaries with the task_id removed.
        """
        updated_start_times = task_start_times.copy()
        updated_dependencies = task_dependencies.copy()
        updated_assignees = assignees.copy()

        if task_id in updated_start_times:
            del updated_start_times[task_id]

        if task_id in updated_dependencies:
            del updated_dependencies[task_id]

        if task_id in updated_assignees:
            del updated_assignees[task_id]

        return updated_start_times, updated_dependencies, updated_assignees
