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

from dataclasses import asdict
from typing import List, Optional

from camel.memory.base_memory import BaseMemory
from camel.memory.lossless_storage.base import LosslessStorage
from camel.memory.lossless_storage.in_memory import InMemoryStorage
from camel.messages.base import BaseMessage


class ChatHistoryMemory(BaseMemory):
    """_summary_

    Args:
        BaseMemory (_type_): _description_
    """

    def __init__(self, storage: Optional[LosslessStorage] = None) -> None:
        """
        Reads the latest message from memory. If no messages are present,
            returns None.

        Returns:
            Optional[BaseMessage]: The latest message or None if memory
                is empty.
        """
        self.storage = storage or InMemoryStorage()

    def read(self,
             current_state: Optional[BaseMessage] = None) -> List[BaseMessage]:
        """
        Reads a message or messages from memory.

        Returns:
            Union[BaseMessage, List[BaseMessage]]: Retrieved message or list of
                messages.
        """
        return [BaseMessage(record) for record in self.storage.load()]

    def write(self, msgs: List[BaseMessage]) -> None:
        """
        Writes a message to memory.

        Args:
            msg (BaseMessage): The message to be written.
        """
        self.storage.save([asdict(msg) for msg in msgs])

    def clear(self) -> None:
        """
        Clears all messages from memory.
        """
        self.storage.clear()
