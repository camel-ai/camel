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
from abc import ABC, abstractmethod
from typing import List, Tuple

from camel.memories.memory_record import ContextRecord
from camel.messages import OpenAIMessage
from camel.utils.token_counting import BaseTokenCounter


class BaseContextCreator(ABC):
    r"""An abstract base class defining the interface for context creation
    strategies.

    This class provides a foundational structure for different strategies to
    generate conversational context from a list of context records. The primary
    goal is to create a context that is aligned with a specified token count
    limit, allowing subclasses to define their specific approach.

    Subclasses should implement the `token_counter`, `token_limit`, and
    `create_context` methods to provide specific context creation logic.

    Attributes:
        token_counter (BaseTokenCounter): A token counter instance responsible
            for counting tokens in a message.
        token_limit (int): The maximum number of tokens allowed in the
            generated context.
    """

    @property
    @abstractmethod
    def token_counter(self) -> BaseTokenCounter:
        pass

    @property
    @abstractmethod
    def token_limit(self) -> int:
        pass

    @abstractmethod
    def create_context(
            self,
            records: List[ContextRecord]) -> Tuple[List[OpenAIMessage], int]:
        r"""An abstract method to create conversational context from the chat history.

        Constructs the context from provided records. The specifics of how this
        is done and how the token count is managed should be provided by
        subclasses implementing this method. The the output messages order
        should keep same as the input order.

        Args:
            records (List[ContextRecord]): A list of context records from
                which to generate the context.

        Returns:
            Tuple[List[OpenAIMessage], int]: A tuple containing the constructed
                context in OpenAIMessage format and the total token count.
        """
        pass
