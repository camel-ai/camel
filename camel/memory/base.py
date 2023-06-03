from dataclasses import dataclass
from typing import List, Dict, Any
from abc import abstractmethod, ABC

@dataclass
class BaseMemory(ABC):
    r"""Base interface for memory in chains."""

    @property
    @abstractmethod
    def memory_variables(self) -> List[str]:
        r"""Provides the memory variables that this class will load dynamically."""
        pass

    @abstractmethod
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        r"""Returns key-value pairs given the text input to the chain.

        Args:
            inputs: The text inputs to the chain.

        Returns:
            A dictionary of the key-value pairs. If None, all memories are returned.
        """
        pass

    @abstractmethod
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        r"""Saves the context of this model run to memory.

        Args:
            inputs: The inputs to the chain.
            outputs: The outputs from the chain.
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        r"""Clears the memory contents."""
        pass


class BaseChatMessageHistory(ABC):
    r"""Base interface for chat message history
    See `ChatMessageHistory` for default implementation.
    """

    """
    Example:
        .. code-block:: python

            class FileChatMessageHistory(BaseChatMessageHistory):
                storage_path:  str
                session_id: str

               @property
               def messages(self):
                   with open(os.path.join(storage_path, session_id), 'r:utf-8') as f:
                       messages = json.loads(f.read())
                    return messages_from_dict(messages)

               def add_message(self, message: BaseMessage) -> None:
                   messages = self.messages.append(_message_to_dict(message))
                   with open(os.path.join(storage_path, session_id), 'w') as f:
                       json.dump(f, messages)

               def clear(self):
                   with open(os.path.join(storage_path, session_id), 'w') as f:
                       f.write("[]")
    """

    messages: List[BaseMessage]

    def add_user_message(self, message: str) -> None:
        """Add a user message to the store"""
        self.add_message(HumanMessage(content=message))

    def add_ai_message(self, message: str) -> None:
        """Add an AI message to the store"""
        self.add_message(AIMessage(content=message))

    def add_message(self, message: BaseMessage) -> None:
        """Add a self-created message to the store"""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Remove all messages from the store"""
