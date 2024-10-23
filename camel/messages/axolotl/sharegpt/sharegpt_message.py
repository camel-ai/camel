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
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ShareGPTMessage(BaseModel):
    """A single message in ShareGPT format with enhanced validation"""

    from_: Literal["human", "gpt", "system", "tool"] = Field(
        alias="from", description="The role of the message sender"
    )
    value: str = Field(
        min_length=1,
        max_length=100000,
        description="The content of the message",
    )

    @field_validator('value')
    @classmethod
    def validate_value_content(cls, v: str) -> str:
        """Validate message content isn't empty and contains printable characters"""
        if not v.strip():
            raise ValueError(
                "Message content cannot be empty or just whitespace"
            )
        if not any(c.isprintable() for c in v):
            raise ValueError(
                "Message must contain at least one printable character"
            )
        return v.strip()

    model_config = {
        "populate_by_name": True,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {"from": "human", "value": "What's the weather like today?"}
            ]
        },
    }
