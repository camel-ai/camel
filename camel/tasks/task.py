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

import re
from enum import Enum
from typing import Callable, Dict, List, Literal, Optional, Union

from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.prompts import TextPrompt

from .task_prompt import (
    TASK_COMPOSE_PROMPT,
    TASK_DECOMPOSE_PROMPT,
    TASK_EVOLVE_PROMPT,
)


class TaskState(str, Enum):
    OPEN = "OPEN"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    DELETED = "DELETED"

    @classmethod
    def states(cls):
        return [s.value for s in cls]


def parse_response(response: str, task_id: Optional[str] = None) -> List[Task]:
    pattern = "<task>(.*?)</task>"
    tasks_content = re.findall(pattern, response, re.DOTALL)

    tasks = []
    if task_id is None:
        task_id = "0"
    for i, content in enumerate(tasks_content):
        tasks.append(Task(content=content.strip(), id=f"{task_id}.{i}"))
    return tasks


class Task(BaseModel):
    """
    Task is specific assignment that can be passed to a agent.

    Attributes:
        content: string content for task.
        id: A unique id.
        state: The state which should be OPEN, RUNNING, DONE or DELETED.
        type: task type
        parent: The parent task, None for root task.
        subtasks: The childrent sub-tasks for the task.
        result: The answer for the task.
    """

    content: str
    """The content of the task."""

    id: str = ""
    """An unique string identifier for the task. This should ideally be
    provided by the provider/model which created the task."""

    state: TaskState = TaskState.OPEN
    """The task state.
    """

    type: Optional[str] = None
    """The type of a task.
    """

    parent: Optional["Task"] = None
    """The parent task.
    """

    subtasks: List["Task"] = []
    """A list of sub tasks.
    """

    result: Optional[str] = ""

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
        self.state = TaskState.OPEN
        self.result = ""

    def update_result(self, result: str):
        self.result = result
        self.set_state(TaskState.DONE)

    def set_id(self, id: str):
        self.id = id

    def set_state(self, state: TaskState):
        self.state = state
        if state == TaskState.DONE:
            for subtask in self.subtasks:
                if subtask.state != TaskState.DELETED:
                    subtask.set_state(state)
        elif state == TaskState.RUNNING:
            if self.parent is not None:
                self.parent.set_state(state)

    def add_subtask(self, task: "Task"):
        task.parent = self
        self.subtasks.append(task)

    def remove_subtask(self, id: str):
        self.subtasks = [task for task in self.subtasks if task.id != id]

    def get_running_task(self) -> Optional["Task"]:
        for sub in self.subtasks:
            if sub.state == TaskState.RUNNING:
                return sub.get_running_task()
        if self.state == TaskState.RUNNING:
            return self
        return None

    def to_string(self, indent="", state=False) -> str:
        if state:
            _str = f"{indent}[{self.state}] Task {self.id}: {self.content}\n"
        else:
            _str = f"{indent}Task {self.id}: {self.content}\n"
        for subtask in self.subtasks:
            _str += subtask.to_string(indent + "  ", state)
        return _str

    def get_result(self, indent="") -> str:
        _str = f"{indent}Task {self.id} result: {self.result}\n"
        for subtask in self.subtasks:
            _str += subtask.get_result(indent + "  ")
        return _str

    def decompose(
        self,
        agent: ChatAgent,
        template: TextPrompt = TASK_DECOMPOSE_PROMPT,
        task_parser: Callable[[str, str], List[Task]] = parse_response,
    ) -> List[Task]:
        r"""Decompose self task to a list of sub-tasks.
            It can be used for data generation and planner of agent.
        Args:
            agent (ChatAgent): An agent that used to decompose the task.
            template (TextPrompt): The prompt template to decompose
                task. If not provided, the default template will be used.
            task_parser (Callable[[str, str], List[Task]], optional): A
                function to extract Task from response. If not provided,
                the default parse_response will be used.

        Returns:
            List[Task]: A list of tasks which is :obj:`Task` instance.
        """

        role_name = agent.role_name
        content = template.format(
            role_name=role_name,
            content=self.content,
        )
        msg = BaseMessage.make_user_message(
            role_name=role_name, content=content
        )
        response = agent.step(msg)
        tasks = task_parser(response.msg.content, self.id)
        return tasks

    def compose(
        self,
        agent: ChatAgent,
        template: TextPrompt = TASK_COMPOSE_PROMPT,
        result_parser: Optional[Callable[[str], str]] = None,
    ):
        r"""compose self task result by the sub-tasks.
        Args:
            agent (ChatAgent): An agent that used to compose the task result.
            template (TextPrompt, optional): The prompt template to compose
                task. If not provided, the default template will be used.
            result_parser (Callable[[str, str], List[Task]], optional): A
                function to extract Task from response.

        Returns:
            None
        """
        if not self.subtasks:
            return

        sub_tasks_result = self.get_result()

        role_name = agent.role_name
        content = template.format(
            role_name=role_name,
            content=self.content,
            other_results=sub_tasks_result,
        )
        msg = BaseMessage.make_user_message(
            role_name=role_name, content=content
        )
        response = agent.step(msg)
        result = response.msg.content
        if result_parser:
            result = result_parser(result)
        self.update_result(result)

        return None

    def get_layer(self):
        if self.parent is None:
            return 1
        return self.parent.get_layer() + 1


