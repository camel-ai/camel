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

import asyncio
import json
import time
from typing import Coroutine, Dict, List, Optional

from colorama import Fore

from camel.logger import get_logger
from camel.societies.workforce.task_channel import TaskChannel
from camel.tasks.task import Task, TaskState

logger = get_logger(__name__)

# Constants
TASK_TIMEOUT_SECONDS = 180.0


class ChannelCommunication:
    r"""Class to handle channel communication operations for workforce
    tasks."""

    def __init__(self):
        r"""Initialize the ChannelCommunication class."""
        pass

    async def _post_task(
        self,
        task: Task,
        assignee_id: str,
        channel: TaskChannel,
        node_id: str,
        task_start_times: Dict[str, float],
        metrics_logger=None,
        increment_in_flight_tasks_func=None,
    ) -> None:
        r"""Post a task to the channel with the specified assignee.

        Args:
            task (Task): The task to post.
            assignee_id (str): The ID of the assignee.
            channel (TaskChannel): The task channel for communication.
            node_id (str): The node identifier.
            task_start_times (Dict[str, float]): Dictionary tracking task
                start times.
            metrics_logger (Any, optional): Optional metrics logger.
                (default: :obj:`None`)
            increment_in_flight_tasks_func (Callable, optional): Function to
                increment in-flight tasks. (default: :obj:`None`)
        """
        # Record the start time when a task is posted
        task_start_times[task.id] = time.time()

        task.assigned_worker_id = assignee_id

        if metrics_logger:
            metrics_logger.log_task_started(
                task_id=task.id, worker_id=assignee_id
            )

        try:
            await channel.post_task(task, node_id, assignee_id)
            if increment_in_flight_tasks_func:
                increment_in_flight_tasks_func(task.id)
            logger.debug(f"Posted task {task.id} to {assignee_id}.")
        except Exception as e:
            logger.error(
                f"Failed to post task {task.id} to {assignee_id}: {e}"
            )
            print(
                f"{Fore.RED}Failed to post task {task.id} to {assignee_id}: "
                f"{e}{Fore.RESET}"
            )

    async def _post_dependency(
        self,
        dependency: Task,
        channel: TaskChannel,
        node_id: str,
    ) -> None:
        r"""Post a dependency to the channel.

        Args:
            dependency (Task): The dependency task to post.
            channel (TaskChannel): The task channel for communication.
            node_id (str): The node identifier.
        """
        await channel.post_dependency(dependency, node_id)

    async def _get_returned_task(
        self,
        channel: TaskChannel,
        node_id: str,
        pending_tasks: List[Task],
        in_flight_tasks: int,
    ) -> Optional[Task]:
        r"""Get the task that's published by this node and just get returned
        from the assignee. Includes timeout handling to prevent indefinite
        waiting.

        Args:
            channel (TaskChannel): The task channel for communication.
            node_id (str): The node identifier.
            pending_tasks (List[Task]): List of pending tasks.
            in_flight_tasks (int): Number of in-flight tasks.

        Returns:
            Optional[Task]: The returned task or None if no task is returned.
        """
        try:
            # Add timeout to prevent indefinite waiting
            return await asyncio.wait_for(
                channel.get_returned_task_by_publisher(node_id),
                timeout=TASK_TIMEOUT_SECONDS,
            )
        except Exception as e:
            error_msg = (
                f"Error getting returned task {e} in "
                f"workforce {node_id}. "
                f"Current pending tasks: {len(pending_tasks)}, "
                f"In-flight tasks: {in_flight_tasks}"
            )
            logger.error(error_msg, exc_info=True)
            return None

    async def _post_ready_tasks(
        self,
        pending_tasks: List[Task],
        completed_tasks: List[Task],
        task_dependencies: Dict[str, List[str]],
        assignees: Dict[str, str],
        channel: TaskChannel,
        node_id: str,
        task_start_times: Dict[str, float],
        metrics_logger=None,
        increment_in_flight_tasks_func=None,
        find_assignee_func=None,
    ) -> None:
        r"""Checks for unassigned tasks, assigns them, and then posts any
        ready tasks to the channel.

        Args:
            pending_tasks (List[Task]): List of pending tasks.
            completed_tasks (List[Task]): List of completed tasks.
            task_dependencies (Dict[str, List[str]]): Dictionary mapping task
                IDs to dependencies.
            assignees (Dict[str, str]): Dictionary mapping task IDs to
                assignee IDs.
            task_start_times (Dict[str, float]): Dictionary tracking task
                start times.
            channel (TaskChannel): The task channel for communication.
            node_id (str): The node identifier.
            metrics_logger (Any, optional): Optional metrics logger.
                (default: :obj:`None`)
            increment_in_flight_tasks_func (Callable, optional): Function to
                increment in-flight tasks. (default: :obj:`None`)
            find_assignee_func (Callable, optional): Function to find task
                assignees. (default: :obj:`None`)
        """

        # Step 1: Identify and assign any new tasks in the pending queue
        tasks_to_assign = [
            task for task in pending_tasks if task.id not in task_dependencies
        ]
        if tasks_to_assign:
            logger.debug(
                f"Found {len(tasks_to_assign)} new tasks. "
                f"Requesting assignment..."
            )
            if find_assignee_func:
                batch_result = await find_assignee_func(tasks_to_assign)
                logger.debug(
                    f"Coordinator returned assignments:\n"
                    f"{json.dumps(batch_result.dict(), indent=2)}"
                )
                for assignment in batch_result.assignments:
                    task_dependencies[assignment.task_id] = (
                        assignment.dependencies
                    )
                    assignees[assignment.task_id] = assignment.assignee_id
                    if metrics_logger:
                        # queue_time_seconds can be derived by logger if task
                        # creation time is logged
                        metrics_logger.log_task_assigned(
                            task_id=assignment.task_id,
                            worker_id=assignment.assignee_id,
                            dependencies=assignment.dependencies,
                            queue_time_seconds=None,
                        )

        # Step 2: Iterate through all pending tasks and post those that are
        # ready
        posted_tasks = []
        # Pre-compute completed task IDs and their states for O(1) lookups
        completed_tasks_info = {t.id: t.state for t in completed_tasks}

        for task in pending_tasks:
            # A task must be assigned to be considered for posting
            if task.id in task_dependencies:
                dependencies = task_dependencies[task.id]
                # Check if all dependencies for this task are in the completed
                # set and their state is DONE
                if all(
                    dep_id in completed_tasks_info
                    and completed_tasks_info[dep_id] == TaskState.DONE
                    for dep_id in dependencies
                ):
                    assignee_id = assignees[task.id]
                    logger.debug(
                        f"Posting task {task.id} to assignee {assignee_id}. "
                        f"Dependencies met."
                    )
                    await self._post_task(
                        task,
                        assignee_id,
                        channel,
                        node_id,
                        task_start_times,
                        metrics_logger,
                        increment_in_flight_tasks_func,
                    )
                    posted_tasks.append(task)

        # Step 3: Remove the posted tasks from the pending list
        for task in posted_tasks:
            try:
                pending_tasks.remove(task)
            except ValueError:
                # Task might have been removed by another process, which is
                # fine
                pass

    def _submit_coro_to_loop(
        self,
        coro: Coroutine,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        r"""Thread-safe submission of coroutine to the workforce loop.

        Args:
            coro (Coroutine): The coroutine to submit.
            loop (asyncio.AbstractEventLoop, optional): The event loop to
                submit to. (default: :obj:`None`)
        """

        if loop is None or loop.is_closed():
            logger.warning("Cannot submit coroutine - no active event loop")
            return
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is loop:
            loop.create_task(coro)
        else:
            asyncio.run_coroutine_threadsafe(coro, loop)
