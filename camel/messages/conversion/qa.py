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


from pydantic import BaseModel, Field
import re

class QAItem(BaseModel):
    r"""Represents a simple question-answer pair.

    Attributes:
        question (str): The question being asked.
        answer (str): The corresponding answer to the question.
    """
    question: str = Field(
        min_length=1,
        description="The question being asked."
    )
    answer: str = Field(
        min_length=1,
        description="The corresponding answer to the question. Must be at least 1 character."
    )
    def to_string(self) -> str:
        r"""Convert the QA item into a formatted string."""
        return f"Question: {self.question}\nAnswer: {self.answer}"

    @classmethod
    def from_string(cls, text: str) -> "QAItem":
        r"""Parses a formatted Q/A string into a QAItem.

        Args:
            text (str): A string in the format:
                "Question: <question>\nAnswer: <answer>"

        Returns:
            QAItem: Parsed instance of QAItem.

        Raises:
            ValueError: If the text format is incorrect.
        """
        text = text.strip()
        match = re.search(r"Question:\s*(.+?)\nAnswer:\s*(.+)", text, re.DOTALL)

        if not match:
            raise ValueError("Invalid format. Expected 'Question: <question>\\nAnswer: <answer>'.")

        question, answer = match.groups()
        return cls(question=question.strip(), answer=answer.strip())
