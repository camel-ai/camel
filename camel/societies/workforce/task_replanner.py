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
from typing import Dict, Optional

from camel.agents import ChatAgent
from camel.societies.workforce.replanner_prompts import (
    ANALYZE_FAILURE_PROMPT,
    GET_MAX_DEPTH_PROMPT,
    REPLAN_TASK_PROMPT,
)
from camel.tasks.task import Task


class TaskReplanner:
    """A module for replanning failed tasks in the Workforce system.

    This class provides functionality to analyze task failures, replan tasks,
    and determine appropriate task depth limits based on task characteristics.
    """

    def __init__(self, agent_kwargs: Optional[Dict] = None):
        """Initialize the TaskReplanner.

        Args:
            agent_kwargs (Optional[Dict], optional): Keyword arguments for
                creating the replanner agent. Defaults to None.
        """
        if agent_kwargs is None:
            agent_kwargs = {}

        # Create a system message for the replanner agent
        replanner_sys_msg = (
            "You are a Task Replanner, an expert at analyzing failed tasks "
            "and restructuring them for better success. Your job is to "
            "identify why tasks fail and suggest better approaches."
        )

        # Create the replanner agent
        self.replanner_agent = ChatAgent(replanner_sys_msg, **agent_kwargs)

    async def analyze_failure_reason(
        self, task: Task, error_log: str = ""
    ) -> str:
        """Analyze why a task has failed.

        Args:
            task (Task): The failed task.
            error_log (str, optional): Error log from the task execution.
                Defaults to "".

        Returns:
            str: Analysis of the failure reason.
        """
        # Create a history string from task execution history if available
        history = ""
        if hasattr(task, "execution_history"):
            history = task.execution_history

        # Format the prompt with task information
        prompt = ANALYZE_FAILURE_PROMPT.format(
            content=task.content,
            error_log=error_log,
            history=history,
        )

        # Get the analysis from the replanner agent
        response = self.replanner_agent.step(prompt)
        return response.msg.content

    async def replan_task(
        self, task: Task, failure_reason: str, child_nodes_info: str
    ) -> Task:
        """Replan a failed task based on the failure analysis.

        Args:
            task (Task): The failed task.
            failure_reason (str): Analysis of why the task failed.
            child_nodes_info (str): Information about available worker nodes.

        Returns:
            Task: A new task with updated content.
        """
        # Format the prompt with task and failure information
        prompt = REPLAN_TASK_PROMPT.format(
            original_content=task.content,
            failure_reason=failure_reason,
            child_nodes_info=child_nodes_info,
        )

        # Get the replanned task from the replanner agent
        response = self.replanner_agent.step(prompt)
        new_content = response.msg.content.strip()

        # Create a new task with the updated content
        new_task = Task(
            content=new_content,
            id=task.id,
            parent=task.parent,
            type=task.type,
            additional_info=task.additional_info,
        )

        # Copy over the failure count
        new_task.failure_count = task.failure_count

        # Mark the task as restructured
        new_task.is_restructured = True

        return new_task

    async def get_max_depth(self, task: Task) -> int:
        """Determine the appropriate maximum depth for a task.

        Args:
            task (Task): The task to analyze.

        Returns:
            int: The recommended maximum depth for the task.
        """
        # Format the prompt with task information
        prompt = GET_MAX_DEPTH_PROMPT.format(
            content=task.content,
            additional_info=task.additional_info or "",
        )

        # Get the recommended depth from the replanner agent
        response = self.replanner_agent.step(prompt)

        try:
            # Try to parse the response as an integer
            max_depth = int(response.msg.content.strip())
            # Ensure the depth is within reasonable bounds
            return max(3, min(max_depth, 6))
        except ValueError:
            # Default to 3 if parsing fails
            return 3
