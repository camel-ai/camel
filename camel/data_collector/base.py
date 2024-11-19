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
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Dict, List, Self, Tuple, Union

from camel.agents import ChatAgent
from camel.messages.base import BaseMessage
from camel.responses.agent_responses import ChatAgentResponse
from camel.types.enums import OpenAIBackendRole


class BaseDataCollector(ABC):
    r"""Base class for data collectors."""

    def __init__(self):
        self.history: Dict[
            str, List[Tuple[int, OpenAIBackendRole, BaseMessage]]
        ] = defaultdict(list)
        self._recording = False
        self.agents: List[ChatAgent] = []
        self._id = 0
        self.data: List[Dict[str, Any]] = []

    def step(
        self,
        message: Union[BaseMessage, ChatAgentResponse],
    ) -> Self:
        r"""Record a message.

        Args:
            message (Union[BaseMessage, ChatAgentResponse]):
                The message to record.
        """

        name = BaseMessage.role_name
        role = BaseMessage.role_type.value
        if isinstance(message, ChatAgentResponse):
            for msg in message.msgs:
                self.history[name].append((self._id, role, msg))
                self._id += 1
        else:
            self.history[name].append((self._id, role, message))
            self._id += 1
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
                self.history[name].append((self._id, role, message))
                self._id += 1
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
        for a, n in zip(agent, agent.role_name):
            self._inject(a, n)
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
        self.history = defaultdict(list)
        self._id = 0
        if reset_agents:
            for _, agent in self.agents:
                agent.reset()

    @abstractmethod
    def convert(self) -> Any:
        r"""Convert the collected data."""
        pass

    def save(self, path: str):
        r"""Save the collected data.

        Args:
            path (str): The path to save the data.
        """
        raise NotImplementedError
