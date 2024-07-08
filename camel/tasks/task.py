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

import re
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.prompts import TextPrompt

from .task_prompt import TASK_DECOMPOSE_PROMPT, TASK_EVOLVE_PROMPT

TASK_STATES = {"OPEN", "RUNNING", "DONE", "DELETED"}


class Task(BaseModel):
    """
    Task is specific assignment that can be passed to a agent.

    Attributes:
        content: string content for task.
        id: A unique id.
        state: The state which should be OPEN, RUNNING, DONE or DELETED.
        parent: The parent task, None for root task.
        subtasks: The childrent sub-tasks for the task.
        result: The answer for the task.
    """

    content: str
    """The content of the task."""

    id: str
    """An unique string identifier for the task. This should ideally be
    provided by the provider/model which created the task."""

    state: Literal["OPEN", "RUNNING", "DONE", "DELETED"] = "OPEN"
    """The task state.
    """

    parent: Optional["Task"] = None
    """The parent task.
    """

    subtasks: List["Task"] = []
    """A list of sub tasks.
    """

    result: str = ""

    @classmethod
    def from_message(cls, message: BaseMessage) -> "Task":
        r"""Create a task from a message.

        Args:
            message (BaseMessage): The message to the task.

        Returns:
            Task
        """
        return cls(content=message.content, id="0")

    @staticmethod
    def to_message():
        r"""Convert a Task to a Message."""
        # TODO
        pass

    def reset(self):
        r"""Reset Task to initial state."""
        self.state = "OPEN"
        self.result = ""

    def update_task_result(self, message: BaseMessage):
        self.result = message.content
        self.state = "DONE"

    def set_id(self, id: str):
        self.id = id

    def set_state(self, state: Literal["OPEN", "RUNNING", "DONE", "DELETED"]):
        assert state in TASK_STATES, f"Invalid state `{state}`"

        self.state = state
        if state == "DONE":
            for subtask in self.subtasks:
                if subtask.state != "DELETED":
                    subtask.set_state(state)
        elif state == "RUNNING":
            if self.parent is not None:
                self.parent.set_state(state)

    def add_subtask(self, task: "Task"):
        task.parent = self
        self.subtasks.append(task)

    def get_running_task(self) -> Optional["Task"]:
        for sub in self.subtasks:
            if sub.state == "RUNNING":
                return sub.get_running_task()
        if self.state == "RUNNING":
            return self
        return None

    def to_string(self, indent="") -> str:
        _str = f"{indent}Task {self.id}: {self.content}\n"
        for subtask in self.subtasks:
            _str += subtask.to_string(indent + "  ")
        return _str


def parse_response(response: str, task_id: Optional[str]) -> List[Task]:
    pattern = "<task>(.*?)</task>"
    tasks_content = re.findall(pattern, response, re.DOTALL)

    tasks = []
    if task_id is None:
        task_id = "0"
    for i, content in enumerate(tasks_content):
        tasks.append(Task(content=content.strip(), id=f"{task_id}.{i}"))
    return tasks


class TaskManager:
    """
    TaskManager is used to manage tasks.

    Attributes:
        root_task: The root task.
        tasks: The ordered tasks.
        task_map: A map for task.id to Task.
        current_task_id: The current "RUNNING" task.id.
    """

    def __init__(self, task: Task):
        self.root_task: Task = task
        self.current_task_id: str = task.id
        self.tasks: List[Task] = [task]
        self.task_map: Dict[str, Task] = {task.id: task}

    def is_taskid_existed(self, task_id: str) -> bool:
        return task_id in self.task_map

    @property
    def current_task(self) -> Optional[Task]:
        return self.task_map.get(self.current_task_id, None)

    @staticmethod
    def _topological_sort(tasks: List[Task]) -> List[Task]:
        stack = []
        visited = set()

        # recursive visit the vertices
        def visit(task: Task):
            if task.id in visited:
                return
            visited.add(task.id)

            # go deep for dependencies
            for sub_task in task.subtasks:
                visit(sub_task)

            # add current task to stack which have no dependencies.
            stack.append(task)

        for task in tasks:
            visit(task)

        return stack

    def add_tasks(self, tasks: Union[Task, List[Task]]) -> None:
        r"""
        self.tasks and self.task_map will be updated by the input tasks.
        """
        if not tasks:
            return
        if not isinstance(tasks, List):
            tasks = [tasks]
        for task in tasks:
            assert not self.is_taskid_existed(
                task.id
            ), f"`{task.id}` already existed."
        self.tasks = self._topological_sort(self.tasks + tasks)
        self.task_map = {task.id: task for task in self.tasks}

    def evolve(
        self,
        task: Task,
        agent: ChatAgent,
        template: Optional[TextPrompt] = None,
    ) -> Optional[Task]:
        r"""Evolve a task to a new task.

        Args:
            task (Task): A giving task.
            agent (ChatAgent): An agent that used to evolve the task.
            template (TextPrompt or None): a prompt template to evolve task.

        Returns:
            Task: The created :obj:`Task` instance or None.
        """

        if template is None:
            template = TASK_EVOLVE_PROMPT

        role_name = agent.role_name
        content = template.format(role_name=role_name, content=task.content)
        msg = BaseMessage.make_user_message(
            role_name=role_name, content=content
        )
        response = agent.step(msg)

        tasks = parse_response(response.msg.content, task_id=task.id)
        if tasks:
            return tasks[0]
        return None

    def decompose(
        self,
        task: Task,
        agent: ChatAgent,
        template: Optional[TextPrompt] = None,
    ) -> List[Task]:
        r"""Decompose a task to a list of sub-tasks.

        Args:
            task (Task): A giving task.
            agent (ChatAgent): An agent that used to evolve the task.
            template (TextPrompt or None): a prompt template to evolve task.

        Returns:
            List[Task]: A list of tasks which is :obj:`Task` instance.
        """

        if template is None:
            template = TASK_DECOMPOSE_PROMPT

        role_name = agent.role_name
        content = template.format(role_name=role_name, content=task.content)
        msg = BaseMessage.make_user_message(
            role_name=role_name, content=content
        )
        response = agent.step(msg)
        tasks = parse_response(response.msg.content, task_id=task.id)
        return tasks
