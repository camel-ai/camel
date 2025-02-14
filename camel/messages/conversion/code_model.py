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

from pydantic import BaseModel, Field, field_validator, ValidationError
import re

class CodeItem(BaseModel):
    r"""
    Represents a code snippet paired with a description.

    Attributes:
        description (str): A clear instruction or requirement for the code.
        code (str): The actual code snippet.
    """
    description: str = Field(
        min_length=5,
        max_length=500,
        description="A clear requirement or description of the code."
    )
    code: str = Field(
        min_length=5,
        max_length=5000,
        description="The actual code snippet."
    )

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        r"""Ensures that the provided code follows basic coding patterns."""
        code_keywords = ["def", "class", "return", "import", "print", "if", "else", "for", "while", "try", "except"]

        if not any(keyword in value for keyword in code_keywords):
            raise ValueError("Code does not appear to be valid programming code.")

        if re.search(r"[^\x20-\x7E\t\n]", value):  # Non-ASCII or control characters
            raise ValueError("Code contains invalid characters.")

        return value.strip()

    def to_string(self) -> str:
        r"""Convert the CodeItem into a formatted string."""
        return f"Description:\n{self.description}\n\nCode:\n{self.code}"

    @classmethod
    def from_string(cls, text: str) -> "CodeItem":
        r"""
        Parses a formatted Code string into a CodeItem.

        Args:
            text (str): A string in the format:
                "Description: <description>\nCode:\n<code>"

        Returns:
            CodeItem: Parsed instance of CodeItem.

        Raises:
            ValueError: If the text format is incorrect.
        """
        text = text.strip()
        match = re.search(r"Description:\s*(.+?)\nCode:\s*(.+)", text, re.DOTALL)

        if not match:
            raise ValueError("Invalid format. Expected 'Description: <description>\\nCode:\\n<code>'.")

        description, code = match.groups()
        return cls(description=description.strip(), code=code.strip())

