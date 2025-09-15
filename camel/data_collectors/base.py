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
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from uuid import UUID

from typing_extensions import Self

from camel.agents import ChatAgent


class CollectorData:
    def __init__(
        self,
        id: UUID,
        name: str,
        role: Literal["user", "assistant", "system", "tool"],
        message: Optional[str] = None,
        function_call: Optional[Dict[str, Any]] = None,
    ) -> None:
        r"""Create a data item store information about a message.
        Used by the data collector.

        Args:

            id (UUID): The id of the message.
            name (str): The name of the agent.
            role (Literal["user", "assistant", "system", "function"]):
                The role of the message.
            message (Optional[str], optional): The message.
                (default: :obj:`None`)
            function_call (Optional[Dict[str, Any]], optional):
                The function call. (default: :obj:`None`)

        Raises:

            ValueError: If the role is not supported.
            ValueError: If the role is system and function call is provided.
            ValueError: If neither message nor function call is provided.

        """
        if role not in ["user", "assistant", "system", "tool"]:
            raise ValueError(f"Role {role} not supported")
        if role == "system" and function_call:
            raise ValueError("System role cannot have function call")
        if not message and not function_call:
            raise ValueError(
                "Either message or function call must be provided"
            )
        self.id = id
        self.name = name
        self.role = role
        self.message = message
        self.function_call = function_call

    @staticmethod
    def from_context(name, context: Dict[str, Any]) -> "CollectorData":
        r"""Create a data collector from a context.

        Args:
            name (str): The name of the agent.
            context (Dict[str, Any]): The context.

        Returns:
            CollectorData: The data collector.
        """
        return CollectorData(
            id=uuid.uuid4(),
            name=name,
            role=context["role"],
            message=context["content"],
            function_call=context.get("tool_calls", None),
        )


class BaseDataCollector(ABC):
    r"""Base class for data collectors."""

    def __init__(self) -> None:
        r"""Create a data collector."""
        self.history: List[CollectorData] = []
        self._recording = False
        self.agents: List[Tuple[str, ChatAgent]] = []
        self.data: List[Dict[str, Any]] = []

    def step(
        self,
        role: Literal["user", "assistant", "system", "tool"],
        name: Optional[str] = None,
        message: Optional[str] = None,
        function_call: Optional[Dict[str, Any]] = None,
    ) -> Self:
        r"""Record a message.

        Args:
            role (Literal["user", "assistant", "system", "tool"]):
                The role of the message.
            name (Optional[str], optional): The name of the agent.
                (default: :obj:`None`)
            message (Optional[str], optional): The message to record.
                (default: :obj:`None`)
            function_call (Optional[Dict[str, Any]], optional):
                The function call to record. (default: :obj:`None`)

        Returns:
            Self: The data collector.

        """

        name = name or role

        self.history.append(
            CollectorData(
                id=uuid.uuid4(),
                name=name,
                role=role,
                message=message,
                function_call=function_call,
            )
        )
        return self

    def record(
        self,
        agent: Union[List[ChatAgent], ChatAgent],
    ) -> Self:
        r"""Record agents.

        Args:
            agent (Union[List[ChatAgent], ChatAgent]):
                The agent(s) to inject.
        """
        if not isinstance(agent, list):
            agent = [agent]
        for a in agent:
            name = a.role_name
            if not name:
                name = f"{a.__class__.__name__}_{len(self.agents)}"
            if name in [n for n, _ in self.agents]:
                raise ValueError(f"Name {name} already exists")

            self.agents.append((name, a))
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

    def get_agent_history(self, name: str) -> List[CollectorData]:
        r"""Get the message history of an agent.

        Args:
            name (str): The name of the agent.

        Returns:
            List[CollectorData]: The message history of the agent
        """
        if not self.history:
            for _name, agent in self.agents:
                if _name == name:
                    return [
                        CollectorData.from_context(name, dict(i))
                        for i in agent.memory.get_context()[0]
                    ]
        return [msg for msg in self.history if msg.name == name]
