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

import pickle
from dataclasses import asdict
from typing import List, Optional

from camel.memory.base_memory import BaseMemory
from camel.memory.dict_storage.base import DictStorage
from camel.memory.dict_storage.in_memory import InMemoryDictStorage
from camel.messages.base import BaseMessage


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
        storage (DictStorage): A storage mechanism for storing chat
            history.
        window_size (int, optional): Specifies the number of recent chat
            messages to retrieve. If not provided, the entire chat history
            will be retrieved.
    """

    def __init__(self, storage: Optional[DictStorage] = None,
                 window_size: Optional[int] = None) -> None:
        self.storage = storage or InMemoryDictStorage()
        self.window_size = window_size

    def read(self,
             current_state: Optional[BaseMessage] = None) -> List[BaseMessage]:
        """
        Retrieves chat messages from the memory based on the window size or
        fetches the entire chat history if no window size is specified.

        Args:
            current_state (Optional[BaseMessage], optional): This argument is
                available due to the base class but is not utilized in this
                method.

        Returns:
            List[BaseMessage]: A list of chat messages retrieved from the
                memory.

        Raises:
            ValueError: If the memory is empty or if the first message is not a
                system message.
        """
        history_messages = []
        for msg_dict in self.storage.load():
            if "__class__" in msg_dict.keys():
                cls = pickle.loads(msg_dict["__class__"])
                msg_dict.pop("__class__")
                history_messages.append(cls(**msg_dict))
            else:
                history_messages.append(BaseMessage(**msg_dict))

        if len(history_messages) == 0:
            raise ValueError("The ChatHistoryMemory is empty.")
        if history_messages[0].meta_dict["role_at_backend"] != "system":
            raise ValueError(
                "The first message in ChatHistoryMemory should be a system "
                "message.")
        if self.window_size is not None and len(
                history_messages) > self.window_size + 1:
            history_messages = (history_messages[0:1] +
                                history_messages[-self.window_size:])
        return history_messages

    def write(self, msgs: List[BaseMessage]) -> None:
        """
        Writes chat messages to the memory. Additionally, performs validation
        checks on the messages.

        Args:
            msgs (List[BaseMessage]): Messages to be added to the memory.

        Raises:
            ValueError: If the message metadata does not contain
                :obj:`role_at_backend` or if it has an unsupported role.
        """
        stored_msgs = []
        for m in msgs:
            if "role_at_backend" not in m.meta_dict:
                raise ValueError(
                    "Messages storing in ChatHistoryMemory should have "
                    "\"role_at_backend\" key in meta_dict.")
            role = m.meta_dict["role_at_backend"]
            if role not in ['system', 'user', 'assistant', 'function']:
                raise ValueError(f"Unsupported role \"{role}\".")
            msg_dict = asdict(m)
            if type(m) != BaseMessage:
                msg_dict["__class__"] = pickle.dumps(m.__class__)
            stored_msgs.append(msg_dict)
        self.storage.save(stored_msgs)

    def clear(self) -> None:
        """
            Clears all chat messages from the memory.
        """
        self.storage.clear()
