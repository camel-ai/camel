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
    """Class to handle channel communication operations for workforce tasks."""

    def __init__(self):
        """Initialize the ChannelCommunication class."""
        pass

    async def post_task(
        self,
        task: Task,
        assignee_id: str,
        channel: TaskChannel,
        node_id: str,
        task_start_times: Dict[str, float],
        metrics_logger=None,
        increment_in_flight_tasks_func=None,
    ) -> None:
        """Post a task to the channel with the specified assignee.

        Args:
            task: The task to post
            assignee_id: The ID of the assignee
            channel: The task channel for communication
            node_id: The node identifier
            task_start_times: Dictionary tracking task start times
            metrics_logger: Optional metrics logger
            increment_in_flight_tasks_func: Function to increment in-flight
                tasks
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

    async def post_dependency(
        self,
        dependency: Task,
        channel: TaskChannel,
        node_id: str,
    ) -> None:
        """Post a dependency to the channel.

        Args:
            dependency: The dependency task to post
            channel: The task channel for communication
            node_id: The node identifier
        """
        await channel.post_dependency(dependency, node_id)

    async def get_returned_task(
        self,
        channel: TaskChannel,
        node_id: str,
        pending_tasks: List[Task],
        in_flight_tasks: int,
    ) -> Optional[Task]:
        """Get the task that's published by this node and just get returned
        from the assignee. Includes timeout handling to prevent indefinite
        waiting.

        Args:
            channel: The task channel for communication
            node_id: The node identifier
            pending_tasks: List of pending tasks
            in_flight_tasks: Number of in-flight tasks

        Returns:
            The returned task or None if no task is returned
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

    async def post_ready_tasks(
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
        """Checks for unassigned tasks, assigns them, and then posts any
        ready tasks to the channel.

        Args:
            pending_tasks: List of pending tasks
            completed_tasks: List of completed tasks
            task_dependencies: Dictionary mapping task IDs to dependencies
            assignees: Dictionary mapping task IDs to assignee IDs
            task_start_times: Dictionary tracking task start times
            channel: The task channel for communication
            node_id: The node identifier
            metrics_logger: Optional metrics logger
            increment_in_flight_tasks_func: Function to increment in-flight
                tasks
            find_assignee_func: Function to find task assignees
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
                    await self.post_task(
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

    async def listen_to_channel(
        self,
        channel: TaskChannel,
        node_id: str,
        pending_tasks: List[Task],
        completed_tasks: List[Task],
        task_dependencies: Dict[str, List[str]],
        assignees: Dict[str, str],
        task_start_times: Dict[str, float],
        in_flight_tasks: int,
        metrics_logger=None,
        find_assignee_func=None,
        increment_in_flight_tasks_func=None,
        decrement_in_flight_tasks_func=None,
        handle_failed_task_func=None,
        handle_completed_task_func=None,
        graceful_shutdown_func=None,
        is_task_result_insufficient_func=None,
        pause_event=None,
        stop_requested=False,
        running=False,
        state=None,
        last_snapshot_time=0,
        snapshot_interval=60,
        save_snapshot_func=None,
        loop=None,
    ) -> None:
        """Continuously listen to the channel, post task to the channel and
        track the status of posted tasks. Now supports pause/resume and
        graceful stop.

        Args:
            channel: The task channel for communication
            node_id: The node identifier
            pending_tasks: List of pending tasks
            completed_tasks: List of completed tasks
            task_dependencies: Dictionary mapping task IDs to dependencies
            assignees: Dictionary mapping task IDs to assignee IDs
            task_start_times: Dictionary tracking task start times
            in_flight_tasks: Number of in-flight tasks
            metrics_logger: Optional metrics logger
            find_assignee_func: Function to find task assignees
            increment_in_flight_tasks_func: Function to increment in-flight
                tasks
            decrement_in_flight_tasks_func: Function to decrement in-flight
                tasks
            handle_failed_task_func: Function to handle failed tasks
            handle_completed_task_func: Function to handle completed tasks
            graceful_shutdown_func: Function for graceful shutdown
            is_task_result_insufficient_func: Function to check if task result
                is insufficient
            pause_event: Event for pause functionality
            stop_requested: Flag indicating if stop was requested
            running: Flag indicating if running
            state: Current state
            last_snapshot_time: Last snapshot time
            snapshot_interval: Snapshot interval
            save_snapshot_func: Function to save snapshots
            loop: Event loop
        """

        logger.info(f"Workforce {node_id} started.")

        await self.post_ready_tasks(
            pending_tasks,
            completed_tasks,
            task_dependencies,
            assignees,
            channel,
            node_id,
            task_start_times,
            metrics_logger,
            increment_in_flight_tasks_func,
            find_assignee_func,
        )

        while (
            len(pending_tasks) > 0 or in_flight_tasks > 0
        ) and not stop_requested:
            try:
                # Check for pause request at the beginning of each loop
                # iteration
                if pause_event:
                    await pause_event.wait()

                # Check for stop request after potential pause
                if stop_requested:
                    logger.info("Stop requested, breaking execution loop.")
                    break

                # Save snapshot before processing next task
                if pending_tasks:
                    current_task = pending_tasks[0]
                    # Throttled snapshot
                    if time.time() - last_snapshot_time >= snapshot_interval:
                        if save_snapshot_func:
                            save_snapshot_func(
                                f"Before processing task: {current_task.id}"
                            )
                        last_snapshot_time = time.time()

                # Get returned task
                returned_task = await self.get_returned_task(
                    channel,
                    node_id,
                    pending_tasks,
                    in_flight_tasks,
                )

                # If no task was returned, continue
                if returned_task is None:
                    logger.debug(
                        f"No task returned in workforce {node_id}. "
                        f"Pending: {len(pending_tasks)}, "
                        f"In-flight: {in_flight_tasks}"
                    )
                    await self.post_ready_tasks(
                        pending_tasks,
                        completed_tasks,
                        task_dependencies,
                        assignees,
                        channel,
                        node_id,
                        task_start_times,
                        metrics_logger,
                        increment_in_flight_tasks_func,
                        find_assignee_func,
                    )
                    continue

                if decrement_in_flight_tasks_func:
                    decrement_in_flight_tasks_func(
                        returned_task.id, "task returned successfully"
                    )

                # Process the returned task based on its state
                if returned_task.state == TaskState.DONE:
                    # Task completed successfully
                    # Check if the "completed" task actually failed to provide
                    # useful results
                    if (
                        is_task_result_insufficient_func
                        and is_task_result_insufficient_func(returned_task)
                    ):
                        result_preview = (
                            returned_task.result
                            if returned_task.result
                            else "No result"
                        )
                        logger.warning(
                            f"Task {returned_task.id} marked as DONE but "
                            f"result is insufficient. "
                            f"Treating as failed. Result: '{result_preview}'"
                        )
                        returned_task.state = TaskState.FAILED
                        try:
                            if handle_failed_task_func:
                                halt = await handle_failed_task_func(
                                    returned_task
                                )
                                if not halt:
                                    continue
                                error_msg = (
                                    returned_task.result or "Unknown error"
                                )
                                print(
                                    f"{Fore.RED}Task {returned_task.id} has "
                                    f"failed for 3 times after "
                                    f"insufficient results, halting the "
                                    f"workforce. Final error: "
                                    f"{error_msg}"
                                    f"{Fore.RESET}"
                                )
                                if graceful_shutdown_func:
                                    await graceful_shutdown_func(returned_task)
                                break
                        except Exception as e:
                            logger.error(
                                f"Error handling insufficient task result "
                                f"{returned_task.id}: {e}",
                                exc_info=True,
                            )
                            continue
                    else:
                        # Task completed successfully with sufficient results
                        if handle_completed_task_func:
                            await handle_completed_task_func(returned_task)
                        print(
                            f"{Fore.GREEN}✅ Task {returned_task.id} "
                            f"completed successfully.{Fore.RESET}"
                        )
                elif returned_task.state == TaskState.FAILED:
                    try:
                        if handle_failed_task_func:
                            halt = await handle_failed_task_func(
                                returned_task,
                            )
                            if not halt:
                                continue
                            error_msg = returned_task.result or 'Unknown error'
                            print(
                                f"{Fore.RED}Task {returned_task.id} has "
                                f"failed for 3 times, halting the "
                                f"workforce. Final error: "
                                f"{error_msg}"
                                f"{Fore.RESET}",
                            )
                            # Graceful shutdown instead of immediate break
                            if graceful_shutdown_func:
                                await graceful_shutdown_func(returned_task)
                            break
                    except Exception as e:
                        logger.error(
                            f"Error handling failed task "
                            f"{returned_task.id}: {e}",
                            exc_info=True,
                        )
                        # Continue to prevent hanging
                        continue
                elif returned_task.state == TaskState.OPEN:
                    # Task is in OPEN state - it's ready to be processed
                    # This typically means the task was returned without being
                    # processed
                    logger.info(
                        f"Task {returned_task.id} returned in OPEN state - "
                        f"ready for processing"
                    )
                    # Move task back to pending queue for reassignment
                    pending_tasks.append(returned_task)
                    if decrement_in_flight_tasks_func:
                        decrement_in_flight_tasks_func(
                            returned_task.id, "task returned in OPEN state"
                        )
                else:
                    raise ValueError(
                        f"Task {returned_task.id} has an unexpected state."
                    )

            except Exception as e:
                # Decrement in-flight counter to prevent hanging
                if decrement_in_flight_tasks_func:
                    decrement_in_flight_tasks_func(
                        "unknown", "exception in task processing loop"
                    )

                logger.error(
                    f"Error processing task in workforce {node_id}: {e}"
                    f"Workforce state - Pending tasks: "
                    f"{len(pending_tasks)}, "
                    f"In-flight tasks: {in_flight_tasks}, "
                    f"Completed tasks: {len(completed_tasks)}"
                )

                if stop_requested:
                    break
                # Continue with next iteration unless stop is requested
                continue

        # Handle final state
        if stop_requested:
            logger.info("Workforce stopped by user request.")
        elif not pending_tasks and in_flight_tasks == 0:
            logger.info("All tasks completed.")

    def submit_coro_to_loop(
        self,
        coro: Coroutine,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        """Thread-safe submission of coroutine to the workforce loop.

        Args:
            coro: The coroutine to submit
            loop: The event loop to submit to
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
