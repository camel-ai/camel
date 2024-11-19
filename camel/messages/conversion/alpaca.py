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

from pydantic import BaseModel, Field, field_validator


class AlpacaItem(BaseModel):
    """Represents an instruction-response item in the Alpaca format.

    Handles both cases where input field is empty or populated.
    Provides parsing from string format using the class method from_string().

    Attributes:
        instruction (str): The instruction/question/prompt
        input (str): Input context or examples (empty string if none)
        output (str): The response/answer to the instruction
    """

    instruction: str = Field(..., min_length=1)
    input: str = Field(default="")
    output: str = Field(..., min_length=1)

    @field_validator('instruction', 'output')
    def no_section_markers(cls, v: str) -> str:
        """Ensures fields don't contain section markers like '### Response:'"""
        if '###' in v:
            raise ValueError("Field cannot contain section markers ('###')")
        return v.strip()

    @classmethod
    def from_string(cls, text: str) -> "AlpacaItem":
        """Creates an AlpacaItem from a formatted string.

        Args:
            text: String in either of these formats:
                 With input:
                 ### Instruction:
                 {instruction}
                 ### Input:
                 {input}
                 ### Response:
                 {response}

                 Without input:
                 ### Instruction:
                 {instruction}
                 ### Response:
                 {response}

        Returns:
            AlpacaItem: Parsed instance

        Raises:
            ValueError: text doesn't match expected format or sections missing
        """
        # Strip and standardize newlines
        text = text.strip().replace('\r\n', '\n')

        # Try to extract sections using regex
        instruction_match = re.search(
            r'###\s*Instruction:\s*\n(.+?)(?=\n###|\Z)', text, re.DOTALL
        )
        input_match = re.search(
            r'###\s*Input:\s*\n(.+?)(?=\n###|\Z)', text, re.DOTALL
        )
        response_match = re.search(
            r'###\s*Response:\s*\n(.+?)(?=\n###|\Z)', text, re.DOTALL
        )

        if not instruction_match or not response_match:
            raise ValueError(
                "Text must contain '### Instruction:'"
                " and '### Response:' sections"
            )

        return cls(
            instruction=instruction_match.group(1).strip(),
            input=input_match.group(1).strip() if input_match else "",
            output=response_match.group(1).strip(),
        )

    def to_string(self) -> str:
        """Converts the AlpacaItem to its string representation.

        Returns:
            str: Formatted string representation with sections markers
        """
        return "\n".join(
            [
                "### Instruction:",
                self.instruction,
                "",
                "### Input:",
                self.input,
                "",
                "### Response:",
                self.output,
            ]
        )
