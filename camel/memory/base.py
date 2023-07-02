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
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from camel.memory.chat_message_histories import BaseChatMessageHistory


@dataclass
class BaseMemory:
    r"""Base interface for memory in the CAMEL chat system.

    This class provides the methods for loading memory variables, saving context, and clearing memory.
    """

    def memory_variables(self) -> List[str]:
        r"""Provides the memory variables that this class will load dynamically.

        Returns:
            List[str]: The list of memory variables.
        """
        raise NotImplementedError

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        r"""Returns key-value pairs given the text input to the CAMEL chat system.

        Args:
            inputs (Dict[str, Any]): The text inputs to the CAMEL chat system.

        Returns:
            Dict[str, Any]: A dictionary of the key-value pairs. If None, all memories are returned.
        """
        raise NotImplementedError

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str,
                                                                 str]) -> None:
        r"""Saves the context of this model run to memory.

        Args:
            inputs (Dict[str, Any]): The inputs to the CAMEL chat system.
            outputs (Dict[str, str]): The outputs from the CAMEL chat system.
        """
        raise NotImplementedError

    def clear(self) -> None:
        r"""Clears the memory contents."""
        raise NotImplementedError


@dataclass
class BaseChatMemory(BaseMemory):
    r"""Base class for chat memory objects used in CAMEL chat system.

    Args:
        chat_memory (BaseChatMessageHistory): The history of chat messages.
            Defaults to ChatMessageHistory.
        output_key (Optional[str]): The output key. Defaults to None.
        input_key (Optional[str]): The input key. Defaults to None.
        return_messages (bool): Whether to return messages. Defaults to False.
    """
    chat_memory: BaseChatMessageHistory
    output_key: Optional[str]
    input_key: Optional[str]
    return_messages: bool

    def __init__(
        self,
        chat_memory: BaseChatMessageHistory = ChatMessageHistory(),
        output_key: Optional[str] = None,
        input_key: Optional[str] = None,
        return_messages: bool = False,
    ):
        self.chat_memory = chat_memory
        self.output_key = output_key
        self.input_key = input_key
        self.return_messages = return_messages

    def _get_input_output(self, inputs: Dict[str, Any],
                          outputs: Dict[str, str]) -> Tuple[str, str]:
        r"""Get input and output keys.

        Args:
            inputs (Dict[str, Any]): Inputs dictionary.
            outputs (Dict[str, str]): Outputs dictionary.

        Returns:
            Tuple[str, str]: Input and output keys.
        """
        if self.input_key is None:
            prompt_input_key = get_prompt_input_key(inputs,
                                                    self.memory_variables)
        else:
            prompt_input_key = self.input_key

        if self.output_key is None:
            if len(outputs) != 1:
                raise ValueError(
                    f"One output key expected, got {outputs.keys()}")
            output_key = list(outputs.keys())[0]
        else:
            output_key = self.output_key

        return inputs[prompt_input_key], outputs[output_key]

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str,
                                                                 str]) -> None:
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
