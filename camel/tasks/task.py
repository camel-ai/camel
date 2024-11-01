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
from enum import Enum
from typing import Callable, Dict, List, Literal, Optional, TypedDict, Union

from pydantic import BaseModel, ConfigDict

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.prompts import TextPrompt
from camel.tasks.machine import Machine
from camel.toolkits.function_tool import FunctionTool

from .task_prompt import (
    TASK_COMPOSE_PROMPT,
    TASK_DECOMPOSE_PROMPT,
    TASK_EVOLVE_PROMPT,
)


def parse_response(
    response: str, task_id: Optional[str] = None
) -> List["Task"]:
    r"""Parse Tasks from a response.

    Args:
        response (str): The model response.
        task_id (str, optional): a parent task id,
            the default value is "0"

    Returns:
        List[Task]: A list of tasks which is :obj:`Task` instance.
    """
    pattern = "<task>(.*?)</task>"
    tasks_content = re.findall(pattern, response, re.DOTALL)

    tasks = []
    if task_id is None:
        task_id = "0"
    for i, content in enumerate(tasks_content):
        tasks.append(Task(content=content.strip(), id=f"{task_id}.{i}"))
    return tasks


class TaskState(str, Enum):
    OPEN = "OPEN"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    DELETED = "DELETED"

    @classmethod
    def states(cls):
        return [s.value for s in cls]


