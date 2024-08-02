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
import asyncio

from camel.tasks import Task
from camel.workforce.manager_node import ManagerNode
from camel.workforce.task_channel import TaskChannel


class Workforce:
    r"""A class representing a workforce system.

    Args:
        name (str, optional): The name of the workforce system. Defaults to
            `"CAMEL Workforce"`.
        description (str, optional): A description of the workforce system.
            Defaults to `"A workforce system for managing tasks."`.
    """

    def __init__(
        self,
        root_node: ManagerNode,
        name: str = "CAMEL Workforce",
        description: str = "A workforce system for managing tasks.",
    ) -> None:
        self.name = name
        self.description = description
        self._root_node = root_node

    def process_task(self, task: Task) -> Task:
        self._root_node.set_main_task(task)
        shared_channel = TaskChannel()
        self._root_node.set_channel(shared_channel)

        # start the root workforce
        asyncio.run(self._root_node.start())

        return task
