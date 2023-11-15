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

from camel.memories import BaseMemory, ContextRecord
from camel.memories.context_creators import BaseContextCreator
from camel.messages import OpenAIMessage


class AgentMemory(BaseMemory, ABC):

    @abstractmethod
    def retrieve(self) -> List[ContextRecord]:
        pass

    @abstractmethod
    def get_context_creator(self) -> BaseContextCreator:
        pass

    def get_context(self) -> Tuple[List[OpenAIMessage], int]:
        r"""Gets chat context with a proper size for the agent from the memory.

        Returns:
            (List[OpenAIMessage], int): A tuple containing the constructed
                context in OpenAIMessage format and the total token count.
        """
        return self.get_context_creator().create_context(self.retrieve())
