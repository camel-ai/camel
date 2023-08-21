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
from camel.memory.short_term_storage.base import BaseShortTermStorage
from camel.memory.short_term_storage.in_memory import InMemoryStorage
from camel.messages.base import BaseMessage


class ShortTermMemory(BaseMemory):
    def __init__(self, storage: Optional[BaseShortTermStorage] = None):
        """
        Initializes a new instance of ShortTermMemory.

        Args:
            storage (Optional[BaseShortTermStorage]): The storage mechanism for short-term memory.
                                                      Defaults to InMemoryStorage if not provided.
        """
        self.memory_storage = storage or InMemoryStorage()

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
