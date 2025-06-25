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
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Set

from colorama import Fore

from camel.societies.workforce.base import BaseNode
from camel.societies.workforce.task_channel import TaskChannel
from camel.societies.workforce.utils import check_if_running
from camel.tasks.task import Task, TaskState

logger = logging.getLogger(__name__)


class Worker(BaseNode, ABC):
    r"""A worker node that works on tasks. It is the basic unit of task
    processing in the workforce system.

    Args:
        description (str): Description of the node.
        node_id (Optional[str]): ID of the node. If not provided, it will
            be generated automatically. (default: :obj:`None`)
    """

    def __init__(
        self,
        description: str,
        node_id: Optional[str] = None,
    ) -> None:
        super().__init__(description, node_id=node_id)
        self._active_task_ids: Set[str] = set()

    def __repr__(self):
        return f"Worker node {self.node_id} ({self.description})"

    @abstractmethod
    async def _process_task(
        self, task: Task, dependencies: List[Task]
    ) -> TaskState:
        r"""Processes a task based on its dependencies.

        Returns:
            'DONE' if the task is successfully processed,
            'FAILED' if the processing fails.
        """
        pass

    async def _get_assigned_task(self) -> Task:
        r"""Get a task assigned to this node from the channel."""
        return await self._channel.get_assigned_task_by_assignee(self.node_id)

    @staticmethod
    def _get_dep_tasks_info(dependencies: List[Task]) -> str:
        result_lines = [
            f"id: {dep_task.id}, content: {dep_task.content}. "
            f"result: {dep_task.result}."
            for dep_task in dependencies
        ]
        result_str = "\n".join(result_lines)
        return result_str

    @check_if_running(False)
    def set_channel(self, channel: TaskChannel):
        self._channel = channel

    async def _process_single_task(self, task: Task) -> None:
        r"""Process a single task and handle its completion/failure."""
        try:
            self._active_task_ids.add(task.id)
            print(
                f"{Fore.YELLOW}{self} get task {task.id}: {task.content}"
                f"{Fore.RESET}"
            )
            # Get the Task instance of dependencies
            dependency_ids = await self._channel.get_dependency_ids()
            task_dependencies = [
                await self._channel.get_task_by_id(dep_id)
                for dep_id in dependency_ids
            ]

            # Process the task
            task_state = await self._process_task(task, task_dependencies)

            # Update the result and status of the task
            task.set_state(task_state)

            await self._channel.return_task(task.id)
        except Exception as e:
            logger.error(f"Error processing task {task.id}: {e}")
            task.set_state(TaskState.FAILED)
            await self._channel.return_task(task.id)
        finally:
            self._active_task_ids.discard(task.id)

    @check_if_running(False)
    async def _listen_to_channel(self):
        r"""Continuously listen to the channel and process assigned tasks.

        This method supports parallel task execution without artificial limits.
        """
        self._running = True
        logger.info(f"{self} started.")

        # Keep track of running task coroutines
        running_tasks: Set[asyncio.Task] = set()

        while self._running:
            try:
                # Clean up completed tasks
                completed_tasks = [t for t in running_tasks if t.done()]
                for completed_task in completed_tasks:
                    running_tasks.remove(completed_task)
                    # Check for exceptions in completed tasks
                    try:
                        await completed_task
                    except Exception as e:
                        logger.error(f"Task processing failed: {e}")

                # Try to get a new task (with short timeout to avoid blocking)
                try:
                    task = await asyncio.wait_for(
                        self._get_assigned_task(), timeout=1.0
                    )

                    # Create and start processing task
                    task_coroutine = asyncio.create_task(
                        self._process_single_task(task)
                    )
                    running_tasks.add(task_coroutine)

                except asyncio.TimeoutError:
                    # No tasks available, continue loop
                    if not running_tasks:
                        # No tasks running and none available, short sleep
                        await asyncio.sleep(0.1)
                    continue

            except Exception as e:
                logger.error(
                    f"Error in worker {self.node_id} listen loop: {e}"
                )
                await asyncio.sleep(0.1)
                continue

        # Wait for all remaining tasks to complete when stopping
        if running_tasks:
            logger.info(
                f"{self} stopping, waiting for {len(running_tasks)} "
                f"tasks to complete..."
            )
            await asyncio.gather(*running_tasks, return_exceptions=True)

        logger.info(f"{self} stopped.")

    @check_if_running(False)
    async def start(self):
        r"""Start the worker."""
        await self._listen_to_channel()

    @check_if_running(True)
    def stop(self):
        r"""Stop the worker."""
        self._running = False
        return
