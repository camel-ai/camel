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

from camel.memories import (
    AgentMemory,
    BaseContextCreator,
    ContextRecord,
    MemoryRecord,
)
from camel.memories.blocks import ChatHistoryBlock, VectorDBBlock
from camel.storages import BaseKeyValueStorage, BaseVectorStorage
from camel.types import OpenAIBackendRole


class ChatHistoryMemory(AgentMemory):
    r""""""

    def __init__(
        self,
        context_creator: BaseContextCreator,
        storage: Optional[BaseKeyValueStorage] = None,
        window_size: Optional[int] = None,
    ) -> None:
        self._context_creator = context_creator
        self._window_size = window_size
        self._chat_history_block = ChatHistoryBlock(storage=storage)

    def retrieve(self) -> List[ContextRecord]:
        return self._chat_history_block.retrieve(self._window_size)

    def write_records(self, records: List[MemoryRecord]) -> None:
        self._chat_history_block.write_records(records)

    def get_context_creator(self) -> BaseContextCreator:
        return self._context_creator

    def clear(self) -> None:
        return self._chat_history_block.clear()


class VectorDBMemory(AgentMemory):
    r""""""

    def __init__(
        self,
        context_creator: BaseContextCreator,
        storage: Optional[BaseVectorStorage] = None,
        retrieve_limit=3,
    ) -> None:
        self._context_creator = context_creator
        self._retrieve_limit = retrieve_limit
        self._vectordb_block = VectorDBBlock(storage=storage)

        self._current_topic: str = ""

    def retrieve(self) -> List[ContextRecord]:
        return self._vectordb_block.retrieve(
            self._current_topic,
            limit=self._retrieve_limit,
        )

    def write_records(self, records: List[MemoryRecord]) -> None:
        # Assume the last user input is the current topic.
        for record in records:
            if record.role_at_backend == OpenAIBackendRole.USER:
                self._current_topic = record.message.content
        self._vectordb_block.write_records(records)

    def get_context_creator(self) -> BaseContextCreator:
        return self._context_creator
