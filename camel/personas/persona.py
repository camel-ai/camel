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

from typing import Optional

from camel.agents import ChatAgent


class Persona(ChatAgent):
    r"""A persona is a character that can be used to generate text.

    Args:
        index (int): The index of the persona.
        name (str): The name of the persona.
        description (str): A description of the persona.
    """

    def __init__(
        self,
        index: int,
        name: Optional[str],
        description: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.index = index
        self.name = name
        self.description = description

    def get_index(self) -> int:
        r"""Get the index of the persona.

        Returns:
            int: The index of the persona.
        """
        return self.index

    def get_name(self) -> Optional[str]:
        r"""Get the name of the persona.

        Returns:
            str: The name of the persona.
        """
        return self.name

    def get_description(self) -> str:
        r"""Get the description of the persona.

        Returns:
            str: The description of the persona.
        """
        return self.description

    def set_index(self, index: int) -> None:
        r"""Set the index of the persona.

        Args:
            index (int): The index of the persona.
        """
        self.index = index

    def set_name(self, name: Optional[str]) -> None:
        r"""Set the name of the persona.

        Args:
            name (str): The name of the persona.
        """
        self.name = name

    def set_description(self, description: str) -> None:
        r"""Set the description of the persona.

        Args:
            description (str): The description of the persona.
        """
        self.description = description
