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
import asyncio
from collections import defaultdict, deque
from enum import Enum
from typing import Dict, List, Optional, Set

from camel.logger import get_logger
from camel.tasks import Task

logger = get_logger(__name__)


class PacketStatus(Enum):
    r"""The status of a packet. The packet can be in one of the following
    states:

    - ``SENT``: The packet has been sent to a worker.
    - ``PROCESSING``: The packet has been claimed by a worker and is being
    processed.
    - ``RETURNED``: The packet has been returned by the worker, meaning that
      the status of the task inside has been updated.
    - ``ARCHIVED``: The packet has been archived, meaning that the content of
      the task inside will not be changed. The task is considered
      as a dependency.
    """

    SENT = "SENT"
    PROCESSING = "PROCESSING"
    RETURNED = "RETURNED"
    ARCHIVED = "ARCHIVED"


class Packet:
    r"""The basic element inside the channel. A task is wrapped inside a
    packet. The packet will contain the task, along with the task's assignee,
    and the task's status.

    Args:
        task (Task): The task that is wrapped inside the packet.
        publisher_id (str): The ID of the workforce that published the task.
        assignee_id (str): The ID of the workforce that is assigned
            to the task. Defaults to None, meaning that the task is posted as
            a dependency in the channel.

    Attributes:
        task (Task): The task that is wrapped inside the packet.
        publisher_id (str): The ID of the workforce that published the task.
        assignee_id (Optional[str], optional): The ID of the workforce that is
            assigned to the task. Would be None if the task is a dependency.
            Defaults to None.
        status (PacketStatus): The status of the task.
    """

    def __init__(
        self,
        task: Task,
        publisher_id: str,
        assignee_id: Optional[str] = None,
        status: PacketStatus = PacketStatus.SENT,
    ) -> None:
        self.task = task
        self.publisher_id = publisher_id
        self.assignee_id = assignee_id
        self.status = status

    def __repr__(self):
        return (
            f"Packet(publisher_id={self.publisher_id}, assignee_id="
            f"{self.assignee_id}, status={self.status})"
        )


