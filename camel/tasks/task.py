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

import re
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Literal,
    Optional,
    Union,
)

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from camel.agents import ChatAgent
    from camel.agents.chat_agent import StreamingChatAgentResponse
import uuid

from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.prompts import TextPrompt

# Note: validate_task_content moved here to avoid circular imports
from .task_prompt import (
    TASK_COMPOSE_PROMPT,
    TASK_DECOMPOSE_PROMPT,
    TASK_EVOLVE_PROMPT,
)

logger = get_logger(__name__)


class TaskValidationMode(Enum):
    r"""Validation modes for different use cases."""

    INPUT = "input"  # For validating task content before processing
    OUTPUT = "output"  # For validating task results after completion


def validate_task_content(
    content: str,
    task_id: str = "unknown",
    min_length: int = 1,
    mode: TaskValidationMode = TaskValidationMode.INPUT,
    check_failure_patterns: bool = True,
) -> bool:
    r"""Unified validation for task content and results to avoid silent
    failures. Performs comprehensive checks to ensure content meets quality
    standards.

    Args:
        content (str): The task content or result to validate.
        task_id (str): Task ID for logging purposes.
            (default: :obj:`"unknown"`)
        min_length (int): Minimum content length after stripping whitespace.
            (default: :obj:`1`)
        mode (TaskValidationMode): Validation mode - INPUT for task content,
            OUTPUT for task results. (default: :obj:`TaskValidationMode.INPUT`)
        check_failure_patterns (bool): Whether to check for failure indicators
            in the content. Only effective in OUTPUT mode.
            (default: :obj:`True`)

    Returns:
        bool: True if content passes validation, False otherwise.
    """
    # 1: Content must not be None
    if content is None:
        logger.warning(f"Task {task_id}: None content rejected")
        return False

    # 2: Content must not be empty after stripping whitespace
    stripped_content = content.strip()
    if not stripped_content:
        logger.warning(
            f"Task {task_id}: Empty or whitespace-only content rejected."
        )
        return False

    # 3: Content must meet minimum meaningful length
    if len(stripped_content) < min_length:
        logger.warning(
            f"Task {task_id}: Content too short ({len(stripped_content)} "
            f"chars < {min_length} minimum). Content preview: "
            f"'{stripped_content}'"
        )
        return False

    # 4: For OUTPUT mode, check for failure patterns if enabled
    if mode == TaskValidationMode.OUTPUT and check_failure_patterns:
        content_lower = stripped_content.lower()

        # Check for explicit failure indicators
        failure_indicators = [
            "i cannot complete",
            "i cannot do",
            "task failed",
            "unable to complete",
            "cannot be completed",
            "failed to complete",
            "i cannot",
            "not possible",
            "impossible to",
            "cannot perform",
        ]

        if any(indicator in content_lower for indicator in failure_indicators):
            logger.warning(
                f"Task {task_id}: Failure indicator detected in result. "
                f"Content preview: '{stripped_content}'"
            )
            return False

        # Check for responses that are just error messages or refusals
        if content_lower.startswith(("error", "failed", "cannot", "unable")):
            logger.warning(
                f"Task {task_id}: Error/refusal pattern detected at start. "
                f"Content preview: '{stripped_content}'"
            )
            return False

    # All validation checks passed
    logger.debug(
        f"Task {task_id}: {mode.value} validation passed "
        f"({len(stripped_content)} chars)"
    )
    return True


