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
import uuid
from typing import Dict, List, Optional, Union

from camel.agents import ChatAgent
from camel.embeddings import SentenceTransformerEncoder
from camel.messages import BaseMessage
from camel.models import BaseModelBackend
from camel.personas import Persona
from camel.prompts import TextPrompt


class PersonaHub:
    r"""PersonaHub proposes a novel persona-driven data synthesis methodology
    that leverages various perspectives within a large language model (LLM) to
    create diverse synthetic data. By showcasing PersonaHub's use cases in
    synthesizing high-quality mathematical and logical reasoning problems,
    instructions (i.e., user prompts), knowledge-rich texts, game NPCs and
    tools (functions) at scale, the authors demonstrate persona-driven data
    synthesis is versatile, scalable, flexible, and easy to use, potentially
    driving a paradigm shift in synthetic data creation and applications in
    practice, which may have a profound impact on LLM research and development.
    Please refer to the paper for more details: https://arxiv.org/pdf/2406.20094

    Args:
        model (BaseModelBackend, optional): The model to use for persona
        generation and manipulation.
    """

    def __init__(
        self,
        model: Optional[BaseModelBackend] = None,
    ):
        self.model = model
        self.personas: Dict[uuid.UUID, Persona] = {}

    def __setitem__(self, persona: Persona):
        r"""Add a persona to the group.

        Args:
            persona (Persona): The persona to add.
        """
        self.personas[persona.id] = persona

    def __delitem__(self, persona_id: uuid.UUID):
        r"""Remove a persona from the group by ID.

        Args:
            persona_id (uuid.UUID): The ID of the persona to remove.
        """
        if persona_id in self.personas:
            del self.personas[persona_id]
        else:
            raise KeyError("Persona ID not found")

    def __getitem__(self, persona_id: uuid.UUID) -> Persona:
        """Get a persona by ID.

        Args:
            persona_id (uuid.UUID): The ID of the persona to retrieve.
        """
        if persona_id in self.personas:
            return self.personas[persona_id]
        else:
            raise KeyError("Persona ID not found")

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
        persona = Persona()

        t2p_prompt: Union[TextPrompt, str] = persona.t2p_prompt
        t2p_prompt_instruction = t2p_prompt.format(action=action, text=text)

        t2p_prompt_instruction_msg = BaseMessage.make_user_message(
            role_name="User",
            content=t2p_prompt_instruction,
        )

        sys_msg = BaseMessage.make_assistant_message(
            role_name="System",
            content="I am a helpful assistant",
        )

        t2p_agent = ChatAgent(system_message=sys_msg, model=self.model)
        t2p_agent.reset()

        from pydantic import BaseModel, Field

        class PersonaResponse(BaseModel):
            persona_name: str = Field(description="The name of the persona")
            persona_description: str = Field(
                description="The description of the persona"
            )

        response = t2p_agent.step(
            t2p_prompt_instruction_msg,
            output_schema=PersonaResponse,  # type: ignore[arg-type]
        )

        if response.terminated:
            raise RuntimeError("Text to persona step failed.")
        msg: BaseMessage = response.msg

        import ast

        parsed_content = ast.literal_eval(msg.content)
        persona.name = parsed_content["persona_name"]
        persona.description = parsed_content["persona_description"]

        return persona

    def persona_to_persona(self, persona: Persona) -> Dict[uuid.UUID, Persona]:
        r"""Derives additional personas based on interpersonal relationships
        from this persona.

        Args:
            persona (Persona): The persona from which to derive related
            personas.

        Returns:
            Dict[uuid.UUID, Persona]: A dictionary of related personas.
        """
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

        sys_msg = BaseMessage.make_assistant_message(
            role_name="System",
            content="I am a helpful assistant",
        )

        p2p_agent = ChatAgent(system_message=sys_msg, model=self.model)
        p2p_agent.reset()

        response = p2p_agent.step(p2p_prompt_instruction_msg)

        if response.terminated:
            raise RuntimeError("Persona to persona step failed.")
        msg: BaseMessage = response.msg

        import re

        # Structured output (TODO: Use a more robust parser)
        pattern = r"(\d+)\.\s*persona_name:\s*(.*?)\s*persona_description:\s*(.*?)\s*(?=\d+\.|$)"  # noqa: E501
        matches = re.findall(pattern, msg.content, re.DOTALL)

        personas: Dict[uuid.UUID, Persona] = {}
        for match in matches:
            name = match[1].strip()
            description = match[2].strip()
            new_persona = Persona(name=name, description=description)
            personas[new_persona.id] = new_persona

        return personas

    def deduplicate(self, similarity_threshold: float = 0.9):
        r"""Remove similar personas from the group.

        Args:
            similarity_threshold (float): The similarity threshold for
            deduplication (default is 0.9).
        """
        # This is a simplified version. Need to implement a more
        # sophisticated deduplication algorithm as described in the paper.
        unique_personas: Dict[uuid.UUID, Persona] = {}
        for persona_id, persona in self.personas.items():
            if not any(
                self.is_similar(persona, up, similarity_threshold)
                for up in unique_personas.values()
            ):
                unique_personas[persona_id] = persona
        self.personas = unique_personas

    def is_similar(
        self, persona1: Persona, persona2: Persona, threshold: float
    ) -> bool:
        r"""Check if two personas are similar."""
        sentence_encoder = SentenceTransformerEncoder(
            model_name='all-mpnet-base-v2'
        )  # Using all-mpnet-base-v2, may switch to other models

        # Ensure persona descriptions are not None
        persona1_description = persona1.description or ""
        persona2_description = persona2.description or ""

        persona1_embeddings = sentence_encoder.embed(persona1_description)
        persona2_embeddings = sentence_encoder.embed(persona2_description)

        import numpy as np

        def cosine_similarity(vec1, vec2):
            return np.dot(vec1, vec2) / (
                np.linalg.norm(vec1) * np.linalg.norm(vec2)
            )

        similarity = cosine_similarity(
            np.array(persona1_embeddings), np.array(persona2_embeddings)
        )

        return similarity >= threshold

    def __len__(self):
        return len(self.personas)

    def __iter__(self):
        return iter(self.personas.values())

    def get_all_personas(self) -> List[Persona]:
        r"""Return a list of all personas."""
        return list(self.personas.values())
