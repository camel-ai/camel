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
from typing import List

from camel.memory.memory_record import MemoryRecord


class BaseMemory(ABC):
    """
    An abstract base class that defines the foundational operations for a
    memory component within an agent's memory system.

    The memory component is tasked with functions like saving chat histories,
    fetching or storing information in vector databases, and other related
    operations. Every memory system should incorporate at least one instance of
    a subclass derived from :obj:`BaseMemory`.

    These instances, known as "memories", typically communicate using the
    :obj:`MemoryRecord` object. Usually, a memory has at least one "storage"
    mechanism, allowing it to interface with various storage systems, such as
    disks or vector databases. Additionally, some memories might embed other
    memory instances, enabling them to function as a high-level controller
    within the broader memory system.

    By default, when executing the :obj:`step()` method, an agent retrieves
    messages from its designated memory and combines them with an incoming
    message for input to a LLM. Subsequently, both the response message and the
    incoming messages are archived back into the memory.
    """

    @abstractmethod
    def retrieve(self) -> List[MemoryRecord]:
        """
        Retrieves messages from the memory based on the current state.

        Returns:
            List[BaseMessage]: A list of messages retrieved from the memory.
        """
        ...

    @abstractmethod
    def write_records(self, records: List[MemoryRecord]) -> None:
        """
        Writes messages to the memory, appending them to existing ones.

        Args:
            msgs (List[BaseMessage]): Messages to be added to the memory.
        """
        ...

    @abstractmethod
    def clear(self) -> None:
        """
        Clears all messages from the memory.
        """
        ...
