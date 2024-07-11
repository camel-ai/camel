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

from typing import Union

from camel.agents.base import BaseAgent
from camel.societies import RolePlaying
from camel.tasks.task import Task
from camel.utils.channel import Channel
from camel.workforce.base import BaseWorkforce


class UnitWorkforce(BaseWorkforce):
    r"""A unit workforce that consists of a single worker. It is the basic unit
    of task processing in the workforce system.

    Args:
        workforce_id (str): ID for the workforce.
        description (str): Description of the workforce.
        worker (Union[BaseAgent, RolePlaying]): Worker of the workforce.
            Could be a single agent or a role playing system.
        channel (Channel): Communication channel for the workforce.

    """

    def __init__(
            self,
            workforce_id: str,
            description: str,
            worker: Union[BaseAgent, RolePlaying],
            channel: Channel,
    ) -> None:
        super().__init__(workforce_id, description, channel)
        self.worker = worker

    async def process_task(self, task: Task) -> Union[str, None]:
        """Processes a given task, serving as an entry point for task
        processing."""
        task_result = self.worker.step(task)
        return task_result

    async def listening(self):
        """Continuously listen to the channel, process the task that are
        assigned to this workforce, and update the result and status of the
        task.

        This method should be run in an event loop, as it will run
            indefinitely.
        """
        # TODO: Check the first task in the channel that are assigned to
        #  this workforce and status is not 'done'

        # TODO: Process the task, no need to remove it from the channel

        # TODO: Update the result and status of the task in the channel
        raise NotImplementedError()
