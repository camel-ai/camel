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

from typing import Optional

from camel.memory.base_memory import BaseMemory
from camel.memory.long_term_storage.base import BaseLongTermStorage
from camel.messages.base import BaseMessage


class LongTermMemory(BaseMemory):
    def __init__(self, storage: Optional[BaseLongTermStorage] = None):
        """
        Initializes a new instance of LongTermMemory.

        Args:
            storage (Optional[BaseLongTermStorage]): The storage mechanism for long-term memory.
        """
        if storage is None:
            raise ValueError("A valid long-term storage mechanism must be provided.")
        self.memory_storage = storage

    def read(self) -> Optional[BaseMessage]:
        """
        Reads the latest message from memory. If no messages are present, returns None.

        Returns:
            Optional[BaseMessage]: The latest message or None if memory is empty.
        """
        messages = self.memory_storage.load()
        if not messages:
            return None
        return messages[-1]

    def write(self, msg: BaseMessage) -> None:
        """
        Writes a message to memory.

        Args:
            msg (BaseMessage): The message to be written.
        """
        self.memory_storage.store(msg)

    def clear(self) -> None:
        """
        Clears all messages from memory.
        """
        self.memory_storage.clear()

    def archive(self, msg: BaseMessage) -> None:
        """
        Archives a message in long-term storage.

        Args:
            msg (BaseMessage): The message to be archived.
        """
        if hasattr(self.memory_storage, "archive"):
            self.memory_storage.archive(msg)
        else:
            raise NotImplementedError("The storage mechanism does not support archiving.")

    def retrieve_archived(self, id: str) -> BaseMessage:
        """
        Retrieves an archived message from long-term storage based on its identifier.

        Args:
            id (str): The unique identifier of the archived message.

        Returns:
            BaseMessage: The retrieved archived message.
        """
        if hasattr(self.memory_storage, "retrieve_archived"):
            return self.memory_storage.retrieve_archived(id)
        else:
            raise NotImplementedError("The storage mechanism does not support retrieving archived messages.")
