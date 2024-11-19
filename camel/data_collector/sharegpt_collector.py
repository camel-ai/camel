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
import json
from typing import Any, Dict, List, Optional, Self, Union

from camel.agents.chat_agent import ChatAgent
from camel.data_collector.base import BaseDataCollector
from camel.messages.base import BaseMessage
from camel.messages.func_message import FunctionCallingMessage
from camel.toolkits.function_tool import FunctionTool
from camel.types.enums import OpenAIBackendRole


class ShareGPTDataCollector(BaseDataCollector):
    def __init__(self):
        super().__init__()
        self.system_message: Optional[BaseMessage] = None
        self.agent_name: Optional[str] = None
        self.tools: List[FunctionTool] = []

    def inject(
        self,
        agent: Union[List[ChatAgent], ChatAgent],
        name: Optional[Union[str, List[Optional[str]]]] = None,
    ) -> Self:
        r"""Inject an agent into the data collector."""
        if len(self.agents) > 1:
            raise ValueError("ShareGPTDataCollector only supports one agent")
        if isinstance(agent, list):
            if len(agent) != 1:
                raise ValueError(
                    "ShareGPTDataCollector only supports one agent"
                )
            agent = agent[0]
        if isinstance(name, list):
            name = name[0]

        self.agent_name = name or agent.role_name
        self.system_message = agent._system_message
        self.tools = list(agent.tool_dict.values())

        self._inject(agent, name)
        return self

    def convert(self) -> Dict[str, Any]:
        r"""Convert the collected data into a dictionary."""
        if self.agent_name is None:
            raise ValueError("No agent injected")
        if history := self.history.get(self.agent_name):
            data = dict(
                system=self.system_message.content
                if self.system_message
                else "",
                tools=json.dumps(
                    [
                        t.get_openai_tool_schema()["function"]
                        for t in self.tools
                    ]
                ),
                conversations=[],
            )
            conversations: List[Any] = []
            for _, role, message in history:
                if role == OpenAIBackendRole.USER:
                    conversations.append(
                        {"from": "human", "value": message.content}
                    )
                elif role == OpenAIBackendRole.ASSISTANT:
                    if isinstance(message, FunctionCallingMessage):
                        tmp = dict(
                            name=message.func_name,
                            arguments=message.args,
                        )
                        conversations.append(
                            {"from": "function_call", "value": json.dumps(tmp)}
                        )
                    else:
                        conversations.append(
                            {"from": "gpt", "value": message.content}
                        )
                elif role == OpenAIBackendRole.FUNCTION:
                    conversations.append(
                        {
                            "from": "observation",
                            "value": json.dumps(message.result),  # type: ignore[attr-defined]
                        }
                    )
            data["conversations"] = conversations

            self.data.append(data)
            return data
        raise ValueError("No data collected")
