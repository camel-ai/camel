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

from camel.memory.base_memory import BaseMemoryStorage
from camel.messages.base import BaseMessage


class BaseLongTermStorage(BaseMemoryStorage, ABC):
    """
    Abstract base class representing the basic operations
    required for long-term memory storage.

    Inherits the fundamental memory operations from BaseMemory.
    Additional long-term specific operations can be added here.
    """

    @abstractmethod
    def archive(self, msg: BaseMessage) -> None:
        """
        Archives a message in long-term storage. Archiving may differ
        from standard storage in terms of compression, backup, redundancy, etc.

        Args:
            msg (BaseMessage): The message to be archived.
        """
        pass

    @abstractmethod
    def retrieve_archived(self, id: str) -> BaseMessage:
        """
        Retrieves an archived message from long-term storage based on its identifier.

        Args:
            id (str): The unique identifier of the archived message.

        Returns:
            BaseMessage: The retrieved archived message.
        """
        pass
