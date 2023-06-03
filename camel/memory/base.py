from dataclasses import dataclass
from typing import List, Dict, Any
from abc import abstractmethod, ABC

from camel.memory.chat_message_histories import BaseChatMessageHistory
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


@dataclass
class BaseChatMemory:
    r"""Base class for chat memory objects used in CAMEL chat system.

    Args:
        chat_memory (BaseChatMessageHistory): The history of chat messages.
            Defaults to ChatMessageHistory.
        output_key (Optional[str]): The output key. Defaults to None.
        input_key (Optional[str]): The input key. Defaults to None.
        return_messages (bool): Whether to return messages. Defaults to False.
    """
    chat_memory: BaseChatMessageHistory = ChatMessageHistory()
    output_key: Optional[str] = None
    input_key: Optional[str] = None
    return_messages: bool = False

    def _get_input_output(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> Tuple[str, str]:
        r"""Get input and output keys.

        Args:
            inputs (Dict[str, Any]): Inputs dictionary.
            outputs (Dict[str, str]): Outputs dictionary.

        Returns:
            Tuple[str, str]: Input and output keys.
        """
        if self.input_key is None:
            prompt_input_key = get_prompt_input_key(inputs, self.memory_variables)
        else:
            prompt_input_key = self.input_key
        if self.output_key is None:
            if len(outputs) != 1:
                raise ValueError(f"One output key expected, got {outputs.keys()}")
            output_key = list(outputs.keys())[0]
        else:
            output_key = self.output_key
        return inputs[prompt_input_key], outputs[output_key]

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        r"""Save context from this conversation to buffer.

        Args:
            inputs (Dict[str, Any]): Inputs dictionary.
            outputs (Dict[str, str]): Outputs dictionary.
        """
        input_str, output_str = self._get_input_output(inputs, outputs)
        self.chat_memory.add_user_message(input_str)
        self.chat_memory.add_ai_message(output_str)

    def clear(self) -> None:
        r"""Clear memory contents."""
        self.chat_memory.clear()
