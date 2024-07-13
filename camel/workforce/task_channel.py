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
from typing import Dict, List

from camel.tasks import Task
from camel.workforce import BaseWorkforce


class _TaskStatus(Enum):
    r"""The status of a task. The task can be in one of the following states:

    - ``ASSIGNED``: The task has been assigned to a worker.
    - ``WORKING``: The task is being worked on by the worker.
    - ``COMPLETED``: The task has been completed by the worker.
    - ``FAILED``: The task has failed to be completed by the worker.
    - ``CLOSED``: The task has been closed.
    """

    ASSIGNED = "assigned"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CLOSED = "closed"


class _Packet:
    r"""The basic element inside the channel. A task is wrapped inside a
    packet. The packet will contain the task, along with the task's assignee,
    and the task's status.

    Args:
        task (Task): The task that is wrapped inside the packet.

    Attributes:
        task (Task): The task that is wrapped inside the packet.
        assignee (BaseWorkforce): The ID of the worker that is assigned to the
            task.
        status (_TaskStatus): The status of the task.
    """

    def __init__(self, task: Task, assignee: BaseWorkforce):
        self.task = task
        self.assignee = assignee
        self.status = _TaskStatus.ASSIGNED


class _TaskChannel:
    r"""An internal class used by Workforce to manage tasks."""

    def __init__(self):
        self._task_id_list: List[str] = []
        self._condition = asyncio.Condition()
        self._task_dict: Dict[str, _Packet] = {}

    async def get_finished_task(self) -> _Packet:
        async with self._condition:
            while True:
                for id in self._task_id_list:
                    packet = self._task_dict[id]
                    if packet.status in [
                        _TaskStatus.COMPLETED,
                        _TaskStatus.FAILED,
                    ]:
                        return packet
                await self._condition.wait()

    async def post_task(self, packet: _Packet) -> None:
        async with self._condition:
            self._task_id_list.append(packet.task.id)
            self._task_dict[packet.task.id] = packet
            self._condition.notify_all()

    async def update_task(self, task_id: str, status: _TaskStatus) -> None:
        async with self._condition:
            packet = self._task_dict[task_id]
            packet.status = status
            self._condition.notify_all()

    async def get_assigned_task(self, worker: BaseWorkforce) -> _Packet:
        async with self._condition:
            while True:
                for id in self._task_id_list:
                    packet = self._task_dict[id]
                    if (
                        packet.assignee == worker
                        and packet.status == _TaskStatus.ASSIGNED
                    ):
                        return packet
                await self._condition.wait()

    async def remove_task(self, task_id: str) -> None:
        async with self._condition:
            self._task_id_list.remove(task_id)
            self._task_dict.pop(task_id)
            self._condition.notify_all()

    async def get_task_by_id(self, task_id: str) -> _Packet:
        async with self._condition:
            return self._task_dict[task_id]