class TaskChannel:
    r"""An internal class used by Workforce to manage tasks.

    This implementation uses a hybrid data structure approach:
    - Hash map (_task_dict) for O(1) task lookup by ID
    - Status-based index (_task_by_status) for efficient filtering by status
    - Assignee/publisher queues for ordered task processing
    """

    def __init__(self) -> None:
        self._condition = asyncio.Condition()
        self._task_dict: Dict[str, Packet] = {}

        self._task_by_status: Dict[PacketStatus, Set[str]] = defaultdict(set)

        # task by assignee store which are sent to
        self._task_by_assignee: Dict[str, deque[str]] = defaultdict(deque)

        self._task_by_publisher: Dict[str, deque[str]] = defaultdict(deque)

    def _update_task_status(
        self, task_id: str, new_status: PacketStatus
    ) -> None:
        r"""Helper method to properly update task status in all indexes."""
        if task_id not in self._task_dict:
            return

        packet = self._task_dict[task_id]
        old_status = packet.status

        if old_status in self._task_by_status:
            self._task_by_status[old_status].discard(task_id)

        packet.status = new_status

        self._task_by_status[new_status].add(task_id)

    def _cleanup_task_from_indexes(self, task_id: str) -> None:
        r"""Helper method to remove a task from all indexes.

        Args:
            task_id (str): The ID of the task to remove from indexes.
        """
        if task_id not in self._task_dict:
            return

        packet = self._task_dict[task_id]

        if packet.status in self._task_by_status:
            self._task_by_status[packet.status].discard(task_id)

        if packet.assignee_id and packet.assignee_id in self._task_by_assignee:
            assignee_queue = self._task_by_assignee[packet.assignee_id]
            self._task_by_assignee[packet.assignee_id] = deque(
                task for task in assignee_queue if task != task_id
            )

        if packet.publisher_id in self._task_by_publisher:
            publisher_queue = self._task_by_publisher[packet.publisher_id]
            self._task_by_publisher[packet.publisher_id] = deque(
                task for task in publisher_queue if task != task_id
            )

    async def get_returned_task_by_publisher(self, publisher_id: str) -> Task:
        r"""Get a task from the channel that has been returned by the
        publisher.
        """
        async with self._condition:
            while True:
                task_ids = self._task_by_publisher[publisher_id]

                if task_ids:
                    task_id = task_ids.popleft()

                    if task_id in self._task_dict:
                        packet = self._task_dict[task_id]

                        if (
                            packet.status == PacketStatus.RETURNED
                            and packet.publisher_id == publisher_id
                        ):
                            # Clean up all indexes before removing
                            self._cleanup_task_from_indexes(task_id)
                            del self._task_dict[task_id]
                            self._condition.notify_all()
                            return packet.task

                await self._condition.wait()

    async def get_assigned_task_by_assignee(self, assignee_id: str) -> Task:
        r"""Atomically get and claim a task from the channel that has been
        assigned to the assignee. This prevents race conditions where multiple
        concurrent calls might retrieve the same task.
        """
        async with self._condition:
            while True:
                task_ids = self._task_by_assignee.get(assignee_id, deque())

                # Process all available tasks until we find a valid one
                while task_ids:
                    task_id = task_ids.popleft()

                    if task_id in self._task_dict:
                        packet = self._task_dict[task_id]

                        if (
                            packet.status == PacketStatus.SENT
                            and packet.assignee_id == assignee_id
                        ):
                            # Use helper method to properly update status
                            self._update_task_status(
                                task_id, PacketStatus.PROCESSING
                            )
                            self._condition.notify_all()
                            return packet.task

                await self._condition.wait()

    async def post_task(
        self, task: Task, publisher_id: str, assignee_id: str
    ) -> None:
        r"""Send a task to the channel with specified publisher and assignee,
        along with the dependency of the task."""
        async with self._condition:
            packet = Packet(task, publisher_id, assignee_id)
            self._task_dict[packet.task.id] = packet
            self._task_by_status[PacketStatus.SENT].add(packet.task.id)
            self._task_by_assignee[assignee_id].append(packet.task.id)
            self._condition.notify_all()

    async def post_dependency(
        self, dependency: Task, publisher_id: str
    ) -> None:
        r"""Post a dependency to the channel. A dependency is a task that is
        archived, and will be referenced by other tasks."""
        async with self._condition:
            packet = Packet(
                dependency, publisher_id, status=PacketStatus.ARCHIVED
            )
            self._task_dict[packet.task.id] = packet
            self._task_by_status[PacketStatus.ARCHIVED].add(packet.task.id)
            self._condition.notify_all()

    async def return_task(self, task_id: str) -> None:
        r"""Return a task to the sender, indicating that the task has been
        processed by the worker."""
        async with self._condition:
            if task_id in self._task_dict:
                packet = self._task_dict[task_id]
                # Only add to publisher queue if not already returned
                if packet.status != PacketStatus.RETURNED:
                    self._update_task_status(task_id, PacketStatus.RETURNED)
                    self._task_by_publisher[packet.publisher_id].append(
                        packet.task.id
                    )
            self._condition.notify_all()

    async def archive_task(self, task_id: str) -> None:
        r"""Archive a task in channel, making it to become a dependency."""
        async with self._condition:
            if task_id in self._task_dict:
                packet = self._task_dict[task_id]
                # Remove from assignee queue before archiving
                if (
                    packet.assignee_id
                    and packet.assignee_id in self._task_by_assignee
                ):
                    assignee_queue = self._task_by_assignee[packet.assignee_id]
                    self._task_by_assignee[packet.assignee_id] = deque(
                        task for task in assignee_queue if task != task_id
                    )
                # Update status (keeps in status index for dependencies)
                self._update_task_status(task_id, PacketStatus.ARCHIVED)
            self._condition.notify_all()

    async def remove_task(self, task_id: str) -> None:
        r"""Remove a task from the channel."""
        async with self._condition:
            # Check if task ID exists before removing
            if task_id in self._task_dict:
                # Clean up all indexes before removing
                self._cleanup_task_from_indexes(task_id)
                del self._task_dict[task_id]
            self._condition.notify_all()

    async def get_dependency_ids(self) -> List[str]:
        r"""Get the IDs of all dependencies in the channel."""
        async with self._condition:
            return list(self._task_by_status[PacketStatus.ARCHIVED])

    async def get_in_flight_tasks(self, publisher_id: str) -> List[Task]:
        r"""Get all tasks that are currently in-flight (SENT, RETURNED
        or PROCESSING) published by the given publisher.

        Args:
            publisher_id (str): The ID of the publisher whose
            in-flight tasks to retrieve.

        Returns:
            List[Task]: List of tasks that are currently in-flight.
        """
        async with self._condition:
            in_flight_tasks = []
            seen_task_ids = set()  # Track seen IDs for duplicate detection

            # Get tasks with SENT, RETURNED or PROCESSING
            # status published by this publisher
            for status in [
                PacketStatus.SENT,
                PacketStatus.PROCESSING,
                PacketStatus.RETURNED,
            ]:
                for task_id in self._task_by_status[status]:
                    if task_id in self._task_dict:
                        packet = self._task_dict[task_id]
                        if packet.publisher_id == publisher_id:
                            # Defensive check: detect if task appears in
                            # multiple status sets (should never happen)
                            if task_id in seen_task_ids:
                                logger.warning(
                                    f"Task {task_id} found in multiple "
                                    f"status sets. This indicates a bug in "
                                    f"status management."
                                )
                                continue
                            in_flight_tasks.append(packet.task)
                            seen_task_ids.add(task_id)

            return in_flight_tasks

    async def get_task_by_id(self, task_id: str) -> Task:
        r"""Get a task from the channel by its ID."""
        async with self._condition:
            packet = self._task_dict.get(task_id)
            if packet is None:
                raise ValueError(f"Task {task_id} not found.")
            return packet.task

    async def get_channel_debug_info(self) -> str:
        r"""Get the debug information of the channel."""
        async with self._condition:
            return str(self._task_dict)
