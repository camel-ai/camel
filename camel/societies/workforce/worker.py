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
from typing import Awaitable, List, Optional, TypeVar

from colorama import Fore

from camel.societies.workforce.base import BaseNode
from camel.societies.workforce.task_channel import TaskChannel
from camel.societies.workforce.utils import check_if_running
from camel.tasks.task import Task, TaskState

logger = logging.getLogger(__name__)

T = TypeVar('T')  # generic type for async operations
TIMEOUT_THRESHOLD = 180.0  # seconds


async def with_timeout(
    coro: Awaitable[T],
    timeout: float = TIMEOUT_THRESHOLD,
    context: str = "operation",
) -> T:
    """general timeout wrapper for async operations.

    Args:
        coro: async operation to be executed
        timeout: max wait time (seconds)
        context: context information, used for error messages

    Returns:
        result of the async operation

    Raises:
        asyncio.TimeoutError: if wait times out
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Operation timed out after {timeout}s: {context}")
        raise asyncio.TimeoutError(f"Timed out while {context}")


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
        r"""Get the task assigned to this node from the channel."""
        return await with_timeout(
            self._channel.get_assigned_task_by_assignee(self.node_id),
            timeout=TIMEOUT_THRESHOLD,
            context=f"getting assigned task for {self.node_id}",
        )

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

    @check_if_running(False)
    async def _listen_to_channel(self):
        """Continuously listen to the channel, process the task that are
        assigned to this node, and update the result and status of the task.

        This method should be run in an event loop, as it will run
            indefinitely.
        """
        self._running = True
        logger.info(f"{self} started.")

        while True:
            # Get the earliest task assigned to this node
            task = await with_timeout(
                self._get_assigned_task(),
                timeout=TIMEOUT_THRESHOLD,
                context=f"getting assigned task for {self.node_id}",
            )

            print(
                f"{Fore.YELLOW}{self} get task {task.id}: {task.content}"
                f"{Fore.RESET}"
            )

            # Get the Task instance of dependencies
            dependency_ids = await with_timeout(
                self._channel.get_dependency_ids(),
                context=f"getting dependency IDs for task {task.id}",
            )
            task_dependencies = []
            for dep_id in dependency_ids:
                dep_task = await with_timeout(
                    self._channel.get_task_by_id(dep_id),
                    context=f"getting dependency task {dep_id}",
                )
                task_dependencies.append(dep_task)

            # Process the task
            task_state = await with_timeout(
                self._process_task(task, task_dependencies),
                timeout=TIMEOUT_THRESHOLD,
                context=f"processing task {task.id}",
            )

            # Update the result and status of the task
            task.set_state(task_state)

            await with_timeout(
                self._channel.return_task(task.id),
                timeout=TIMEOUT_THRESHOLD,
                context=f"returning task {task.id}",
            )

    @check_if_running(False)
    async def start(self):
        r"""Start the worker."""
        await with_timeout(
            self._listen_to_channel(),
            timeout=TIMEOUT_THRESHOLD,
            context=f"listening to channel for {self.node_id}",
        )

    @check_if_running(True)
    def stop(self):
        r"""Stop the worker."""
        self._running = False
        return
