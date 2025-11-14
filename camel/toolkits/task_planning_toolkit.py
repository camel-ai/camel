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
import uuid
from typing import List, Optional

from camel.logger import get_logger
from camel.tasks import Task
from camel.toolkits import BaseToolkit, FunctionTool

logger = get_logger(__name__)


class TaskPlanningToolkit(BaseToolkit):
    r"""A toolkit for task decomposition and re-planning."""

    def __init__(
        self,
        timeout: Optional[float] = None,
    ):
        r"""Initialize the TaskPlanningToolkit.

        Args:
            timeout (Optional[float]): The timeout for the toolkit.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

    def decompose_task(
        self,
        original_task_content: str,
        sub_task_contents: List[str],
        original_task_id: Optional[str] = None,
    ) -> List[Task]:
        r"""Use the tool to decompose an original task into several sub-tasks.
        It creates new Task objects from the provided original task content,
        used when the original task is complex and needs to be decomposed.

        Args:
            original_task_content (str): The content of the task to be
                decomposed.
            sub_task_contents (List[str]): A list of strings, where each
                string is the content for a new sub-task.
            original_task_id (Optional[str]): The id of the task to be
                decomposed. If not provided, a new id will be generated.
                (default: :obj:`None`)

        Returns:
            List[Task]: A list of newly created sub-task objects.
        """
        # Create the original task object from its content
        original_task = Task(
            content=original_task_content,
            id=original_task_id if original_task_id else str(uuid.uuid4()),
        )

        new_tasks: List[Task] = []
        for i, content in enumerate(sub_task_contents):
            new_task = Task(
                content=content,
                id=f"{original_task.id}.{i}",
                parent=original_task,
            )
            new_tasks.append(new_task)
            original_task.subtasks.append(new_task)

        logger.debug(
            f"Decomposed task (content: '{original_task.content[:50]}...', "
            f"id: {original_task.id}) into {len(new_tasks)} sub-tasks: "
            f"{[task.id for task in new_tasks]}"
        )

        return new_tasks

    def replan_tasks(
        self,
        original_task_content: str,
        sub_task_contents: List[str],
        original_task_id: Optional[str] = None,
    ) -> List[Task]:
        r"""Use the tool to re_decompose a task into several subTasks.
        It creates new Task objects from the provided original task content,
        used when the decomposed tasks are not good enough to help finish
        the task.

        Args:
            original_task_content (str): The content of the task to be
                decomposed.
            sub_task_contents (List[str]): A list of strings, where each
                string is the content for a new sub-task.
            original_task_id (Optional[str]): The id of the task to be
                decomposed. (default: :obj:`None`)

        Returns:
            List[Task]: Reordered or modified tasks.
        """
        original_task = Task(
            content=original_task_content,
            id=original_task_id if original_task_id else str(uuid.uuid4()),
        )

        new_tasks: List[Task] = []
        for i, content in enumerate(sub_task_contents):
            new_task = Task(
                content=content,
                id=f"{original_task.id}.{i}",
                parent=original_task,
            )
            new_tasks.append(new_task)
            original_task.subtasks.append(new_task)

        logger.debug(
            f"RePlan task (content: '{original_task.content[:50]}...', "
            f"id: {original_task.id}) into {len(new_tasks)} sub-tasks: "
            f"{[task.id for task in new_tasks]}"
        )

        return new_tasks

    def get_tools(self) -> List[FunctionTool]:
        return [
            FunctionTool(self.decompose_task),
            FunctionTool(self.replan_tasks),
        ]
