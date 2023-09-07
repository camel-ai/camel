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

from camel.memory.base_memory import BaseMemory
from camel.memory.graph_storage.base import BaseGraphStorage
from camel.messages import BaseMessage

from .episodic_memory import EpisodicMemory
from .procedural_memory import ProceduralMemory
from .semantic_memory import SemanticMemory


class WorkingMemory(BaseMemory):
    """
    A short-term memory directly interact with the environment.
    """

    def __init__(
        self,
        storage: Optional[BaseGraphStorage],
        procedural_memory: Optional[ProceduralMemory] = None,
        episodic_memory: Optional[EpisodicMemory] = None,
        semantic_memory: Optional[SemanticMemory] = None,
    ) -> None:
        super().__init__()
        self.procedural_memory = procedural_memory or ProceduralMemory()
        self.episodic_memory = episodic_memory or EpisodicMemory()
        self.semantic_memory = semantic_memory or SemanticMemory()

    def read(self,
             current_state: Optional[BaseMessage] = None) -> List[BaseMessage]:
        ...

    def write(self, msgs: List[BaseMessage]) -> None:
        ...

    def clear(self) -> None:
        ...
