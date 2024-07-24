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
from typing import ClassVar, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from camel.prompts import PersonaGeneratorPrompt, TextPrompt


class Persona(BaseModel):
    """A persona is a character in the society.

    Attributes:
        name (Optional[str]): Name of the persona.
        description (Optional[str]): Description of the persona.
        t2p_prompt (Union[TextPrompt, str]): Text to Persona Prompt.
        p2p_prompt (Union[TextPrompt, str]): Persona to Persona Prompt.
    """

    name: Optional[str] = None
    description: Optional[str] = None

    # Field with default_factory to avoid circular import issues
    # Union type allows either TextPrompt or str
    t2p_prompt: Union[TextPrompt, str] = Field(
        default_factory=lambda: PersonaGeneratorPrompt.TEXT_TO_PERSONA,
        description="Text to Persona Prompt",
    )

    # Similar to t2p_prompt, using default_factory for lazy evaluation
    p2p_prompt: Union[TextPrompt, str] = Field(
        default_factory=lambda: PersonaGeneratorPrompt.PERSONA_TO_PERSONA,
        description="Persona to Persona Prompt",
    )

    # Class-level configuration for Pydantic model
    # ClassVar indicates this is a class variable, not an instance variable
    model_config: ClassVar[ConfigDict] = ConfigDict(
        # Allows the use of custom types like TextPrompt
        arbitrary_types_allowed=True,
        # Custom JSON schema configuration
        json_schema_extra={
            "properties": {
                # Ensure t2p_prompt and p2p_prompt are treated as strings in
                # JSON schema
                "t2p_prompt": {"type": "string"},
                "p2p_prompt": {"type": "string"},
            }
        },
    )

    @classmethod
    def model_json_schema(cls):
        r"""Customize the model's JSON schema. This method is used by Pydantic
        v2 for advanced JSON schema modifications.
        """
        schema = super().model_json_schema()
        # Additional schema customizations can be added here
        return schema
