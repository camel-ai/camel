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

from typing import List, Optional

from camel.embedding.base import BaseEmbedding
from camel.embedding.openai_embedding import OpenAiEmbedding
from camel.memory.base_memory import BaseMemory
from camel.memory.vector_storage.base import BaseVectorStorage
from camel.memory.vector_storage.qdrant import Qdrant
from camel.messages.base import BaseMessage


class VectorDBMemory(BaseMemory):

    def __init__(self, storage: Optional[BaseVectorStorage] = None,
                 embedding: Optional[BaseEmbedding] = None):
        """
        Initializes a new instance of LongTermMemory.

        Args:
            storage (Optional[BaseLongTermStorage]): The storage mechanism for
                long-term memory.
        """
        self.storage = storage or Qdrant()
        self.embedding = embedding or OpenAiEmbedding()

    def read(self,
             current_state: Optional[BaseMessage] = None) -> List[BaseMessage]:
        """
        Reads a message or messages from memory.

        Returns:
            Union[BaseMessage, List[BaseMessage]]: Retrieved message or list
                of messages.
        """
        if current_state is None:
            raise RuntimeError(
                "Readling vector database memeory without message input")
        self.embedding.embed(current_state)

    def write(self, msgs: List[BaseMessage]) -> None:
        """
        Writes a message to memory.

        Args:
            msg (BaseMessage): The message to be written.
        """
        ...

    def clear(self) -> None:
        """
        Clears all messages from memory.
        """
        ...
