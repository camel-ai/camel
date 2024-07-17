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
import asyncio
from enum import Enum
from typing import Dict, List, Optional

from camel.tasks import Task


class PacketStatus(Enum):
    r"""The status of a packet. The packet can be in one of the following
    states:
    - ``SENT``: The packet has been sent to a worker.
    - ``RETURNED``: The packet has been returned by the worker, meaning that
            the status of the task inside has been updated.
    - ``HANGING``: The packet is temporarily unavailable. This may due to
            reasons like failed tasks.
    - ``ARCHIVED``: The packet has been archived, meaning that the content of
            the task inside will not be changed.
    """

    SENT = "SENT"
    RETURNED = "RETURNED"
    HANGING = "HANGING"
    ARCHIVED = "ARCHIVED"


class Packet:
    r"""The basic element inside the channel. A task is wrapped inside a
    packet. The packet will contain the task, along with the task's assignee,
    and the task's status.

    Args:
        task (Task): The task that is wrapped inside the packet.
        publisher_id (str): The ID of the workforce that published the task.
        assignee_id (str): The ID of the workforce that is assigned to the
            task.
        dependencies (Optional[Tuple[str]], optional): The list of task IDs
            that the task depends on. Defaults to None.

    Attributes:
        task (Task): The task that is wrapped inside the packet.
        publisher_id (str): The ID of the workforce that published the task.
        assignee_id (str): The ID of the workforce that is assigned to the
            task.
        status (PacketStatus): The status of the task.
        dependencies (Optional[List[str]]): The list of task IDs that the
            task depends on.
    """

    def __init__(
        self,
        task: Task,
        publisher_id: str,
        assignee_id: str,
        dependencies: Optional[List[str]] = None,
        status: PacketStatus = PacketStatus.SENT,
    ):
        self.task = task
        self.publisher_id = publisher_id
        self.assignee_id = assignee_id
        self.dependencies = dependencies
        self.status = status


class TaskChannel:
    r"""An internal class used by Workforce to manage tasks."""

    def __init__(self):
        self._task_id_list: List[str] = []
        self._condition = asyncio.Condition()
        self._task_dict: Dict[str, Packet] = {}

    async def get_returned_task_by_publisher(self, publisher_id: str) -> Task:
        async with self._condition:
            while True:
                for task_id in self._task_id_list:
                    packet = self._task_dict[task_id]
                    if packet.publisher_id != publisher_id:
                        continue
                    if packet.status != PacketStatus.RETURNED:
                        continue
                    return packet.task
                await self._condition.wait()

    async def get_assigned_task_by_assignee(self, assignee_id: str) -> Task:
        async with self._condition:
            while True:
                for task_id in self._task_id_list:
                    packet = self._task_dict[task_id]
                    if (
                        packet.assignee_id == assignee_id
                        and packet.status == PacketStatus.SENT
                    ):
                        return packet.task
                await self._condition.wait()

    async def send_task(
        self,
        task: Task,
        publisher_id: str,
        assignee_id: str,
        dependencies: Optional[List[str]] = None,
    ) -> None:
        r"""Send a task to the channel with specified publisher and assignee,
        along with the dependency of the task."""
        async with self._condition:
            self._task_id_list.append(task.id)
            packet = Packet(task, publisher_id, assignee_id, dependencies)
            self._task_dict[packet.task.id] = packet
            self._condition.notify_all()

    async def return_task(self, task_id: str) -> None:
        r"""Return a task to the sender, indicating that the task has been
        processed by the worker."""
        async with self._condition:
            packet = self._task_dict[task_id]
            packet.status = PacketStatus.RETURNED
            self._condition.notify_all()

    async def remove_task(self, task_id: str) -> None:
        async with self._condition:
            self._task_id_list.remove(task_id)
            self._task_dict.pop(task_id)
            self._condition.notify_all()

    async def get_task_by_id(self, task_id: str) -> Task:
        async with self._condition:
            if task_id not in self._task_id_list:
                raise ValueError(f"Task {task_id} not found.")
            return self._task_dict[task_id].task

    async def print_channel(self):
        async with self._condition:
            print(self._task_dict)
            print(self._task_id_list)
            self._condition.notify_all()
