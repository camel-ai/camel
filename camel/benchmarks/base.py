from abc import ABC, abstractmethod
from io import TextIOWrapper
import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from camel.agents import ChatAgent
from camel.messages.base import BaseMessage
import dataclasses

logger = logging.getLogger(__name__)

class BaseBenchmark(ABC):

    def __init__(self, name: str, data_dir: str, save_to: str, processes: int = 1):
        self.name = name
        self.data_dir = Path(data_dir)
        self.processes = processes
        self.save_to = save_to
        if not self.data_dir.exists():
            logger.info(f"Data directory {data_dir} does not exist. Creating it.")
            self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.data_dir.is_dir():
            raise NotADirectoryError(f"Data directory {data_dir} is not a directory")
        self._data = dict()
        self._results = []
        self._current_history = []

    @abstractmethod
    def download(self) -> "BaseBenchmark":
        pass

    @abstractmethod
    def load(self, force_download: bool = False) -> "BaseBenchmark":
        pass

    @property
    def train(self) -> List[Dict[str, Any]]:
        if not self._data:
            logger.info("Data not loaded. Loading data.")
            self.load()
        return self._data["train"]

    @property
    def valid(self) -> List[Dict[str, Any]]:
        if not self._data:
            logger.info("Data not loaded. Loading data.")
            self.load()
        return self._data["valid"]

    @property
    def test(self) -> List[Dict[str, Any]]:
        if not self._data:
            logger.info("Data not loaded. Loading data.")
            self.load()
        return self._data["test"]

    @abstractmethod
    def run(
        self,
        agent: ChatAgent,
        on: Literal["train", "valid", "test"],
        randomize: bool = False,
        subset: Optional[int] = None,
        *args,
        **kwargs,
    ) -> "BaseBenchmark":
        pass

    @property
    def results(self) -> List[Dict[str, Any]]:
        return self._results

    def _inject(self, agent: ChatAgent) -> ChatAgent:
        ori = agent.record_message
        def record_message(message: BaseMessage) -> None:
            tmp = dataclasses.asdict(message)
            tmp.pop("role_type")
            self._current_history.append(tmp)
            return ori(message)

        agent.record_message = record_message
        return agent
