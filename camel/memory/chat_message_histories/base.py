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
from camel.messages import AssistantChatMessage, BaseMessage, UserChatMessage


@dataclass
class BaseChatMessageHistory:
    r"""Base interface for chat message history.

    Args:
        messages (List[BaseMessage]): List of base messages.

    Example:
        .. code-block:: python

            class FileChatMessageHistory(BaseChatMessageHistory):
                storage_path: str
                session_id: str

                @property
                def messages(self) -> List[BaseMessage]:
                    with open(os.path.join(storage_path, session_id), 'r:utf-8') as f:
                        messages = json.loads(f.read())
                    return messages_from_dict(messages)

                def add_message(self, message: BaseMessage) -> None:
                    messages = self.messages.append(_message_to_dict(message))
                    with open(os.path.join(storage_path, session_id), 'w') as f:
                        json.dump(f, messages)

                def clear(self) -> None:
                    with open(os.path.join(storage_path, session_id), 'w') as f:
                        f.write("[]")
    """

    messages: List[BaseMessage]

    def add_user_message(self, message: str) -> None:
        r"""Add a user message to the store.

        Args:
            message (str): The user message to be added.

        Returns:
            None
        """
        self.add_message(UserChatMessage(role_name=role_name, content=message))

    def add_assistant_message(self, message: str) -> None:
        r"""Add an AI message to the store.

        Args:
            message (str): The AI message to be added.

        Returns:
            None
        """
        self.add_message(
            AssistantChatMessage(role_name=role_name, content=message))

    def add_message(self, message: BaseMessage) -> None:
        r"""Add a self-created message to the store.

        Args:
            message (BaseMessage): The message to be added.

        Raises:
            NotImplementedError: This method should be overridden by subclasses.
        """
        raise NotImplementedError(
            "The method 'add_message' is not implemented")

    def clear(self) -> None:
        r"""Remove all messages from the store.

        Raises:
            NotImplementedError: This method should be overridden by subclasses.
        """
        raise NotImplementedError("The method 'clear' is not implemented")
