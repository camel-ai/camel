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
from typing import List, Tuple

from camel.memories import ContextRecord, MemoryRecord
from camel.memories.context_creators import BaseContextCreator
from camel.messages import OpenAIMessage


class MemoryBlock(ABC):
    r"""An abstract base class that defines the foundational operations for a
    memory component within an agent's memory system.

    The memory component is tasked with functions like saving chat histories,
    fetching or storing information in vector databases, and other related
    operations. Every memory system should incorporate at least one instance of
    a subclass derived from :obj:`MemoryBlock`.

    These instances, known as "memories", typically communicate using the
    :obj:`MemoryRecord` object. Usually, a memory has at least one "storage"
    mechanism, allowing it to interface with various storage systems, such as
    disks or vector databases. Additionally, some memories might embed other
    memory instances, enabling them to function as a high-level controller
    within the broader memory system.

    By default, when executing the :obj:`step()` method, an agent retrieves
    messages from its designated memory and combines them with an incoming
    message for input to the agent. Subsequently, both the response message and
    the incoming messages are archived back into the memory.
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
        r"""Clears all messages from the memory.
        """
        pass


class AgentMemory(MemoryBlock, ABC):

    @abstractmethod
    def retrieve(self) -> List[ContextRecord]:
        pass

    @abstractmethod
    def get_context_creator(self) -> BaseContextCreator:
        pass

    def get_context(self) -> Tuple[List[OpenAIMessage], int]:
        r"""Gets chat context with a proper size for the agent from the memory.

        Returns:
            (List[OpenAIMessage], int): A tuple containing the constructed
                context in OpenAIMessage format and the total token count.
        """
        return self.get_context_creator().create_context(self.retrieve())
