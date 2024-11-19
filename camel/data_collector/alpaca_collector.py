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
from typing import Dict, List, Optional, Self, Union

from camel.agents.chat_agent import ChatAgent
from camel.data_collector.base import BaseDataCollector
from camel.messages.base import BaseMessage


class AlpacaDataCollector(BaseDataCollector):
    def __init__(self):
        super().__init__()
        self.system_message: Optional[BaseMessage] = None
        self.agent_name: Optional[str] = None

    def inject(
        self,
        agent: Union[List[ChatAgent], ChatAgent],
        name: Optional[Union[str, List[Optional[str]]]] = None,
    ) -> Self:
        if len(self.agents) > 1:
            raise ValueError("AlpacaDataCollector only supports one agent")
        if isinstance(agent, list):
            if len(agent) != 1:
                raise ValueError("AlpacaDataCollector only supports one agent")
            agent = agent[0]
        if isinstance(name, list):
            name = name[0]
        self.agent_name = name or agent.role_name
        self.system_message = agent._system_message
        self._inject(agent, name)
        return self

    def convert(self) -> Dict[str, str]:
        if self.agent_name is None:
            raise ValueError("No agent injected")
        if history := self.history.get(self.agent_name):
            if len(history) != 2:
                raise ValueError(
                    "AlpacaDataCollector only supports one message"
                )
            data = dict(
                instructions=self.system_message.content
                if self.system_message
                else "",
                input=history[0][2].content,
                output=history[1][2].content,
            )
            self.data.append(data)
            return data
        raise ValueError("No data collected")
