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

import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple, Union
from typing_extensions import Self
from uuid import UUID

from camel.agents import ChatAgent
from camel.messages.base import BaseMessage
from camel.types.enums import OpenAIBackendRole


class CollectorData:
    def __init__(
        self,
        id: UUID,
        name: str,
        role: OpenAIBackendRole,
        message: BaseMessage,
    ) -> None:
        self.id = id
        self.name = name
        self.role = role
        self.message = message


class BaseDataCollector(ABC):
    r"""Base class for data collectors."""

    def __init__(self) -> None:
        self.history: List[CollectorData] = []
        self._recording = False
        self.agents: List[Tuple[str, ChatAgent]] = []
        self.data: List[Dict[str, Any]] = []

    def step(
        self,
        message: BaseMessage,
        role: OpenAIBackendRole,
        role_name: Optional[str] = None,
    ) -> Self:
        r"""Record a message.

        Args:
            message (Union[BaseMessage, ChatAgentResponse]):
                The message to record.
            role (OpenAIBackendRole): The role of the message.
            role_name (Optional[str], optional):
                The name of the role. Defaults to None.
                Used when message if from user.
        """

        name = role_name or message.role_name

        self.history.append(
            CollectorData(
                id=uuid.uuid1(), name=name, role=role, message=message
            )
        )
        return self

    def _inject(self, agent: ChatAgent) -> Self:
        r"""Inject an agent.

        Args:
            agent (ChatAgent): The agent to inject.
        """
        name = agent.role_name
        if not name:
            name = f"{agent.__class__.__name__}_{len(self.agents)}"
        if name in [n for n, _ in self.agents]:
            raise ValueError(f"Name {name} already exists")

        self.agents.append((name, agent))

        ori_update_memory = agent.update_memory

        def update_memory(
            message: BaseMessage, role: OpenAIBackendRole
        ) -> None:
            if self._recording:
                self.history.append(
                    CollectorData(
                        id=uuid.uuid1(), name=name, role=role, message=message
                    )
                )
            return ori_update_memory(message, role)

        agent.update_memory = update_memory  # type: ignore[method-assign]

        return self

    def inject(
        self,
        agent: Union[List[ChatAgent], ChatAgent],
    ) -> Self:
        r"""Inject agents.

        Args:
            agent (Union[List[ChatAgent], ChatAgent]):
                The agent(s) to inject.
        """
        if not isinstance(agent, list):
            agent = [agent]
        for a in agent:
            self._inject(a)
        return self

    def start(self) -> Self:
        r"""Start recording."""
        self._recording = True
        return self

    def stop(self) -> Self:
        r"""Stop recording."""
        self._recording = False
        return self

    @property
    def recording(self) -> bool:
        r"""Whether the collector is recording."""
        return self._recording

    def reset(self, reset_agents: bool = True):
        r"""Reset the collector.

        Args:
            reset_agents (bool, optional):
                Whether to reset the agents. Defaults to True.
        """
        self.history = []
        if reset_agents:
            for _, agent in self.agents:
                agent.reset()

    @abstractmethod
    def convert(self) -> Any:
        r"""Convert the collected data."""
        pass

    @abstractmethod
    def llm_convert(self, converter: Any, prompt: Optional[str] = None) -> Any:
        r"""Convert the collected data."""
        pass

    def save(self, path: str):
        r"""Save the collected data.

        Args:
            path (str): The path to save the data.
        """
        raise NotImplementedError

    def get_agent_history(self, name: str) -> List[CollectorData]:
        return [msg for msg in self.history if msg.name == name]
