# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========


from pydantic import BaseModel, Field, field_validator
from typing import List
import re

class EntityItem(BaseModel):
    r"""Represents an individual entity in the text.

    Attributes:
        entity (str): The entity name found in the text.
        type (str): The category of the entity (e.g., Person, Organization, Location, Date).
    """
    entity: str = Field(
        min_length=1,
        description="The entity name found in the text."
    )
    type: str = Field(
        min_length=1,
        description="The category of the entity (e.g., Person, Organization, Location, Date)."
    )

    @field_validator("entity", "type")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        r"""Ensures that entity and type are non-empty and stripped."""
        return value.strip()

class EntityRecognitionItem(BaseModel):
    r"""Represents text with labeled entities.

    Attributes:
        text (str): The input text containing named entities.
        entities (List[EntityItem]): A list of extracted entities.
    """
    text: str = Field(
        min_length=1,
        description="The input text containing named entities."
    )
    entities: List[EntityItem] = Field(
        description="A list of extracted entities."
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        r"""Ensures that the text is non-empty and contains valid characters."""
        if not re.search(r"[a-zA-Z0-9]", value):
            raise ValueError("Text must contain at least one alphanumeric character.")
        return value.strip()

    def to_string(self) -> str:
        r"""Convert the EntityRecognitionItem into a formatted string."""
        entity_strings = "\n".join([f"- {e.entity}: {e.type}" for e in self.entities])
        return f"Text:\n{self.text}\n\nEntities:\n{entity_strings}"

    @classmethod
    def from_string(cls, text: str) -> "EntityRecognitionItem":
        r"""
        Parses a formatted Entity Recognition string into an EntityRecognitionItem.

        Args:
            text (str): A string in the format:
                "Text: <text>\nEntities:\n- <entity>: <type>\n- <entity>: <type>"

        Returns:
            EntityRecognitionItem: Parsed instance.

        Raises:
            ValueError: If the text format is incorrect.
        """
        text = text.strip()

        # Extract text content
        text_match = re.search(r"Text:\s*(.+?)\nEntities:\s*", text, re.DOTALL)
        if not text_match:
            raise ValueError("Invalid format. Expected 'Text: <text>\\nEntities: <entities>'.")

        extracted_text = text_match.group(1).strip()

        # Extract entities
        entity_matches = re.findall(r"-\s*(.+?)\s*:\s*(.+)", text)
        if not entity_matches:
            raise ValueError("Invalid entity format. Expected '- <entity>: <type>'.")

        entities = [EntityItem(entity=e.strip(), type=t.strip()) for e, t in entity_matches]

        return cls(text=extracted_text, entities=entities)
