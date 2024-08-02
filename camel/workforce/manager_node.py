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
from typing import Deque, Dict, Optional

from colorama import Fore

from camel.agents import ChatAgent
from camel.messages.base import BaseMessage
from camel.societies import RolePlaying
from camel.tasks.task import Task, TaskState
from camel.workforce.base import BaseNode
from camel.workforce.role_playing_node import RolePlayingNode
from camel.workforce.single_agent_node import SingleAgentNode
from camel.workforce.task_channel import TaskChannel
from camel.workforce.utils import parse_assign_task_resp, parse_create_wf_resp
from camel.workforce.worker_node import WorkerNode
from camel.workforce.workforce_prompt import (
    ASSIGN_TASK_PROMPT,
    CREATE_WF_PROMPT,
)


class ManagerNode(BaseNode):
    r"""A workforce that manages multiple workforces and agents. It will
    split the task it receives into subtasks and assign them to the
    workforces/agents under it, and also handles the situation when the task
    fails.

    Args:
        workforce_id (str): ID for the workforce.
        description (str): Description of the workforce.
        coordinator_agent_kwargs (Optional[Dict]): Keyword arguments for the
            coordinator agent, e.g. `model`, `api_key`, `tools`, etc.
        task_agent_kwargs (Optional[Dict]): Keyword arguments for the task
            agent, e.g. `model`, `api_key`, `tools`, etc.
    """

    def __init__(
            self,
            workforce_id: str,
            description: str,
            coordinator_agent_kwargs: Optional[Dict] = None,
            task_agent_kwargs: Optional[Dict] = None,
    ) -> None:
        super().__init__(workforce_id, description)
        self._child_listening_tasks: Deque[asyncio.Task] = deque()
        self._children: Deque[BaseNode] = deque()

        coord_agent_sysmsg = BaseMessage.make_assistant_message(
            role_name="Workforce Manager",
            content="You are managing a group of workforces. A workforce can "
                    "be a group of agents or a single agent. Each workforce is"
                    " created to solve a specific kind of task. Your job "
                    "includes assigning tasks to a existing workforce, "
                    "creating a new workforce for a task, etc.",
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
        self.pending_tasks: Deque[Task] = deque()

    def set_task(self, task: Task) -> None:
        r"""Set the main task for the workforce."""
        self._task = task

    def add_single_agent(self, agent: ChatAgent, description: str) -> None:
        r"""Add a single agent child worker node to the workforce."""

        single_agent = SingleAgentNode(
            node_id=str(len(self._children) + 1),
            description=description,
            worker=agent,
        )
        self._children.append(single_agent)

    def add_role_playing(
            self, role_playing: RolePlaying, description: str
    ) -> None:
        r"""Add a role playing child worker node to the workforce."""
        role_playing_agent = RolePlayingNode(
            node_id=str(len(self.child_workforces) + 1),
            description=description,
            role_playing=role_playing,
        )

    def _get_workforces_info(self) -> str:
        r"""Get the information of all the workforces under this workforce."""
        return '\n'.join(
            f'{workforce.node_id}: {workforce.description}'
            for workforce in self.child_workforces
        )

    def _find_assignee(
            self,
            task: Task,
            failed_log: Optional[str] = None,
    ) -> str:
        r"""Assigns a task to an internal workforce if capable, otherwise
        create a new workforce.

        Parameters:
            task (Task): The task to be assigned.
            failed_log (Optional[str]): Optional log of a previous failed
                attempt.

        Returns:
            str: ID of the assigned workforce.
        """
        prompt = ASSIGN_TASK_PROMPT.format(
            content=task.content,
            workforces_info=self._get_workforces_info(),
        )
        req = BaseMessage.make_user_message(
            role_name="User",
            content=prompt,
        )
        response = self.coordinator_agent.step(req)
        try:
            assign_id = parse_assign_task_resp(response.msg.content)
        except Exception:
            assign_id = self._create_workforce_for_task(task).node_id
        return assign_id

    async def _post_task(self, task: Task, assignee_id: str) -> None:
        await self._channel.post_task(task, self.node_id, assignee_id)

    async def _post_dependency(self, dependency: Task) -> None:
        await self._channel.post_dependency(dependency, self.node_id)

    def _create_workforce_for_task(self, task: Task) -> WorkerNode:
        r"""Creates a new workforce for a given task and add it to the
        workforce list of this workforce. This is one of the actions that
        the manager can take when a task has failed.

        Args:
            task (Task): The task for which the workforce is created.

        Returns:
            WorkerNode: The created workforce.
        """
        prompt = CREATE_WF_PROMPT.format(
            content=task.content,
            workforces_info=self._get_workforces_info(),
        )
        req = BaseMessage.make_user_message(
            role_name="User",
            content=prompt,
        )
        response = self.coordinator_agent.step(req)
        new_wf_conf = parse_create_wf_resp(response.msg.content)

        worker_msg = BaseMessage.make_assistant_message(
            role_name=new_wf_conf.role,
            content=new_wf_conf.system,
        )

        worker = ChatAgent(worker_msg)

        new_workforce = SingleAgentNode(
            node_id=str(len(self._children) + 1),
            description=new_wf_conf.description,
            worker=worker,
        )
        new_workforce.set_channel(self._channel)

        self._children.append(new_workforce)
        return new_workforce

    async def _get_returned_task(self) -> Task:
        r"""Get the task that's published by this workforce and just get
        returned from the assignee."""
        return await self._channel.get_returned_task_by_publisher(
            self.node_id
        )

    async def _post_ready_tasks(self) -> None:
        r"""Send all the pending tasks that have all the dependencies met to
        the channel, or directly return if there is none. For now, we will
        directly send the first task in the pending list because all the tasks
        are linearly dependent."""

        if not self.pending_tasks:
            return

        ready_task = self.pending_tasks[0]

        # if the task has failed previously, just compose and send the task
        # to the channel as a dependency
        if ready_task.state == TaskState.FAILED:
            ready_task.compose(self.task_agent)
            # remove the subtasks from the channel
            for subtask in ready_task.subtasks:
                await self._channel.remove_task(subtask.id)
            # send the task to the channel as a dependency
            await self._post_dependency(ready_task)
            self.pending_tasks.popleft()
            # try to send the next task in the pending list
            await self._post_ready_tasks()
        else:
            # directly post the task to the channel if it's a new one
            # find a workforce to assign the task
            assignee_id = self._find_assignee(task=ready_task)
            await self._post_task(ready_task, assignee_id)

    async def _handle_failed_task(self, task: Task) -> None:
        # remove the failed task from the channel
        await self._channel.remove_task(task.id)
        if task.get_depth() >= 3:
            # create a new WF and reassign
            # TODO: add a state for reassign?
            assignee = self._create_workforce_for_task(task)
            # print('create_new_assignee:', assignee)
            await self._post_task(task, assignee.node_id)
        else:
            subtasks = task.decompose(self.task_agent)
            # Insert packets at the head of the queue
            self.pending_tasks.extendleft(reversed(subtasks))
            await self._post_ready_tasks()

    async def _handle_completed_task(self, task: Task) -> None:
        # archive the packet, making it into a dependency
        self.pending_tasks.popleft()
        await self._channel.archive_task(task.id)
        await self._post_ready_tasks()

    def set_channel(self, channel: TaskChannel):
        r"""Set the channel for the workforce and all the workforces under it.
        """
        if self._running:
            print(f"{Fore.YELLOW} Warning: Node {self.node_id} is already "
                  f"running. Channel is not set. {Fore.RESET}")
            return

        self._channel = channel
        for workforce in self._children:
            workforce.set_channel(channel)

    async def _listen_to_channel(self) -> None:
        r"""Continuously listen to the channel, post task to the channel and
        track the status of posted tasks.
        """


        print(f'listening {self.node_id}')

        # if this workforce is at the top level, it will have an initial task
        # the initial task must be decomposed into subtasks first
        if self._task is not None:
            subtasks = self._task.decompose(self.task_agent)
            self.pending_tasks.extend(subtasks)
            self._task.state = TaskState.FAILED
            self.pending_tasks.append(self._task)

        # before starting the loop, send ready pending tasks to the channel
        await self._post_ready_tasks()

        while self._task is None or self.pending_tasks:
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
        await self.stop()

    async def start(self) -> None:
        r"""Start the internal workforce and all the workforces under it."""
        for workforce in self._children:
            child_listening_task = asyncio.create_task(workforce.start())
            self._child_listening_tasks.append(child_listening_task)
        print('start listening...')
        self._running = True
        await self._listen_to_channel()

    async def stop(self) -> None:
        r"""Cancel all the workforces under this workforce and return."""
        for workforce in self._children:
            await workforce.stop()
        for child_task in self._child_listening_tasks:
            child_task.cancel()
        self._running = False
