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
from __future__ import annotations

import datetime
import json
from typing import Any, List

from colorama import Fore

from camel.agents import ChatAgent
from camel.societies.workforce.prompts import PROCESS_TASK_PROMPT
from camel.societies.workforce.utils import TaskResult
from camel.societies.workforce.worker import Worker
from camel.tasks.task import Task, TaskState, validate_task_content


class SingleAgentWorker(Worker):
    r"""A worker node that consists of a single agent.

    Args:
        description (str): Description of the node.
        worker (ChatAgent): Worker of the node. A single agent.
        max_concurrent_tasks (int): Maximum number of tasks this worker can
            process concurrently. (default: :obj:`10`)
    """

    def __init__(
        self,
        description: str,
        worker: ChatAgent,
        max_concurrent_tasks: int = 10,
    ) -> None:
        node_id = worker.agent_id
        super().__init__(
            description,
            node_id=node_id,
            max_concurrent_tasks=max_concurrent_tasks,
        )
        self.worker = worker

    def reset(self) -> Any:
        r"""Resets the worker to its initial state."""
        super().reset()
        self.worker.reset()

    async def _process_task(
        self, task: Task, dependencies: List[Task]
    ) -> TaskState:
        r"""Processes a task with its dependencies using a cloned agent.

        This method asynchronously processes a given task, considering its
        dependencies, by sending a generated prompt to a cloned worker agent.
        Using a cloned agent ensures that concurrent tasks don't interfere
        with each other's state.

        Args:
            task (Task): The task to process, which includes necessary details
                like content and type.
            dependencies (List[Task]): Tasks that the given task depends on.

        Returns:
            TaskState: `TaskState.DONE` if processed successfully, otherwise
                `TaskState.FAILED`.
        """
        # Clone the agent for this specific task to avoid state conflicts
        # when processing multiple tasks concurrently
        worker_agent = self.worker.clone(with_memory=False)

        dependency_tasks_info = self._get_dep_tasks_info(dependencies)
        prompt = PROCESS_TASK_PROMPT.format(
            content=task.content,
            dependency_tasks_info=dependency_tasks_info,
            additional_info=task.additional_info,
        )
        try:
            response = await worker_agent.astep(
                prompt, response_format=TaskResult
            )
        except Exception as e:
            print(
                f"{Fore.RED}Error occurred while processing task {task.id}:"
                f"\n{e}{Fore.RESET}"
            )
            return TaskState.FAILED

        # Get actual token usage from the cloned agent that processed this task
        try:
            _, total_token_count = worker_agent.memory.get_context()
        except Exception:
            # Fallback if memory context unavailable
            total_token_count = 0

        # Populate additional_info with worker attempt details
        if task.additional_info is None:
            task.additional_info = {}

        # Create worker attempt details with descriptive keys
        worker_attempt_details = {
            "agent_id": getattr(
                worker_agent, "agent_id", worker_agent.role_name
            ),
            "original_worker_id": getattr(
                self.worker, "agent_id", self.worker.role_name
            ),
            "timestamp": str(datetime.datetime.now()),
            "description": f"Attempt by "
            f"{getattr(worker_agent, 'agent_id', worker_agent.role_name)} "
            f"(cloned from "
            f"{getattr(self.worker, 'agent_id', self.worker.role_name)}) "
            f"to process task {task.content}",
            "response_content": response.msg.content,
            "tool_calls": response.info["tool_calls"],
            "total_token_count": total_token_count,
        }

        # Store the worker attempt in additional_info
        if "worker_attempts" not in task.additional_info:
            task.additional_info["worker_attempts"] = []
        task.additional_info["worker_attempts"].append(worker_attempt_details)

        # Store the actual token usage for this specific task
        task.additional_info["token_usage"] = {
            "total_tokens": total_token_count
        }

        print(f"======\n{Fore.GREEN}Reply from {self}:{Fore.RESET}")

        result_dict = json.loads(response.msg.content)
        task_result = TaskResult(**result_dict)

        color = Fore.RED if task_result.failed else Fore.GREEN
        print(
            f"\n{color}{task_result.content}{Fore.RESET}\n======",
        )

        if task_result.failed:
            return TaskState.FAILED

        if not validate_task_content(task_result.content, task.id):
            print(
                f"{Fore.RED}Task {task.id}: Content validation failed - "
                f"task marked as failed{Fore.RESET}"
            )
            return TaskState.FAILED

        task.result = task_result.content
        return TaskState.DONE
