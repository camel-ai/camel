from abc import ABC, abstractmethod
from collections import defaultdict
import dataclasses
from typing import Any, Dict, List, Optional, Tuple, Type, Union, Self

from anthropic import BaseModel

from camel.agents.base import BaseAgent
from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.responses.agent_responses import ChatAgentResponse
from camel.types.enums import OpenAIBackendRole


class BaseDataCollector(ABC):

    def __init__(self):
        self.history: Dict[str, List[Tuple[int, OpenAIBackendRole, BaseMessage]]] = (
            defaultdict(list)
        )
        self._recording = False
        self.agents: List[Tuple[str, BaseAgent]] = []
        self._id = 0
        self.data: List[Dict[str, Any]] = []

    def step(
        self, message: Union[BaseMessage, ChatAgentResponse], role: OpenAIBackendRole, name: Optional[str] = None
    ) -> Self:
        if name is None:
            if len(self.agents) > 1:
                raise ValueError("DataCollector has multiple agents, please specify the agent name")
            name = self.agents[0][0]
        if isinstance(message, ChatAgentResponse):
            if len(message.msgs) != 1:
                raise ValueError("Only supports one message in response")
            message = message.msgs[0]
        self.history[name].append((self._id, role, message))
        self._id += 1
        return self

    def _inject(self, agent: ChatAgent, name: Optional[str] = None) -> Self:
        name = name or agent.role_name
        if not name:
            name = f"{agent.__class__.__name__}_{len(self.agents)}"
        if name in [n for n, _ in self.agents]:
            raise ValueError(f"Name {name} already exists")

        self.agents.append((name, agent))

        ori_update_memory = agent.update_memory

        def update_memory(message: BaseMessage, role: OpenAIBackendRole) -> None:
            if self._recording:
                self.history[name].append((self._id, role, message))
                self._id += 1
            return ori_update_memory(message, role)

        agent.update_memory = update_memory  # type: ignore[method-assign]


        return self

    def inject(self, agent: Union[List[ChatAgent], ChatAgent], name: Optional[Union[str, List[str]]] = None) -> Self:
        if not isinstance(agent, list):
            agent = [agent]
        if name is None:
            name = [None] * len(agent)
        elif not isinstance(name, list):
            name = [name]
        for a, n in zip(agent, name):
            self._inject(a, n)
        return self

    def start(self) -> Self:
        self._recording = True
        return self

    def stop(self) -> Self:
        self._recording = False
        return self

    @property
    def recording(self) -> bool:
        return self._recording

    def reset(self, reset_agents: bool = True):
        self.history = defaultdict(list)
        self._id = 0
        if reset_agents:
            for _, agent in self.agents:
                agent.reset()

    @abstractmethod
    def convert(self) -> Any:
        pass

    def save(self, path: str):
        raise NotImplementedError
