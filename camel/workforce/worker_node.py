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

from camel.tasks.task import Task, TaskState
from camel.workforce.base import BaseNode
from camel.workforce.task_channel import TaskChannel


class WorkerNode(BaseNode, ABC):
    r"""A unit workforce that consists of a single worker. It is the basic unit
    of task processing in the workforce system.

    Args:
        workforce_id (str): ID for the workforce.
        description (str): Description of the workforce.
        worker (Union[BaseAgent, RolePlaying]): Worker of the workforce.
            Could be a single agent or a role playing system.
        channel (TaskChannel): Communication channel for the workforce.

    """

    def __init__(
        self,
        workforce_id: str,
        description: str,
        # TODO: here we should have a superclass for BaseAgent and
        #  RolePlaying
        # worker: Union[BaseAgent, RolePlaying],
        channel: TaskChannel,
    ) -> None:
        super().__init__(workforce_id, description, channel)
        # self.worker = worker

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
        r"""Get the task assigned to this workforce from the channel."""
        return await self.channel.get_assigned_task_by_assignee(
            self.workforce_id
        )

    def _get_dep_tasks_info(self, dependencies: List[Task]) -> str:
        result_lines = [
            f"id: {dep_task.id}, content: {dep_task.content}. "
            f"result: {dep_task.result}."
            for dep_task in dependencies
        ]
        result_str = "\n".join(result_lines)
        return result_str

    async def _listen_to_channel(self):
        """Continuously listen to the channel, process the task that are
        assigned to this workforce, and update the result and status of the
        task.

        This method should be run in an event loop, as it will run
            indefinitely.
        """
        while self.running:
            # get the earliest task assigned to this workforce
            task = await self._get_assigned_task()
            print(
                f'workforce-{self.workforce_id} get task:',
                task.id,
                task.content,
            )
            # get the Task instance of dependencies
            dependency_ids = await self.channel.get_dependency_ids()
            task_dependencies = [
                await self.channel.get_task_by_id(dep_id)
                for dep_id in dependency_ids
            ]

            # process the task
            task_state = await self._process_task(task, task_dependencies)

            # update the result and status of the task
            task.set_state(task_state)

            await self.channel.return_task(task.id)

    async def start(self):
        await self._listen_to_channel()

    async def stop(self):
        return
