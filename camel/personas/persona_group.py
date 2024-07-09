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

from .persona import Persona


class Group:
    r"""A group of personas. This class manages a collection of Persona
    instances and provides methods for adding, removing, and manipulating
    personas within the group.

    Args:
        group_name (str): The name of the group.
        group_description (str, optional): A description of the group.
    """

    def __init__(
        self, group_name: str, group_description: Optional[str] = None
    ):
        self.group_name = group_name
        self.group_description = group_description
        self.personas: List[Persona] = []

    def add_persona(self, persona: Persona):
        r"""Add a persona to the group."""
        self.personas.append(persona)

    def remove_persona(self, index: int):
        r"""Remove a persona from the group by index."""
        if 0 <= index < len(self.personas):
            del self.personas[index]
        else:
            raise IndexError("Persona index out of range")

    def get_persona(self, index: int) -> Persona:
        r"""Get a persona by index."""
        if 0 <= index < len(self.personas):
            return self.personas[index]
        else:
            raise IndexError("Persona index out of range")

    def deduplicate(self, similarity_threshold: float = 0.9):
        r"""Remove similar personas from the group."""
        # This is a simplified version. You might want to implement a more
        # sophisticated deduplication algorithm as described in the paper.
        unique_personas: List[Persona] = []
        for persona in self.personas:
            if not any(
                self._is_similar(persona, up, similarity_threshold)
                for up in unique_personas
            ):
                unique_personas.append(persona)
        self.personas = unique_personas

    def _is_similar(
        self, persona1: Persona, persona2: Persona, threshold: float
    ) -> bool:
        r"""Check if two personas are similar."""
        # This is a placeholder. You should implement a proper similarity
        # check, possibly using embedding-based methods as suggested in the
        # paper.
        return False  # Placeholder return

    def __len__(self):
        return len(self.personas)

    def __iter__(self):
        return iter(self.personas)
