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
from camel.responses import ChatAgentResponse
from camel.tasks.task import Task, TaskState
from camel.workforce.leaf_workforce import LeafWorkforce
from camel.workforce.task_channel import TaskChannel
from camel.workforce.utils import parse_task_result_resp
from camel.workforce.workforce_prompt import PROCESS_TASK_PROMPT


class SingleAgentWorforce(LeafWorkforce):
    r"""A unit workforce that consists of a single worker. It is the basic unit
    of task processing in the workforce system.

    Args:
        workforce_id (str): ID for the workforce.
        description (str): Description of the workforce.
        worker (Union[BaseAgent, RolePlaying]): Worker of the workforce.
            Could be a single agent or a role playing system.
        channel (TaskChannel): Communication channel for the workforce.

    """

    def __init__(
        self,
        workforce_id: str,
        description: str,
        worker: BaseAgent,
        channel: TaskChannel,
    ) -> None:
        super().__init__(workforce_id, description, worker, channel)
        self.worker = worker

    async def _process_task(
        self, task: Task, dependencies: List[Task]
    ) -> TaskState:
        r"""Processes a task based on its dependencies.

        Returns:
            'DONE' if the task is successfully processed,
            'FAILED' if the processing fails.
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
            response: ChatAgentResponse = self.worker.step(req)[0]
            print("response.info['tool_calls']:", response.info['tool_calls'])
            task.result = parse_task_result_resp(response.msg.content)
            print('task.result:', task.result)
            return TaskState.DONE
        except Exception:
            return TaskState.FAILED
        # return parse_assign_task_resp(response.msg.content)
