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
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from colorama import Fore

from camel.tasks.task import Task, TaskState
from camel.workforce.base import BaseNode
from camel.workforce.task_channel import TaskChannel
from camel.workforce.utils import check_if_running


class WorkerNode(BaseNode, ABC):
    r"""A worker node that works on tasks. It is the basic unit of task
    processing in the workforce system.

    Args:
        description (str): Description of the node.

    """

    # TODO: Make RolePlaying and Agent scceed from one parent class, so that
    #   we don't need two different classes for the worker node.

    def __init__(
        self,
        description: str,
    ) -> None:
        super().__init__(description)

    @abstractmethod
    async def _process_task(
        self, task: Task, dependencies: List[Task]
    ) -> TaskState:
        r"""Processes a task based on its dependencies.

        Returns:
            'DONE' if the task is successfully processed,
            'FAILED' if the processing fails.
        """

    async def _get_assigned_task(self) -> Task:
        r"""Get the task assigned to this node from the channel."""
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

    @check_if_running(False)
    async def _listen_to_channel(self):
        """Continuously listen to the channel, process the task that are
        assigned to this node, and update the result and status of the task.

        This method should be run in an event loop, as it will run
            indefinitely.
        """
        self._running = True
        print(f"{Fore.GREEN}Worker node {self.node_id} started.{Fore.RESET}")

        while True:
            # get the earliest task assigned to this node
            task = await self._get_assigned_task()
            print(
                f'worker node {self.node_id} get task:',
                task.id,
                task.content,
            )
            # get the Task instance of dependencies
            dependency_ids = await self._channel.get_dependency_ids()
            task_dependencies = [
                await self._channel.get_task_by_id(dep_id)
                for dep_id in dependency_ids
            ]

            # process the task
            task_state = await self._process_task(task, task_dependencies)

            # update the result and status of the task
            task.set_state(task_state)

            await self._channel.return_task(task.id)

    @check_if_running(False)
    async def start(self):
        await self._listen_to_channel()

    @check_if_running(True)
    def stop(self):
        self._running = False
        return
