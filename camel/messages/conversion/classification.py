# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========


from pydantic import BaseModel, Field, field_validator
import re

class ClassificationItem(BaseModel):
    r"""Represents a text sample labeled with a classification category.

    Attributes:
        text (str): The input text that is classified.
        label (str): The category or classification of the text.
    """
    text: str = Field(
        min_length=1,
        description="The text input to be classified."
    )
    label: str = Field(
        min_length=1,
        description="The classification label."
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        r"""Ensures that the text is non-empty and contains valid characters."""
        if not re.search(r"[a-zA-Z0-9]", value):
            raise ValueError("Text must contain at least one alphanumeric character.")
        return value.strip()

    @field_validator("label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        r"""Ensures that the label is non-empty and meaningful."""
        return value.strip()

    def to_string(self) -> str:
        r"""Convert the ClassificationItem into a formatted string."""
        return f"Text:\n{self.text}\n\nLabel:\n{self.label}"

    @classmethod
    def from_string(cls, text: str) -> "ClassificationItem":
        r"""
        Parses a formatted classification string into a ClassificationItem.

        Args:
            text (str): A string in the format:
                "Text: <text>\nLabel: <label>"

        Returns:
            ClassificationItem: Parsed instance.

        Raises:
            ValueError: If the text format is incorrect.
        """
        text = text.strip()
        match = re.search(r"Text:\s*(.+?)\nLabel:\s*(.+)", text, re.DOTALL)

        if not match:
            raise ValueError("Invalid format. Expected 'Text: <text>\\nLabel: <label>'.")

        text_content, label = match.groups()
        return cls(text=text_content.strip(), label=label.strip())
