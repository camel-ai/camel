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
from typing import Any, Dict, List, Optional, Self, Union

from camel.agents.chat_agent import ChatAgent
from camel.data_collector.base import BaseDataCollector
from camel.messages.base import BaseMessage


class AlpacaDataCollector(BaseDataCollector):
    def __init__(self) -> None:
        super().__init__()
        self.system_message: Optional[BaseMessage] = None
        self.agent_name: Optional[str] = None

    def inject(
        self,
        agent: Union[List[ChatAgent], ChatAgent],
    ) -> Self:
        r"""Inject an agent into the data collector.

        Args:
            agent (Union[List[ChatAgent], ChatAgent]):
                The agent to inject.
            name (Optional[Union[str, List[Optional[str]]]], optional):
                The name of the agent. Defaults to None.
        """
        if not self.agent_name:
            _agent = agent if isinstance(agent, ChatAgent) else agent[0]
            self.agent_name = _agent.role_name
            self.system_message = _agent._system_message
        super().inject(agent)
        return self

    def convert(self) -> Dict[str, str]:
        r"""Convert the collected data into a dictionary."""
        if self.agent_name is None:
            raise ValueError("No agent injected")
        if history := self.get_agent_history(self.agent_name):
            if len(history) != 2:
                raise ValueError(
                    "AlpacaDataCollector only supports one message,",
                    f" but got {len(history)}",
                )
            data = dict(
                instructions=self.system_message.content
                if self.system_message
                else "",
                input=history[0].message.content,
                output=history[1].message.content,
            )
            self.data.append(data)
            return data
        raise ValueError("No data collected")

    def llm_convert(self, converter: Any, prompt: Optional[str] = None) -> Any:
        raise NotImplementedError(
            "LLM conversion is not supported, waiting for another PR merged."
        )
