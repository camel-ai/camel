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

from camel.memory.base_memory import BaseMemory, MemoryRecord
from camel.memory.dict_storage.base import BaseDictStorage
from camel.memory.dict_storage.in_memory import InMemoryDictStorage
from camel.typing import OpenAIBackendRole


class ChatHistoryMemory(BaseMemory):
    """
    An implementation of the :obj:`BaseMemory` abstract base class for
    maintaining a record of chat histories.

    This memory class helps manage conversation histories with a designated
    storage mechanism, either provided by the user or using a default
    in-memory storage. It offers a windowed approach to retrieving chat
    histories, allowing users to specify how many recent messages they'd
    like to fetch.

    `ChatHistoryMemory` requires messages to be stored with certain
    metadata (e.g., `role_at_backend`) to maintain consistency and validate
    the chat history.

    Args:
        storage (BaseDictStorage): A storage mechanism for storing chat
            history.
        window_size (int, optional): Specifies the number of recent chat
            messages to retrieve. If not provided, the entire chat history
            will be retrieved.
    """

    def __init__(self, storage: Optional[BaseDictStorage] = None,
                 window_size: Optional[int] = None) -> None:
        self.storage = storage or InMemoryDictStorage()
        self.window_size = window_size

    def retrieve(self) -> List[MemoryRecord]:
        """
        Retrieves chat messages from the memory based on the window size or
        fetches the entire chat history if no window size is specified.

        Returns:
            List[MemoryRecord]: A list of memory records retrieved from the
                memory.

        Raises:
            ValueError: If the memory is empty or if the first message in the
                memory is not a system message.
        """
        record_dicts = self.storage.load()
        if len(record_dicts) == 0:
            raise ValueError("The ChatHistoryMemory is empty.")

        system_record = MemoryRecord.from_dict(record_dicts[0])
        if system_record.role_at_backend != OpenAIBackendRole.SYSTEM:
            raise ValueError(
                "The first record in ChatHistoryMemory should contain a system"
                " message.")

        chat_records: List[MemoryRecord] = []
        truncate_idx = 1 if self.window_size is None else -self.window_size
        for record_dict in record_dicts[truncate_idx:]:
            chat_records.append(MemoryRecord.from_dict(record_dict))

        return [system_record] + chat_records

    def write_records(self, records: List[MemoryRecord]) -> None:
        """
        Writes memory records to the memory. Additionally, performs validation
        checks on the messages.

        Args:
            msgs (List[MemoryRecord]): Memory records to be added to the
                memory.
        """
        stored_records = []
        for record in records:
            stored_records.append(record.to_dict())
        self.storage.save(stored_records)

    def clear(self) -> None:
        """
            Clears all chat messages from the memory.
        """
        self.storage.clear()
