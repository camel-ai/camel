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
import re
from typing import List, Optional, Union

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.messages import BaseMessage
from camel.models import BaseModelBackend, ModelFactory
from camel.personas import Persona
from camel.prompts import TextPrompt
from camel.types import ModelPlatformType, ModelType, RoleType


class PersonaGenerator(ChatAgent):
    r"""A generator of personas. This class manages a collection of Persona
    instances and provides methods for adding, removing, and manipulating
    personas within the group.

    Args:
        model (BaseModelBackend, optional): The model to use for persona
        group_name (str, optional): The name of the group.
        group_description (str, optional): A description of the group.
    """

    def __init__(
        self,
        model: Optional[BaseModelBackend] = None,
    ):
        system_message = BaseMessage(
            role_name="",
            role_type=RoleType.ASSISTANT,
            meta_dict=None,
            content="",
        )
        self.model = model if model else ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.GPT_4O_MINI,
            model_config_dict=ChatGPTConfig().__dict__,
            api_key=self._api_key,
        )
        super().__init__(system_message, model=model)
        self.personas: List[Persona] = []

    def add_persona(self, persona: Persona):
        r"""Add a persona to the group."""
        self.personas.append(persona)

    def __delitem__(self, index: int):
        r"""Remove a persona from the group by index.

        Args:
            index (int): The index of the persona to remove.
        """
        if 0 <= index < len(self.personas):
            del self.personas[index]
        else:
            raise IndexError("Persona index out of range")

    def __getitem__(self, index: int) -> Persona:
        r"""Get a persona by index.

        Args:
            index (int): The index of the persona to get.
        """
        if 0 <= index < len(self.personas):
            return self.personas[index]
        else:
            raise IndexError("Persona index out of range")

    def text_to_persona(self, text: str, action: str = "read") -> Persona:
        r"""Infers a specific persona who is likely to [read|write|like|dislike
        |...] the given text.

        Args:
            text (str): The input text for which to infer a persona.
            action (str): The action associated with the persona (default is
            "read").

        Returns:
            Persona: The inferred persona.
        """
        super().reset()

        persona = Persona()

        t2p_prompt: Union[TextPrompt, str] = persona.t2p_prompt
        answer_template = """
You MUST answer the question according to the format of the ANSWER TEMPLATE, and you can only modify the content within <BLANK>.
===== ANSWER TEMPLATE =====
persona_name: <BLANK>
persona_description: <BLANK>
"""  # noqa: E501
        t2p_prompt_instruction = (
            t2p_prompt.format(action=action, text=text) + answer_template
        )

        t2p_prompt_instruction_msg = BaseMessage.make_user_message(
            role_name="User",
            content=t2p_prompt_instruction,
        )

        response = self.step(input_message=t2p_prompt_instruction_msg)

        if response.terminated:
            raise RuntimeError("Text to persona step failed.")
        msg: BaseMessage = response.msg

        # Structured output (TODO: Use a more robust parser)
        pattern = (
            r"\s*persona_name:\s*(.*?)\s*persona_description:\s*(.*?)\s*$"
        )
        match = re.match(pattern, msg.content, re.DOTALL)
        if match:
            persona_name = match.group(1).strip()
            persona_description = match.group(2).strip()

        persona.name = persona_name
        persona.description = persona_description

        return persona

    def persona_to_persona(self, persona: Persona) -> List[Persona]:
        r"""Derives additional personas based on interpersonal relationships
        from this persona.

        Args:
            persona (Persona): The persona from which to derive related
            personas.

        Returns:
            List[Persona]: A list of related personas with their relationship
            types.
        """
        super().reset()

        p2p_prompt: Union[TextPrompt, str] = persona.p2p_prompt
        answer_template = """
You MUST answer the question according to the format of the ANSWER TEMPLATE, and you can only modify the content within <BLANK>.
===== ANSWER TEMPLATE =====
1. persona_name: <BLANK>
persona_description: <BLANK>
...
n. persona_name: <BLANK>
persona_description: <BLANK>
"""  # noqa: E501
        p2p_prompt_instruction = (
            p2p_prompt.format(
                persona_name=persona.name,
                persona_description=persona.description,
            )
            + answer_template
        )

        p2p_prompt_instruction_msg = BaseMessage.make_user_message(
            role_name="User",
            content=p2p_prompt_instruction,
        )

        response = self.step(input_message=p2p_prompt_instruction_msg)

        if response.terminated:
            raise RuntimeError("Persona to persona step failed.")
        msg: BaseMessage = response.msg

        # Structured output (TODO: Use a more robust parser)
        pattern = r"(\d+)\.\s*persona_name:\s*(.*?)\s*persona_description:\s*(.*?)\s*(?=\d+\.|$)"  # noqa: E501
        matches = re.findall(pattern, msg.content, re.DOTALL)

        personas: List[Persona] = []
        for match in matches:
            name = match[1].strip()
            description = match[2].strip()
            personas.append(
                Persona(
                    name=name,
                    description=description,
                )
            )

        for persona in personas:
            self.add_persona(persona)

        return personas

    def deduplicate(self, similarity_threshold: float = 0.9):
        r"""Remove similar personas from the group."""
        # This is a simplified version. Need to implement a more
        # sophisticated deduplication algorithm as described in the paper.
        unique_personas: List[Persona] = []
        for persona in self.personas:
            if not any(
                self.is_similar(persona, up, similarity_threshold)
                for up in unique_personas
            ):
                unique_personas.append(persona)
        self.personas = unique_personas

    def is_similar(
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
