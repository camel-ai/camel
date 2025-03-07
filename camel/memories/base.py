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

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from camel.memories.records import ContextRecord, MemoryRecord
from camel.messages import OpenAIMessage
from camel.utils import BaseTokenCounter


class MemoryBlock(ABC):
    r"""An abstract class serves as the fundamental component within the agent
    memory system. This class is equipped with "write" and "clear" functions.
    However, it intentionally does not define a retrieval interface, as the
    structure of the data to be retrieved may vary in different types of
    memory blocks.
    """

    @abstractmethod
    def write_records(self, records: List[MemoryRecord]) -> None:
        r"""Writes records to the memory, appending them to existing ones.

        Args:
            records (List[MemoryRecord]): Records to be added to the memory.
        """
        pass

    def write_record(self, record: MemoryRecord) -> None:
        r"""Writes a record to the memory, appending it to existing ones.

        Args:
            record (MemoryRecord): Record to be added to the memory.
        """
        self.write_records([record])

    @abstractmethod
    def clear(self) -> None:
        r"""Clears all messages from the memory."""
        pass


class BaseContextCreator(ABC):
    r"""An abstract base class defining the interface for context creation
    strategies.

    This class provides a foundational structure for different strategies to
    generate conversational context from a list of context records. The
    primary goal is to create a context that is aligned with a specified token
    count limit, allowing subclasses to define their specific approach.

    Subclasses should implement the :obj:`token_counter`,:obj: `token_limit`,
    and :obj:`create_context` methods to provide specific context creation
    logic.

    Attributes:
        token_counter (BaseTokenCounter): A token counter instance responsible
            for counting tokens in a message.
        token_limit (int): The maximum number of tokens allowed in the
            generated context.
    """

    @property
    @abstractmethod
    def token_counter(self) -> BaseTokenCounter:
        pass

    @property
    @abstractmethod
    def token_limit(self) -> int:
        pass

    @abstractmethod
    def create_context(
        self,
        records: List[ContextRecord],
    ) -> Tuple[List[OpenAIMessage], int]:
        r"""An abstract method to create conversational context from the chat
        history.

        Constructs the context from provided records. The specifics of how this
        is done and how the token count is managed should be provided by
        subclasses implementing this method. The output messages order
        should keep same as the input order.

        Args:
            records (List[ContextRecord]): A list of context records from
                which to generate the context.

        Returns:
            Tuple[List[OpenAIMessage], int]: A tuple containing the constructed
                context in OpenAIMessage format and the total token count.
        """
        pass


class AgentMemory(MemoryBlock, ABC):
    r"""Represents a specialized form of `MemoryBlock`, uniquely designed for
    direct integration with an agent. Two key abstract functions, "retrieve"
    and "get_context_creator", are used for generating model context based on
    the memory records stored within the AgentMemory.
    """

    @property
    @abstractmethod
    def agent_id(self) -> Optional[str]:
        pass

    @agent_id.setter
    @abstractmethod
    def agent_id(self, val: Optional[str]) -> None:
        pass

    @abstractmethod
    def retrieve(self) -> List[ContextRecord]:
        r"""Get a record list from the memory for creating model context.

        Returns:
            List[ContextRecord]: A record list for creating model context.
        """
        pass

    @abstractmethod
    def get_context_creator(self) -> BaseContextCreator:
        r"""Gets context creator.

        Returns:
            BaseContextCreator: A model context creator.
        """
        pass

    def get_context(self) -> Tuple[List[OpenAIMessage], int]:
        r"""Gets chat context with a proper size for the agent from the memory.

        Returns:
            (List[OpenAIMessage], int): A tuple containing the constructed
                context in OpenAIMessage format and the total token count.
        """
        return self.get_context_creator().create_context(self.retrieve())

    def __repr__(self) -> str:
        r"""Returns a string representation of the AgentMemory.

        Returns:
            str: A string in the format 'ClassName(agent_id=<id>)'
                if agent_id exists, otherwise just 'ClassName()'.
        """
        agent_id = getattr(self, '_agent_id', None)
        if agent_id:
            return f"{self.__class__.__name__}(agent_id='{agent_id}')"
        return f"{self.__class__.__name__}()"
