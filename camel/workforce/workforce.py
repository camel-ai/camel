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

from typing import List, Union

from camel.agents.manager_agent import ManagerAgent
from camel.tasks.task import Task
from camel.utils.channel import Channel
from camel.workforce.base import BaseWorkforce
from camel.workforce.unit_workforce import UnitWorkforce
from camel.workforce.utils import compose, get_workforces_info


class Workforce(BaseWorkforce):
    def __init__(
        self,
        workforce_id: str,
        description: str,
        workforces: List[UnitWorkforce],
        manager_agent_config: dict,
        channel: Channel,
    ) -> None:
        """Initializes a new instance of the Workforce class. Only have one
        layer structure first.

        Args:
            workforce_id (str): ID for the workforce.
            description (str): Description of the workforce.
            workforces (List[UnitWorkforce]): List of unit workforces under
                this workforce.
            manager_agent_config (dict): Configuration parameters for the
                manager agent.
            channel (Channel): Communication channel for the workforce.
        """
        super().__init__(workforce_id, description, channel)
        self.workforces = workforces
        manager_agent = ManagerAgent(manager_agent_config)
        self.manager_workforce = UnitWorkforce(manager_agent)

        self.workforce_info = get_workforces_info(workforces)

    async def process_current_task(self, current_task: Task):
        """Processes the current task, managing task assignment and result
            aggregation.

        Args:
            current_task (Task): The task to be processed.

        Returns:
            The result of the task processing, or None if the task cannot be
                processed.
        """
        chosen_workforce = await self.send_messgae_receive_result(
            self.manager_workforce.id,
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
