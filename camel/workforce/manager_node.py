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
from typing import Deque, Dict, List, Optional

from colorama import Fore

from camel.agents import ChatAgent
from camel.messages.base import BaseMessage
from camel.tasks.task import Task, TaskState
from camel.workforce.base import BaseNode
from camel.workforce.single_agent_node import SingleAgentNode
from camel.workforce.task_channel import TaskChannel
from camel.workforce.utils import (
    check_if_running,
    parse_assign_task_resp,
    parse_create_node_resp,
)
from camel.workforce.worker_node import WorkerNode
from camel.workforce.workforce_prompt import (
    ASSIGN_TASK_PROMPT,
    CREATE_NODE_PROMPT,
)


class ManagerNode(BaseNode):
    r"""A node that manages multiple nodes. It will split the task it
    receives into subtasks and assign them to the child nodes under
    it, and also handles the situation when the task fails.

    Args:
        description (str): Description of the node.
        coordinator_agent_kwargs (Optional[Dict]): Keyword arguments for the
            coordinator agent, e.g. `model`, `api_key`, `tools`, etc.
        task_agent_kwargs (Optional[Dict]): Keyword arguments for the task
            agent, e.g. `model`, `api_key`, `tools`, etc.
    """

    def __init__(
        self,
        description: str,
        children: List[BaseNode],
        coordinator_agent_kwargs: Optional[Dict] = None,
        task_agent_kwargs: Optional[Dict] = None,
    ) -> None:
        super().__init__(description)
        self._child_listening_tasks: Deque[asyncio.Task] = deque()
        self._children = children

        coord_agent_sysmsg = BaseMessage.make_assistant_message(
            role_name="Workforce Manager",
            content="You are coordinating a group of workers. A worker can be "
            "a group of agents or a single agent. Each worker is created to"
            " solve a specific kind of task. Your job includes assigning "
            "tasks to a existing worker, creating a new worker for a task, "
            "etc.",
        )
        self.coordinator_agent = ChatAgent(
            coord_agent_sysmsg, **(coordinator_agent_kwargs or {})
        )

        task_sys_msg = BaseMessage.make_assistant_message(
            role_name="Task Planner",
            content="You are going to compose and decompose tasks.",
        )
        self.task_agent = ChatAgent(task_sys_msg, **(task_agent_kwargs or {}))

        # if there is one, will set by the workforce class wrapping this
        self._task: Optional[Task] = None
        self._pending_tasks: Deque[Task] = deque()

    @check_if_running(False)
    def set_main_task(self, task: Task) -> None:
        r"""Set the main task for the node."""
        self._task = task

    def _get_child_nodes_info(self) -> str:
        r"""Get the information of all the child nodes under this node."""
        return '\n'.join(
            f'{child.node_id}: {child.description}' for child in self._children
        )

    def _find_assignee(
        self,
        task: Task,
        failed_log: Optional[str] = None,
    ) -> str:
        r"""Assigns a task to a child node if capable, otherwise create a
        new worker node.

        Parameters:
            task (Task): The task to be assigned.
            failed_log (Optional[str]): Optional log of a previous failed
                attempt.

        Returns:
            str: ID of the assigned node.
        """
        prompt = ASSIGN_TASK_PROMPT.format(
            content=task.content,
            child_nodes_info=self._get_child_nodes_info(),
        )
        req = BaseMessage.make_user_message(
            role_name="User",
            content=prompt,
        )
        response = self.coordinator_agent.step(req)
        try:
            print(f"{Fore.YELLOW}{response.msg.content}{Fore.RESET}")
            assignee_id = parse_assign_task_resp(response.msg.content)
        except ValueError:
            assignee_id = self._create_worker_node_for_task(task).node_id
        return assignee_id

    async def _post_task(self, task: Task, assignee_id: str) -> None:
        await self._channel.post_task(task, self.node_id, assignee_id)

    async def _post_dependency(self, dependency: Task) -> None:
        await self._channel.post_dependency(dependency, self.node_id)

    def _create_worker_node_for_task(self, task: Task) -> WorkerNode:
        r"""Creates a new worker node for a given task and add it to the
        children list of this node. This is one of the actions that
        the coordinator can take when a task has failed.

        Args:
            task (Task): The task for which the worker node is created.

        Returns:
            WorkerNode: The created worker node.
        """
        prompt = CREATE_NODE_PROMPT.format(
            content=task.content,
            child_nodes_info=self._get_child_nodes_info(),
        )
        req = BaseMessage.make_user_message(
            role_name="User",
            content=prompt,
        )
        response = self.coordinator_agent.step(req)
        new_node_conf = parse_create_node_resp(response.msg.content)

        worker_sysmsg = BaseMessage.make_assistant_message(
            role_name=new_node_conf.role,
            content=new_node_conf.system,
        )

        # TODO: add a default selection of tools for the worker
        worker = ChatAgent(worker_sysmsg)

        new_node = SingleAgentNode(
            description=new_node_conf.description,
            worker=worker,
        )
        new_node.set_channel(self._channel)

        print(
            f"{Fore.GREEN}New worker node {new_node.node_id} created."
            f"{Fore.RESET}"
        )

        self._children.append(new_node)
        self._child_listening_tasks.append(
            asyncio.create_task(new_node.start())
        )
        return new_node

    async def _get_returned_task(self) -> Task:
        r"""Get the task that's published by this node and just get returned
        from the assignee.
        """
        return await self._channel.get_returned_task_by_publisher(self.node_id)

    async def _post_ready_tasks(self) -> None:
        r"""Send all the pending tasks that have all the dependencies met to
        the channel, or directly return if there is none. For now, we will
        directly send the first task in the pending list because all the tasks
        are linearly dependent."""

        if not self._pending_tasks:
            return

        ready_task = self._pending_tasks[0]

        # if the task has failed previously, just compose and send the task
        # to the channel as a dependency
        if ready_task.state == TaskState.FAILED:
            # TODO: the composing of tasks seems not work very well
            ready_task.compose(self.task_agent)
            # remove the subtasks from the channel
            for subtask in ready_task.subtasks:
                await self._channel.remove_task(subtask.id)
            # send the task to the channel as a dependency
            await self._post_dependency(ready_task)
            self._pending_tasks.popleft()
            # try to send the next task in the pending list
            await self._post_ready_tasks()
        else:
            # directly post the task to the channel if it's a new one
            # find a node to assign the task
            assignee_id = self._find_assignee(task=ready_task)
            await self._post_task(ready_task, assignee_id)

    async def _handle_failed_task(self, task: Task) -> None:
        # remove the failed task from the channel
        await self._channel.remove_task(task.id)
        if task.get_depth() >= 3:
            # create a new WF and reassign
            # TODO: add a state for reassign?
            assignee = self._create_worker_node_for_task(task)
            # print('create_new_assignee:', assignee)
            await self._post_task(task, assignee.node_id)
        else:
            subtasks = task.decompose(self.task_agent)
            # Insert packets at the head of the queue
            self._pending_tasks.extendleft(reversed(subtasks))
            await self._post_ready_tasks()

    async def _handle_completed_task(self, task: Task) -> None:
        # archive the packet, making it into a dependency
        self._pending_tasks.popleft()
        await self._channel.archive_task(task.id)
        await self._post_ready_tasks()

    @check_if_running(False)
    def set_channel(self, channel: TaskChannel):
        r"""Set the channel for the node and all the child nodes under it."""
        self._channel = channel
        for child in self._children:
            child.set_channel(channel)

    @check_if_running(False)
    async def _listen_to_channel(self) -> None:
        r"""Continuously listen to the channel, post task to the channel and
        track the status of posted tasks.
        """

        self._running = True
        print(f"{Fore.GREEN}Manager node {self.node_id} started.{Fore.RESET}")

        # if this node is at the top level, it will have an initial task
        # the initial task must be decomposed into subtasks first
        if self._task is not None:
            subtasks = self._task.decompose(self.task_agent)
            self._pending_tasks.extend(subtasks)
            self._task.state = TaskState.FAILED
            self._pending_tasks.append(self._task)

        # before starting the loop, send ready pending tasks to the channel
        await self._post_ready_tasks()

        await self._channel.print_channel()

        while self._task is None or self._pending_tasks:
            returned_task = await self._get_returned_task()
            if returned_task.state == TaskState.DONE:
                await self._handle_completed_task(returned_task)
            elif returned_task.state == TaskState.FAILED:
                await self._handle_failed_task(returned_task)
            else:
                raise ValueError(
                    f"Task {returned_task.id} has an unexpected state."
                )

        # shut down the whole workforce tree
        self.stop()

    @check_if_running(False)
    async def start(self) -> None:
        r"""Start itself and all the child nodes under it."""
        for child in self._children:
            child_listening_task = asyncio.create_task(child.start())
            self._child_listening_tasks.append(child_listening_task)
        await self._listen_to_channel()

    @check_if_running(True)
    def stop(self) -> None:
        r"""Stop all the child nodes under it. The node itself will be stopped
        by its parent node.
        """
        for child in self._children:
            child.stop()
        for child_task in self._child_listening_tasks:
            child_task.cancel()
        self._running = False
