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

import json
import re
from typing import Any, ClassVar, Dict, List, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class ShareGPTMessage(BaseModel):
    r"""A data model for storing information about a conversation item.

    Attributes:
        from_ (Literal["human", "gpt", "function_call", "observation"]):
            The source of the message, indicating who or what generated
            the message.
            - "human": Represents a message from the user.
            - "gpt": Represents a message from the AI assistant.
            - "function_call": Represents a function or tool call made by the
            assistant.
            - "observation": Represents a response or observation from a tool
            or function.
        value (str):
            The content of the message or the value associated with the
            conversation item.

    Notes:
        - Originally created by @Xukun Liu under camel/data_collector/
        sharegpt_collector.py: ConversationItem,
          and @CaelumF under camel/messages/conversion/
        conversation_models.py: ShareGPTMessage,
          refactored by @boerz-coding.
    """

    from_: Literal["human", "gpt", "function_call", "observation"] = Field(
        alias="from", description="The source of the message."
    )
    value: str

    model_config: ClassVar[ConfigDict] = ConfigDict(
        populate_by_name=True,
        extra="forbid",
    )


class ShareGPTData(BaseModel):
    r"""A data model for storing conversation details.

    Attributes:
        system (Optional[str]): The system message associated with the
        conversation.
        tools (Optional[str]): JSON-encoded string representing tools used in
        the conversation.
        conversations (List[ShareGPTMessage]): List of messages exchanged in
        the conversation.


    Notes:
        - Originally created by @Xukun Liu under camel/data_collector/
        sharegpt_collector.py: ShareGPTData,
          and @CaelumF under camel/messages/conversion/
        conversation_models.py: ShareGPTConversation,
          refactored by @boerz-coding.
    """

    system: Optional[str] = None
    tools: Optional[str] = None
    conversations: List[ShareGPTMessage]

    model_config = {
        "extra": "forbid"  # Ensures no unexpected fields are allowed
    }


class AlpacaItem(BaseModel):
    r"""Represents an instruction-response item in the Alpaca format.

    Appropripate for both cases where input field is empty, or populated.
    Provides parsing from string format using the class method from_string().

    Args:
        instruction (str): The instruction/question/prompt
        input (str): Input context or examples (put empty string if none)
        output (str): The response/answer to the instruction
    """

    instruction: str = Field(description="The instruction/question/prompt")
    input: str = Field(
        description="Optional context or input for the task."
        " For example, when the instruction is \"Summarize the "
        "following article\", the input is the article."
    )
    output: str = Field(description="The response/answer to the instruction")

    @field_validator('instruction', 'output')
    def no_section_markers(cls, value: str) -> str:
        r"""Ensures fields don't contain section markers like '###
        Response:'
        """
        if (
            '### Response' in value
            or '### Instruction' in value
            or '### Input' in value
        ):
            raise ValueError("Field cannot contain section markers")
        return value.strip()

    @classmethod
    def from_string(cls, text: str) -> "AlpacaItem":
        r"""Creates an AlpacaItem from a formatted string.

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

        Notes:
            Originally created by @CaelumF under camel/messages/conversion/
            alpaca.py
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
        r"""Converts the AlpacaItem to its string representation.

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


class ToolCall(BaseModel):
    r"""A data model for representing a validated tool or function call.

    Attributes:
        name (str):
            The name of the tool to be called.
            Must be between 1 and 256 characters in length.
        arguments (Dict[str, Any]):
            A dictionary containing key-value pairs of arguments
            to be passed to the tool. Must be JSON-serializable.

    Notes:
        Originally created by @CaelumF under camel/messages/conversion/
        conversation_models.py: ToolCall
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="The name of the tool to call.",
    )
    arguments: Dict[str, Any] = Field(
        ...,
        description="A dictionary containing arguments to pass to the tool.",
    )

    @field_validator("arguments")
    @classmethod
    def validate_arguments(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validates that the arguments are JSON-serializable."""
        try:
            json.dumps(v, ensure_ascii=False)
        except (TypeError, ValueError):
            raise ValueError("Arguments must be JSON-serializable.")
        return v

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "name": "get_weather",
                    "arguments": {"city": "London", "units": "celsius"},
                }
            ]
        },
    }


class ToolResponse(BaseModel):
    r"""A data model for representing a validated tool or function response.

    Attributes:
        name (str):
            The name of the tool that was called.
            Must be between 1 and 256 characters in length.
        content (Any):
            The response content from the tool.
            Must be a JSON-serializable literal or object.

    Notes:
        Originally created by @CaelumF under camel/messages/conversion/
        conversation_models: ToolResponse
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="The name of the tool that was called.",
    )
    content: Any = Field(
        ...,
        description="The response content from the tool. Must be"
        " a JSON-serializable literal or object.",
    )

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validates that the response content is JSON-serializable."""
        try:
            json.dumps(v, ensure_ascii=False)
        except (TypeError, ValueError):
            raise ValueError("Response content must be JSON-serializable.")
        return v

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "name": "get_weather",
                    "content": {
                        "temperature": 20,
                        "conditions": "sunny",
                        "humidity": 65,
                    },
                }
            ]
        },
    }
