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

import asyncio
from collections import deque
from typing import List, Optional, boolean

from camel.agents.manager_agent import ChatAgent, ManagerAgent
from camel.tasks.task import Task, TaskManager
from camel.workforce import BaseWorkforce, LeafWorkforce
from camel.workforce.task_channel import Packet, TaskChannel, Taskstatus
from camel.workforce.utils import get_workforces_info


class InternalWorkforce(BaseWorkforce):
    r"""A workforce that manages multiple workforces and agents. It will
    split the task it receives into subtasks and assign them to the
    workforces/agents under it, and also handles the situation when the task
    fails.

    Args:
        workforce_id (str): ID for the workforce.
        description (str): Description of the workforce.
        workforces (List[BaseWorkforce]): List of workforces under this
            workforce.
        manager_agent_config (dict): Configuration parameters for the
            manager agent.
        channel (TaskChannel): Communication channel for the workforce.
    """

    def __init__(
        self,
        workforce_id: str,
        description: str,
        workforces: List[BaseWorkforce],
        manager_agent_config: dict,
        task_agent_config: dict,
        initial_task: Optional[Task],
        channel: TaskChannel,
    ) -> None:
        super().__init__(workforce_id, description, channel)
        self.workforces = workforces
        self.manager_agent = ManagerAgent(manager_agent_config)
        self.task_agent = ChatAgent(task_agent_config)
        self.workforce_info = get_workforces_info(workforces)
        self.initial_task = initial_task
        self.task_collection = TaskManager(self.initial_task)

    def assign_task(
        self, task: Task, failed_log: Optional[str], workforce_info: str
    ) -> str:
        r"""Assigns a task to an internal workforce if capable, otherwise
        create a new workforce.

        Parameters:
            task (Task): The task to be assigned.
            failed_log (Optional[str]): Optional log of a previous failed
                attempt.
            workforce_info (str): Information about the internal workforce.

        Returns:
            str: ID of the assigned workforce.
        """
        raise NotImplementedError()

    def create_workforce_for_task(self, task: Task) -> LeafWorkforce:
        r"""Creates a new workforce for a given task. One of the actions that
        the manager agent can take when a task has failed.

        Args:
            task (Task): The task for which the workforce is created.

        Returns:
            LeafWorkforce: The created workforce.
        """
        raise NotImplementedError()

    def decompose_task_to_packets(
        self, task: Task, failed: boolean
    ) -> List[Packet]:
        r"""Decompose a task into a packet and set dependencies."""
        packet_lst, dependencies = [], []
        subtasks = self.task_collection.decompose(task, self.task_agent)

        for subtask in subtasks:
            # get assign_id by calling assign_task function.
            # If failed, create a workforce.
            if failed:
                assign_id = self.create_workforce_for_task(
                    subtask
                ).workforce_id
            else:
                assign_id = self.assign_task(subtask)
            # set status as Taskstatus.ASSIGNED
            packet = Packet(
                subtask, self.workforce_id, assign_id, dependencies
            )
            packet_lst.append(packet)
            # get dependencies via the index of the subtask list
            dependencies.append(subtask.id)

        return packet_lst

    async def get_finished_task(self) -> Packet:
        r"""Get the task that's published by the workforce and just get
        finished from the channel."""
        return await self.channel.get_finished_task_by_publisher(
            self.workforce_id
        )

    async def send_packet(self) -> None:
        await self.channel.post_task(self.pending_packets.popleft())

    async def listening(self) -> None:
        r"""Continuously listen to the channel, post task to the channel and
        track the status of posted tasks.
        """
        if self.initial_task is not None:
            # TODO: split the initial task into subtasks and assign the
            #  first one to the workforces
            packets = self.decompose_task_to_packets(
                task=self.initial_task, failed=False
            )
            # Insert packets at the tail of the queue and send to channel
            self.pending_packets.extend(packets)
            self.send_packet()

        while self.running and self.pending_packets:
            finished_task = await self.get_finished_task()
            if finished_task.status == Taskstatus.COMPLETED:
                # close the task, indicating that the task is completed and
                # known by the manager
                await self.channel.update_task(
                    finished_task.task.id, Taskstatus.CLOSED
                )
                # TODO: mark the task as completed, assign the next task
                await self.send_packet()

            elif finished_task.status == Taskstatus.FAILED:
                # remove the failed task from the channel
                await self.channel.remove_task(finished_task.task.id)
                # TODO: apply action when the task fails

                packets = self.decompose_task_to_packets(
                    task=finished_task.task, failed=True
                )
                # Insert packets at the head of the queue
                self.pending_packets.extendleft(packets)

                await self.send_packet()
        # Q: When does the manager compose the results of all subtasks?
        # After all tasks are closed, or does the process continue
        # when it detects that subtasks are completed?
        await self.stop()

    async def start(self) -> None:
        r"""Start the internal workforce and all the workforces under it."""
        self.running = True
        self.pending_packets = deque()
        tasks = [
            asyncio.create_task(workforce.start())
            for workforce in self.workforces
        ]
        tasks.append(asyncio.create_task(self.listening()))
        await asyncio.gather(*tasks)

    async def stop(self) -> None:
        r"""Stop the internal workforce and all the workforces under it."""
        self.running = False
        for workforce in self.workforces:
            await workforce.stop()
