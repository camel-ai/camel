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

    system: Optional[str] = None
    tools: Optional[str] = None
    conversations: List[ShareGPTMessage]

    model_config = {
        "extra": "forbid"  # Ensures no unexpected fields are allowed
    }


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
            json.dumps(v)
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
            json.dumps(v)
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
