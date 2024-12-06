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

from typing import Any, Dict, List, Optional, Union

from typing_extensions import Self

from camel.agents.chat_agent import ChatAgent
from camel.data_collector.base import BaseDataCollector
from camel.messages.base import BaseMessage
from camel.messages.conversion import AlpacaItem
from camel.schemas import OpenAISchemaConverter

DEFAULT_CONVERTER_PROMPTS = """
    Extract key entities and attributes from the conversations
    and convert them into a structured JSON format.
    For example:
    Instructions: You are a helpful assistant
    User: When is the release date of the video game Portal?
    Assistant: The release date of the video game Portal is October 9.
    Your output should be:
    {
        "instructions": "You are a helpful assistant",
        "input": "When is the release date of the video game Portal?",
        "output": "The release date of the video game Portal is October 9."
    }
"""


class AlpacaDataCollector(BaseDataCollector):
    def __init__(self) -> None:
        super().__init__()
        self.system_message: Optional[BaseMessage] = None
        self.agent_name: Optional[str] = None

    def record(
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
        super().record(agent)
        return self

    def convert(self) -> Dict[str, Any]:
        r"""Convert the collected data into a dictionary."""
        if self.agent_name is None:
            raise ValueError("No agent injected")
        if history := self.get_agent_history(self.agent_name):
            for message in history:
                print(message.role, message.message)

            if len(history) != 2:
                if len(history) == 3 and history[0].role == "system":
                    history = history[1:]
                else:
                    raise ValueError(
                        "AlpacaDataCollector only supports one message,"
                        + f" but got {len(history)}",
                    )
            data = dict(
                instructions=(
                    self.system_message.content if self.system_message else ""
                )
                + str(history[0].message),
                input="",
                output=history[1].message,
            )
            self.data.append(data)
            return data
        raise ValueError("No data collected")

    def llm_convert(
        self,
        converter: Optional[OpenAISchemaConverter] = None,
        prompt: Optional[str] = None,
    ) -> Dict[str, str]:
        prompt = prompt or DEFAULT_CONVERTER_PROMPTS
        converter = converter or OpenAISchemaConverter()
        system = self.system_message.content if self.system_message else ""
        context = [f"Instructions: {system}\n"]
        for message in self.get_agent_history(str(self.agent_name)):
            if message.role == "user":
                context.append(f"User: {message.message}\n")
            else:
                context.append(f"{message.name}: {message.message}\n")
        return converter.convert(
            "\n".join(context), AlpacaItem, prompt=prompt
        ).model_dump()
