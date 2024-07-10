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

from typing import List, Optional, Union
from uuid import uuid4

from camel.agents.manager_agent import ManagerAgent
from camel.tasks.task import Task
from camel.utils.channel import Channel
from camel.workforce import BaseWorkforce, UnitWorkforce
from camel.workforce.utils import compose, get_workforces_info


class Workforce(BaseWorkforce):
    r"""A workforce that manages multiple workforces and agents. It will
    split the task it receives into subtasks and assign them to the
    workforces/agents under it, and also handles the situation when the task
    fails.

    Args:
        workforce_id (str): ID for the workforce.
        description (str): Description of the workforce.
        workforces (List[Union[UnitWorkforce, Workforce]]): List of workforces
            under this workforce.
        manager_agent_config (dict): Configuration parameters for the
            manager agent.
        channel (Channel): Communication channel for the workforce.
    """

    def __init__(
        self,
        workforce_id: str,
        description: str,
        workforces: List[Union[UnitWorkforce, Workforce]],
        manager_agent_config: dict,
        channel: Channel,
    ) -> None:
        super().__init__(workforce_id, description, channel)
        self.workforces = workforces
        manager_agent = ManagerAgent()
        self.manager = UnitWorkforce(
            str(uuid4()), "manager", manager_agent, channel
        )
        self.workforce_info = get_workforces_info(workforces)

    def assign_other_workforce(
        self, task: Task, failed_log: Optional[str], workforce_info: str
    ) -> Union[int, None]:
        r"""Assigns a task to an internal workforce if capable, otherwise
        returns None.

        Parameters:
            task (Task): The task to be assigned.
            failed_log (Optional[str]): Optional log of a previous failed
                attempt.
            workforce_info (str): Information about the internal workforce.

        Returns:
            Union[int, None]: ID of the assigned workforce, or None if not
                assignable.
        """
        pass

    async def process_current_task(self, current_task: Task):
        """Processes the current task, managing task assignment and result
            aggregation.

        Args:
            current_task (Task): The task to be processed.

        Returns:
            The result of the task processing, or None if the task cannot be
                processed.
        """
        chosen_workforce = await self.send_message_receive_result(
            self.manager_agent.id,
            "assign_other_workforce",
            (current_task, None, self.workforce_info),
        )
        if not chosen_workforce:
            return None
        else:
            task_result = await chosen_workforce.process_task(current_task)
            if not task_result:
                current_subtasks = current_task.decompose()
                subtask_result = []
                for subtask in current_subtasks:
                    subtask_result.append
                    (await self.process_current_task(subtask))
                return compose(subtask_result)
            else:
                return task_result

    async def process_task(self, task: Task) -> Union[str, None]:
        r"""Processes a given task, serving as an entry point for task
            processing.

        Args:
            task (Task): The task to be processed.

        Returns:
            Union[str, None]: The result of the task processing, or None if
                the task cannot be processed.
        """
        return await self.process_current_task(task)

    async def start(self):
        for workforce in self.workforces:
            workforce.listening()