class Task(BaseModel):
    r"""Task is specific assignment that can be passed to a agent.

    Attributes:
        content: string content for task.
        id: An unique string identifier for the task. This should
        ideally be provided by the provider/model which created the task.
        state: The state which should be OPEN, RUNNING, DONE or DELETED.
        type: task type
        parent: The parent task, None for root task.
        subtasks: The children sub-tasks for the task.
        result: The answer for the task.
        onTaskComplete: The callback functions when the task is completed.
    """

    content: str

    id: str = ""

    state: TaskState = TaskState.OPEN

    type: Optional[str] = None

    parent: Optional["Task"] = None

    subtasks: List["Task"] = []

    result: Optional[str] = ""

    failure_count: int = 0

    additional_info: Optional[str] = None

    onTaskComplete: List[Callable[[], None]] = []

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
        self.onTaskComplete = []

    def update_result(self, result: str):
        r"""Set task result and mark the task as DONE.

        Args:
            result (str): The task result.
        """
        self.result = result
        self.set_state(TaskState.DONE)
        for callback in self.onTaskComplete or []:
            callback()

    def add_on_task_complete(
        self, callbacks: Union[Callable[[], None], List[Callable[[], None]]]
    ):
        r"""Adds one or more callbacks to the onTaskComplete list.

        Args:
            callbacks (Union[Callable[[], None], List[Callable[[], None]]]):
                A single callback function or a list of callback functions to
                be added.
        """
        if isinstance(callbacks, list):
            self.onTaskComplete.extend(callbacks)
        else:
            self.onTaskComplete.append(callbacks)

    def set_id(self, id: str):
        self.id = id

    def set_state(self, state: TaskState):
        r"""Recursively set the state of the task and its subtasks.

        Args:
            state (TaskState): The giving state.
        """
        self.state = state
        if state == TaskState.DONE:
            for subtask in self.subtasks:
                if subtask.state != TaskState.DELETED:
                    subtask.set_state(state)
        elif state == TaskState.RUNNING and self.parent:
            self.parent.set_state(state)

    def add_subtask(self, task: "Task"):
        task.parent = self
        self.subtasks.append(task)

    def remove_subtask(self, id: str):
        self.subtasks = [task for task in self.subtasks if task.id != id]

    def get_running_task(self) -> Optional["Task"]:
        r"""Get RUNNING task."""
        for sub in self.subtasks:
            if sub.state == TaskState.RUNNING:
                return sub.get_running_task()
        if self.state == TaskState.RUNNING:
            return self
        return None

    def to_string(self, indent: str = "", state: bool = False) -> str:
        r"""Convert task to a sting.

        Args:
            indent (str): The ident for hierarchical tasks.
            state (bool): Include or not task state.

        Returns:
            str: The printable task string.
        """
        if state:
            _str = f"{indent}[{self.state}] Task {self.id}: {self.content}\n"
        else:
            _str = f"{indent}Task {self.id}: {self.content}\n"
        for subtask in self.subtasks:
            _str += subtask.to_string(indent + "  ", state)
        return _str

    def get_result(self, indent: str = "") -> str:
        r"""Get task result to a sting.

        Args:
            indent (str): The ident for hierarchical tasks.

        Returns:
            str: The printable task string.
        """
        _str = f"{indent}Task {self.id} result: {self.result}\n"
        for subtask in self.subtasks:
            _str += subtask.get_result(indent + "  ")
        return _str

    def decompose(
        self,
        agent: ChatAgent,
        prompt: Optional[str] = None,
        task_parser: Callable[[str, str], List["Task"]] = parse_response,
    ) -> List["Task"]:
        r"""Decompose a task to a list of sub-tasks. It can be used for data
        generation and planner of agent.

        Args:
            agent (ChatAgent): An agent that used to decompose the task.
            prompt (str, optional): A prompt to decompose the task. If not
                provided, the default prompt will be used.
            task_parser (Callable[[str, str], List[Task]], optional): A
                function to extract Task from response. If not provided,
                the default parse_response will be used.

        Returns:
            List[Task]: A list of tasks which are :obj:`Task` instances.
        """

        role_name = agent.role_name
        content = prompt or TASK_DECOMPOSE_PROMPT.format(
            role_name=role_name,
            content=self.content,
        )
        msg = BaseMessage.make_user_message(
            role_name=role_name, content=content
        )
        response = agent.step(msg)
        tasks = task_parser(response.msg.content, self.id)
        for task in tasks:
            task.additional_info = self.additional_info
        return tasks

    def compose(
        self,
        agent: ChatAgent,
        template: TextPrompt = TASK_COMPOSE_PROMPT,
        result_parser: Optional[Callable[[str], str]] = None,
    ):
        r"""compose task result by the sub-tasks.

        Args:
            agent (ChatAgent): An agent that used to compose the task result.
            template (TextPrompt, optional): The prompt template to compose
                task. If not provided, the default template will be used.
            result_parser (Callable[[str, str], List[Task]], optional): A
                function to extract Task from response.
        """

        if not self.subtasks:
            return

        sub_tasks_result = self.get_result()

        role_name = agent.role_name
        content = template.format(
            role_name=role_name,
            content=self.content,
            additional_info=self.additional_info,
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

    def get_depth(self) -> int:
        r"""Get current task depth."""
        if self.parent is None:
            return 1
        return 1 + self.parent.get_depth()


class TaskManager:
    r"""TaskManager is used to manage tasks.

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
        self.tasks: List[Task] = []
        self.task_map: Dict[str, Task] = {}
        self.add_tasks(task)

    def gen_task_id(self) -> str:
        r"""Generate a new task id."""
        return f"{len(self.tasks)}"

    def exist(self, task_id: str) -> bool:
        r"""Check if a task with the given id exists."""
        return task_id in self.task_map

    @property
    def current_task(self) -> Optional[Task]:
        r"""Get the current task."""
        return self.task_map.get(self.current_task_id, None)

    @staticmethod
    def topological_sort(tasks: List[Task]) -> List[Task]:
        r"""Sort a list of tasks by topological way.

        Args:
            tasks (List[Task]): The giving list of tasks.

        Returns:
            The sorted list of tasks.
        """
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
        """
        # filter the root task in the others to avoid self-loop dependence.
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
        r"""self.tasks and self.task_map will be updated by the input tasks."""
        if not tasks:
            return
        tasks = tasks if isinstance(tasks, list) else [tasks]

        for task in tasks:
            assert not self.exist(task.id), f"`{task.id}` already exists."
            # Add callback to update the current task ID
            task.add_on_task_complete(
                self.create_update_current_task_id_callback(task)
            )
        self.tasks = self.topological_sort(self.tasks + tasks)
        self.task_map = {task.id: task for task in self.tasks}

    def create_update_current_task_id_callback(
        self, task: Task
    ) -> Callable[[], None]:
        r"""
        Creates a callback function to update `current_task_id` after the
        specified task is completed.

        The returned callback function, when called, sets `current_task_id` to
        the ID of the next task in the `tasks` list. If the specified task is
        the last one in the list, `current_task_id` is set to an empty string.

        Args:
            task (Task): The task after which `current_task_id` should be
                updated.

        Returns:
            Callable[[], None]:
                A callback function that, when invoked, updates
                `current_task_id` to the next task's ID or clears it if the
                specified task is the last in the list.
        """

        def update_current_task_id():
            current_index = self.tasks.index(task)

            if current_index + 1 < len(self.tasks):
                self.current_task_id = self.tasks[current_index + 1].id
            else:
                self.current_task_id = ""

        return update_current_task_id

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


class FunctionToolState(BaseModel):
    """Represents a specific state of a function tool within a state machine.

    Attributes:
        name (str): The unique name of the state, serving as an identifier.
        tools_space (Optional[List[FunctionTool]]): A list of `FunctionTool`
            objects associated with this state. Defaults to an empty list.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
    )

    name: str
    tools_space: Optional[List[FunctionTool]] = []

    def __eq__(self, other):
        if isinstance(other, FunctionToolState):
            return self.name == other.name
        return False

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class FunctionToolTransition(TypedDict):
    """Defines a transition within a function tool state machine.

    Attributes:
        trigger (Task): The task that initiates this transition.
        source (str): The name of the starting state.
        dest (str): The name of the target state after the transition.
    """

    trigger: Task
    source: FunctionToolState
    dest: FunctionToolState


class TaskManagerWithState(TaskManager):
    r"""
    A TaskManager with an integrated state machine supporting conditional
    function calls based on task states and transitions.

    Args:
        task (Task): The primary task to manage.
        states (List[FunctionToolState]): A list of all possible states.
        initial_state (str): The initial state of the machine.
        transitions (Optional[List[FunctionToolTransition]]): A list of state
            transitions, each containing a trigger, source state, and
            destination state.

    Attributes:
        state_space (List[FunctionToolState]): Collection of all states.
        machine (Machine): Manages state transitions and tracks the current
            state.
    """

    def __init__(
        self,
        task,
        initial_state: FunctionToolState,
        states: List[FunctionToolState],
        transitions: Optional[List[FunctionToolTransition]],
    ):
        super().__init__(task)
        self.state_space = states
        self.machine = Machine(
            states=[state.name for state in states],
            transitions=[],
            initial=initial_state.name,
        )

        for transition in transitions or []:
            self.add_transition(
                transition['trigger'],
                transition['source'],
                transition['dest'],
            )

    @property
    def current_state(self) -> Optional[FunctionToolState]:
        r"""
        Retrieves the current state object based on the machine's active state
        name.

        Returns:
            Optional[FunctionToolState]:
                The state object with a `name` matching `self.machine.
                current_state`, or `None` if no match is found.
        """
        for state in self.state_space:
            if state.name == self.machine.current_state:
                return state
        return None

    def add_state(self, state: FunctionToolState):
        r"""
        Adds a new state to both `state_space` and the machine.

        Args:
            state (FunctionToolState): The state object to be added.
        """
        if state not in self.state_space:
            self.state_space.append(state)
            self.machine.add_state(state.name)

    def add_transition(
        self, trigger: Task, source: FunctionToolState, dest: FunctionToolState
    ):
        r"""
        Adds a new transition to the state machine.

        Args:
            trigger (Task): The task that initiates this transition.
            source (FunctionToolState): The source state.
            dest (FunctionToolState): The destination state after the
                transition.
        """
        trigger.add_on_task_complete(lambda: self.machine.trigger(trigger.id))
        if not self.exist(trigger.id):
            self.add_tasks(trigger)
        self.machine.add_transition(trigger.id, source.name, dest.name)

    def get_current_tools(self) -> Optional[List[FunctionTool]]:
        r"""
        Retrieves the tools available in the current state.

        Returns:
            Optional[List[FunctionTool]]: The tools associated with the
                current state.
        """
        return self.current_state.tools_space

    def remove_state(self, state_name: str):
        r"""
        Removes a state from `state_space` and the machine.

        Args:
            state_name (str): The name of the state to remove.
        """
        self.state_space = [
            state for state in self.state_space if state.name != state_name
        ]
        self.machine.remove_state(state_name)

    def remove_transition(self, trigger: Task, source: FunctionToolState):
        r"""
        Removes a transition from the machine.

        Args:
            trigger (Task): The task associated with the transition to remove.
            source (FunctionToolState): The source state.
        """
        self.machine.remove_transition(trigger.id, source.name)

    def reset(self):
        r"""
        Resets the machine to its initial state.
        """
        self.machine.reset()
