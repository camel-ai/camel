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

from typing import List

from camel.agents.base import BaseAgent
from camel.messages.base import BaseMessage
from camel.tasks.task import Task, TaskState
from camel.workforce.utils import parse_task_result_resp
from camel.workforce.worker_node import WorkerNode
from camel.workforce.workforce_prompt import PROCESS_TASK_PROMPT


class SingleAgentNode(WorkerNode):
    r"""A worker node that consists of a single agent.

    Args:
        description (str): Description of the node.
        worker (BaseAgent): Worker of the node. A single agent.
    """

    def __init__(
        self,
        description: str,
        worker: BaseAgent,
    ) -> None:
        super().__init__(description)
        self.worker = worker

    async def _process_task(
        self, task: Task, dependencies: List[Task]
    ) -> TaskState:
        r"""Processes a task with its dependencies.

        This method asynchronously processes a given task, considering its
        dependencies, by sending a generated prompt to a worker. It updates
        the task's result based on the agent's response.

        Args:
            task (Task): The task to process, which includes necessary details
                like content and type.
            dependencies (List[Task]): Tasks that the given task depends on.

        Returns:
            TaskState: `TaskState.DONE` if processed successfully, otherwise
                `TaskState.FAILED`.
        """
        try:
            dependency_tasks_info = self._get_dep_tasks_info(dependencies)
            prompt = PROCESS_TASK_PROMPT.format(
                content=task.content,
                type=task.type,
                dependency_task_info=dependency_tasks_info,
            )
            req = BaseMessage.make_user_message(
                role_name="User",
                content=prompt,
            )
            response = self.worker.step(req)
            # print("info['tool_calls']:", response.info['tool_calls'])
            task.result = parse_task_result_resp(response.msg.content)
            print('Task result:', task.result, '\n')
            return TaskState.DONE
        except Exception:
            return TaskState.FAILED
