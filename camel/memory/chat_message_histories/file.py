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
from dataclasses import dataclass
from pathlib import Path
import json
import logging

from camel.memory.chat_message_histories import BaseChatMessageHistory
from camel.messages import BaseMessage

logger = logging.getLogger(__name__)

@dataclass
class FileChatMessageHistory(BaseChatMessageHistory):
    r"""
    Chat message history that stores history in a local file.

    Args:
        file_path (str): path of the local file to store the messages.
    """
    file_path: str

    def __post_init__(self):
        self.file_path = Path(self.file_path)
        if not self.file_path.exists():
            self.file_path.touch()
            self.file_path.write_text(json.dumps([]))

    def messages(self) -> List[BaseMessage]:
        r"""Retrieve the messages from the local file.

        Returns:
            List[BaseMessage]: The list of :obj:`BaseMessage` objects.
        """
        items = json.loads(self.file_path.read_text())
        messages = messages_from_dict(items)
        return messages

    def add_message(self, message: BaseMessage) -> None:
        r"""Append the message to the record in the local file.

        Args:
            message (BaseMessage): The :obj:`BaseMessage` object to be appended.
        """
        messages = messages_to_dict(self.messages)
        messages.append(messages_to_dict([message])[0])
        self.file_path.write_text(json.dumps(messages))

    def clear(self) -> None:
        r"""Clear session memory from the local file."""
        self.file_path.write_text(json.dumps([]))
