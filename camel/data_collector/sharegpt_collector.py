# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import json
from typing import Any, ClassVar, Dict, List, Literal, Optional, Union

from pydantic import BaseModel
from typing_extensions import Self

from camel.agents.chat_agent import ChatAgent
from camel.data_collector.base import BaseDataCollector
from camel.messages.base import BaseMessage
from camel.messages.func_message import FunctionCallingMessage
from camel.schemas.openai_converter import OpenAISchemaConverter
from camel.toolkits.function_tool import FunctionTool
from camel.types.enums import OpenAIBackendRole

# ruff: noqa: E501
DEFAULT_CONVERTER_PROMPTS = """
    Extract key entities and attributes from the conversations
    and convert them into a structured JSON format.
    For example:
    System: You are a helpful assistant
    Tools: [{"name": "get_release_date", "arguments": ["Portal"]}]
    User: When is the release date of the video game Portal?
    Assistant: The release date of the video game Portal is October 9, 2007.
    Your output should be:
    {
        "system": "You are a helpful assistant",
        "tools": "[{"name": "get_release_date", "arguments": ["Portal"]}]",
        "conversations": [
            {"from": "human", "value": "When is the release date of the video game Portal?"},
            {"from": "gpt", "value": "The release date of the video game Portal is October 9, 2007."}
        ]
    }
"""


class ConversationItem(BaseModel):
    from_: Literal["human", "gpt", "function_call", "observation"]
    value: str

    class Config:
        fields: ClassVar[Dict[str, str]] = {"from_": "from"}
        extra = "forbid"


class ShareGPTData(BaseModel):
    system: str
    tools: str
    conversations: List[ConversationItem]

    class Config:
        extra = "forbid"


class ShareGPTDataCollector(BaseDataCollector):
    def __init__(self) -> None:
        super().__init__()
        self.system_message: Optional[BaseMessage] = None
        self.agent_name: Optional[str] = None
        self.tools: List[FunctionTool] = []

    def inject(
        self,
        agent: Union[List[ChatAgent], ChatAgent],
    ) -> Self:
        r"""Inject an agent into the data collector."""
        if not self.agent_name:
            _agent = agent if isinstance(agent, ChatAgent) else agent[0]
            self.agent_name = _agent.role_name
            self.system_message = _agent._system_message
            self.tools += list(_agent.tool_dict.values())

        super().inject(agent)
        return self

    def convert(self) -> Dict[str, Any]:
        r"""Convert the collected data into a dictionary."""
        if self.agent_name is None:
            raise ValueError("No agent injected")
        if history := self.get_agent_history(self.agent_name):
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
            for _data in history:
                role, message = _data.role, _data.message
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

    def llm_convert(
        self,
        converter: Optional[OpenAISchemaConverter] = None,
        prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        prompt = prompt or DEFAULT_CONVERTER_PROMPTS
        converter = converter or OpenAISchemaConverter()
        system = self.system_message.content if self.system_message else ""
        context = [f"System: {system}\n"]
        context.append(
            "Tools: "
            + json.dumps(
                [t.get_openai_tool_schema()["function"] for t in self.tools]
            )
        )
        for _data in self.history:
            role, message = _data.role, _data.message
            prefix = (
                f"{role.value}: "
                if role != OpenAIBackendRole.USER
                else "User: " + f"{_data.name}: "
            )
            if isinstance(message, FunctionCallingMessage):
                tmp = dict(
                    name=message.func_name,
                    arguments=message.args,
                )
                context.append(prefix + json.dumps(tmp))
            elif role == OpenAIBackendRole.FUNCTION:
                context.append(prefix + json.dumps(message.result))  # type: ignore[attr-defined]
            else:
                context.append(prefix + message.content)
        return converter.convert(
            "\n".join(context), ShareGPTData, prompt
        ).model_dump()
