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
from typing import List, Optional

from camel.logger import get_logger
from camel.tasks import Task
from camel.toolkits import BaseToolkit, FunctionTool

logger = get_logger(__name__)


class TaskPlanningToolkit(BaseToolkit):
    r"""
    A toolkit for task decomposition and rePlanning.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
    ):
        r"""Initialize the TaskPlanningToolkit.

        Args:
            timeout (Optional[float]): The timeout for the toolkit.
                (default: :obj: `None`)
        """
        super().__init__(timeout=timeout)

    def decompose_task(
        self,
        tasks: List[Task],
    ) -> List[Task]:
        r"""Use the tool to decompose a task into several subTasks.
        It will not obtain new information or change the database, but just
        append the subTasks to the log.

        Args:
            tasks (List[Task]): the subTasks which compose the task.

        Returns:
            str: The recorded tasks.
        """
        logger.debug(f"subTasks: {tasks}")

        return tasks

    def replan_tasks(
        self,
        tasks: List[Task],
        context: str = "",
    ) -> List[Task]:
        r"""
        Use the tool to reDecompose the task into subTasks when the subTasks
        decompose before are not good enough to solve the task.

        Args:
            tasks (List[Task]): Original list of tasks.
            context (str): Contextual information affecting the replanning.

        Returns:
            List[Task]: Reordered or modified tasks.
        """
        logger.debug(f"rePlanSubTasks: {tasks}")

        return tasks

    def get_tools(self) -> List[FunctionTool]:
        return [
            FunctionTool(self.decompose_task),
            FunctionTool(self.replan_tasks),
        ]
