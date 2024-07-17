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

from typing import List, Union

from camel.agents.base import BaseAgent
from camel.societies import RolePlaying
from camel.tasks.task import Task
from camel.workforce.base import BaseWorkforce
from camel.workforce.task_channel import Packet, TaskChannel, PacketStatus


class LeafWorkforce(BaseWorkforce):
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
        worker: Union[BaseAgent, RolePlaying],
        channel: TaskChannel,
    ) -> None:
        super().__init__(workforce_id, description, channel)
        self.worker = worker

    def process_task(
        self, task: Task, dependencies: List[Task]
    ) -> PacketStatus:
        r"""Processes a task based on its dependencies.

        Returns:
            'COMPLETE' if the task is successfully processed,
            'FAILED' if the processing fails.
        """
        raise NotImplementedError()

    async def get_assigned_task(self) -> Packet:
        r"""Get the task assigned to this workforce from the channel."""
        return await self.channel.get_assigned_task_by_assignee(
            self.workforce_id
        )

    async def listening(self):
        """Continuously listen to the channel, process the task that are
        assigned to this workforce, and update the result and status of the
        task.

        This method should be run in an event loop, as it will run
            indefinitely.
        """
        while self.running:
            # get the earliest task assigned to this workforce
            packet = await self.get_assigned_task()
            # get the Task instance of dependencies
            task_dependencies = []
            for dep_task_id in packet.dependencies:
                task_dependency = await self.channel.get_task_by_id(
                    dep_task_id
                )
                task_dependencies.append(task_dependency)

            task_state = await self.process_task(
                packet.task, task_dependencies
            )

            await self.channel.return_task(packet.task.id, task_state)

            # TODO: check if the task can be done. If not, fail the task.
            # TODO: fetch the info of dependencies
            # TODO: process the task
            # TODO: update the result and status of the task

    async def start(self):
        self.running = True
        await self.listening()

    async def stop(self):
        self.running = False
