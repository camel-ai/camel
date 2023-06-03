from typing import List
from dataclasses import dataclass, field
from camel.messages import BaseMessage
from camel.memory.chat_message_histories.base import BaseChatMessageHistory

@dataclass
class SimpleChatMessageHistory(BaseChatMessageHistory):
    r"""A history of messages in a CAMEL chat system.

    Args:
        messages (List[BaseMessage]): A list of messages in the chat history.
    """
    messages: List[BaseMessage] = field(default_factory=list)

    def add_message(self, message: BaseMessage) -> None:
        r"""Add a self-created message to the chat history.

        Args:
            message (BaseMessage): The message to be added.
        """
        self.messages.append(message)

    def clear(self) -> None:
        r"""Clears all messages from the chat history."""
        self.messages = []