class TaskManager:
    """
    TaskManager is used to manage tasks.

    Attributes:
        root_task: The root task.
        tasks: The ordered tasks.
        task_map: A map for task.id to Task.
        current_task_id: The current "RUNNING" task.id.

    Args:
        task (Task): The root Task.
    """

    def __init__(self, task: Task):
        self.root_task: Task = task
        self.current_task_id: str = task.id
        self.tasks: List[Task] = [task]
        self.task_map: Dict[str, Task] = {task.id: task}

    def gen_task_id(self) -> str:
        return f"{len(self.tasks)}"

    def exist(self, task_id: str) -> bool:
        return task_id in self.task_map

    @property
    def current_task(self) -> Optional[Task]:
        return self.task_map.get(self.current_task_id, None)

    @staticmethod
    def topological_sort(tasks: List[Task]) -> List[Task]:
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

    @staticmethod
    def set_tasks_dependence(
        root: Task,
        others: List[Task],
        type: Literal["serial", "parallel"] = "parallel",
    ):
        r"""Set relationship between root task and other tasks.
        Two relationships are currently supported: serial and parallel.
        `serial` :  root -> other1 -> other2
        `parallel`: root -> other1
                         -> other2
        Args:
            root (Task): A root task.
            others (List[Task]): A list of tasks.

        Returns:
            None
        """
        # filter the root task in the others to void self-loop dependence.
        others = [other for other in others if other != root]

        if len(others) == 0:
            return
        if type == "parallel":
            for other in others:
                root.add_subtask(other)
        else:
            parent = root
            for child in others:
                parent.add_subtask(child)
                parent = child

    def add_tasks(self, tasks: Union[Task, List[Task]]) -> None:
        r"""
        self.tasks and self.task_map will be updated by the input tasks.
        """
        if not tasks:
            return
        if not isinstance(tasks, List):
            tasks = [tasks]
        for task in tasks:
            assert not self.exist(task.id), f"`{task.id}` already existed."
        self.tasks = self.topological_sort(self.tasks + tasks)
        self.task_map = {task.id: task for task in self.tasks}

    def evolve(
        self,
        task: Task,
        agent: ChatAgent,
        template: Optional[TextPrompt] = None,
        task_parser: Optional[Callable[[str, str], List[Task]]] = None,
    ) -> Optional[Task]:
        r"""Evolve a task to a new task.
            Evolve is only used for data generation.
        Args:
            task (Task): A given task.
            agent (ChatAgent): An agent that used to evolve the task.
            template (TextPrompt, optional): A prompt template to evolve task.
                If not provided, the default template will be used.
            task_parser (Callable, optional): A function to extract Task from
                response. If not provided, the default parser will be used.

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
        if task_parser is None:
            task_parser = parse_response
        tasks = task_parser(response.msg.content, task.id)
        if tasks:
            return tasks[0]
        return None
