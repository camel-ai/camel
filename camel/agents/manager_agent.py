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
from typing import Optional

from camel.agents.chat_agent import ChatAgent
from camel.models import BaseModelBackend
from camel.types import TaskType


class ManagerAgent(ChatAgent):
    r"""An agent that has ability to manager tasks in workforce."""

    def __init__(
        self,
        model: Optional[BaseModelBackend] = None,
        task_type: TaskType = TaskType.AI_SOCIETY,
        assign_task_prompt: Optional[str] = None,
    ):
        pass

    def other_func(self):
        r'''manager agent may have function to deal with error or restart some
        workforce in the future.
        '''
        pass