def is_task_result_insufficient(task: "Task") -> bool:
    r"""Check if a task result is insufficient and should be treated as failed.

    This is a convenience wrapper around validate_task_content for backward
    compatibility and semantic clarity when checking task results.

    Args:
        task (Task): The task to check.

    Returns:
        bool: True if the result is insufficient, False otherwise.
    """
    if not hasattr(task, 'result') or task.result is None:
        return True

    return not validate_task_content(
        content=task.result,
        task_id=task.id,
        mode=TaskValidationMode.OUTPUT,
        check_failure_patterns=True,
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
    for i, content in enumerate(tasks_content, 1):
        stripped_content = content.strip()
        # validate subtask content before creating the task
        if validate_task_content(stripped_content, f"{task_id}.{i}"):
            tasks.append(Task(content=stripped_content, id=f"{task_id}.{i}"))
        else:
            logger.warning(
                f"Skipping invalid subtask {task_id}.{i} "
                f"during decomposition: "
                f"Content '{stripped_content}' failed validation"
            )
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
        content (str): string content for task.
        id (str): An unique string identifier for the task. This should
            ideally be provided by the provider/model which created the task.
            (default: :obj:`uuid.uuid4()`)
        state (TaskState): The state which should be OPEN, RUNNING, DONE or
            DELETED. (default: :obj:`TaskState.FAILED`)
        type (Optional[str]): task type. (default: :obj:`None`)
        parent (Optional[Task]): The parent task, None for root task.
            (default: :obj:`None`)
        subtasks (List[Task]): The childrent sub-tasks for the task.
            (default: :obj:`[]`)
        result (Optional[str]): The answer for the task.
            (default: :obj:`""`)
        failure_count (int): The failure count for the task.
            (default: :obj:`0`)
        assigned_worker_id (Optional[str]): The ID of the worker assigned to
            this task. (default: :obj:`None`)
        dependencies (List[Task]): The dependencies for the task.
            (default: :obj:`[]`)
        additional_info (Optional[Dict[str, Any]]): Additional information for
            the task. (default: :obj:`None`)
        image_list (Optional[List[Union[Image.Image, str]]]): Optional list
            of PIL Image objects or image URLs (strings) associated with the
            task. (default: :obj:`None`)
        image_detail (Literal["auto", "low", "high"]): Detail level of the
            images associated with the task. (default: :obj:`auto`)
        video_bytes (Optional[bytes]): Optional bytes of a video associated
            with the task. (default: :obj:`None`)
        video_detail (Literal["auto", "low", "high"]): Detail level of the
            videos associated with the task. (default: :obj:`auto`)
    """

    content: str

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    state: TaskState = (
        TaskState.FAILED
    )  # TODO: Add logic for OPEN in workforce.py

    type: Optional[str] = None

    parent: Optional["Task"] = None

    subtasks: List["Task"] = []

    result: Optional[str] = ""

    failure_count: int = 0

    assigned_worker_id: Optional[str] = None

    dependencies: List["Task"] = []

    additional_info: Optional[Dict[str, Any]] = None

    image_list: Optional[List[Union[Image.Image, str]]] = None

    image_detail: Literal["auto", "low", "high"] = "auto"

    video_bytes: Optional[bytes] = None

    video_detail: Literal["auto", "low", "high"] = "auto"

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __repr__(self) -> str:
        r"""Return a string representation of the task."""
        content_preview = self.content
        return (
            f"Task(id='{self.id}', content='{content_preview}', "
            f"state='{self.state.value}')"
        )

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
        self.state = (
            TaskState.FAILED
        )  # TODO: Add logic for OPEN in workforce.py
        self.result = ""

    def update_result(self, result: str):
        r"""Set task result and mark the task as DONE.

        Args:
            result (str): The task result.
        """
        self.result = result
        self.set_state(TaskState.DONE)

    def set_id(self, id: str):
        r"""Set the id of the task.

        Args:
            id (str): The id of the task.
        """
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
        r"""Add a subtask to the current task.

        Args:
            task (Task): The subtask to be added.
        """
        task.parent = self
        self.subtasks.append(task)

    def remove_subtask(self, id: str):
        r"""Remove a subtask from the current task.

        Args:
            id (str): The id of the subtask to be removed.
        """
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
        r"""Convert task to a string.

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
        r"""Get task result to a string.

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
        agent: "ChatAgent",
        prompt: Optional[str] = None,
        task_parser: Callable[[str, str], List["Task"]] = parse_response,
    ) -> Union[List["Task"], Generator[List["Task"], None, None]]:
        r"""Decompose a task to a list of sub-tasks. Automatically detects
        streaming or non-streaming based on agent configuration.

        Args:
            agent (ChatAgent): An agent that used to decompose the task.
            prompt (str, optional): A prompt to decompose the task. If not
                provided, the default prompt will be used.
            task_parser (Callable[[str, str], List[Task]], optional): A
                function to extract Task from response. If not provided,
                the default parse_response will be used.

        Returns:
            Union[List[Task], Generator[List[Task], None, None]]: If agent is
                configured for streaming, returns a generator that yields lists
                of new tasks as they are parsed. Otherwise returns a list of
                all tasks.
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

        # Auto-detect streaming based on response type
        from camel.agents.chat_agent import StreamingChatAgentResponse

        if isinstance(response, StreamingChatAgentResponse):
            return self._decompose_streaming(response, task_parser)
        else:
            return self._decompose_non_streaming(response, task_parser)

    def _decompose_streaming(
        self,
        response: "StreamingChatAgentResponse",
        task_parser: Callable[[str, str], List["Task"]],
    ) -> Generator[List["Task"], None, None]:
        r"""Handle streaming response for task decomposition.

        Args:
            response: Streaming response from agent
            task_parser: Function to parse tasks from response

        Yields:
            List[Task]: New tasks as they are parsed from streaming response
        """
        accumulated_content = ""
        yielded_count = 0

        # Process streaming response
        for chunk in response:
            accumulated_content = chunk.msg.content

            # Try to parse partial tasks from accumulated content
            try:
                current_tasks = self._parse_partial_tasks(accumulated_content)

                # Yield new tasks if we have more than previously yielded
                if len(current_tasks) > yielded_count:
                    new_tasks = current_tasks[yielded_count:]
                    for task in new_tasks:
                        task.additional_info = self.additional_info
                        task.parent = self
                    yield new_tasks
                    yielded_count = len(current_tasks)

            except Exception:
                # If parsing fails, continue accumulating
                continue

        # Final complete parsing
        final_tasks = task_parser(accumulated_content, self.id)
        for task in final_tasks:
            task.additional_info = self.additional_info
            task.parent = self
        self.subtasks = final_tasks

    def _decompose_non_streaming(
        self, response, task_parser: Callable[[str, str], List["Task"]]
    ) -> List["Task"]:
        r"""Handle non-streaming response for task decomposition.

        Args:
            response: Regular response from agent
            task_parser: Function to parse tasks from response

        Returns:
            List[Task]: All parsed tasks
        """
        tasks = task_parser(response.msg.content, self.id)
        for task in tasks:
            task.additional_info = self.additional_info
            task.parent = self
        self.subtasks = tasks
        return tasks

    def _parse_partial_tasks(self, response: str) -> List["Task"]:
        r"""Parse tasks from potentially incomplete response.

        Args:
            response: Partial response content

        Returns:
            List[Task]: Tasks parsed from complete <task></task> blocks
        """
        pattern = r"<task>(.*?)</task>"
        tasks_content = re.findall(pattern, response, re.DOTALL)

        tasks = []
        task_id = self.id or "0"

        for i, content in enumerate(tasks_content, 1):
            stripped_content = content.strip()
            if validate_task_content(stripped_content, f"{task_id}.{i}"):
                tasks.append(
                    Task(content=stripped_content, id=f"{task_id}.{i}")
                )
            else:
                logger.warning(
                    f"Skipping invalid subtask {task_id}.{i} "
                    f"during streaming decomposition: "
                    f"Content '{stripped_content}' failed validation"
                )
        return tasks

    def compose(
        self,
        agent: "ChatAgent",
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
            image_list=self.image_list,
            image_detail=self.image_detail,
            video_bytes=self.video_bytes,
            video_detail=self.video_detail,
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
        self.tasks: List[Task] = [task]
        self.task_map: Dict[str, Task] = {task.id: task}

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
        if not isinstance(tasks, List):
            tasks = [tasks]
        for task in tasks:
            assert not self.exist(task.id), f"`{task.id}` already existed."
        self.tasks = self.topological_sort(self.tasks + tasks)
        self.task_map = {task.id: task for task in self.tasks}

    def evolve(
        self,
        task: Task,
        agent: "ChatAgent",
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
            role_name=role_name,
            content=content,
            image_list=task.image_list,
            image_detail=task.image_detail,
            video_bytes=task.video_bytes,
            video_detail=task.video_detail,
        )
        response = agent.step(msg)
        if task_parser is None:
            task_parser = parse_response
        tasks = task_parser(response.msg.content, task.id)
        if tasks:
            return tasks[0]
        return None
