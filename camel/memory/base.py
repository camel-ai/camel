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

