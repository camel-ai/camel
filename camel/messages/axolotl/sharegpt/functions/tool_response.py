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


import json
from typing import Any, Dict

from pydantic import BaseModel, Field, field_validator


class ToolResponse(BaseModel):
    """Represents a tool/function response with validation"""

    name: str = Field(
        min_length=1,
        max_length=256,
        pattern=r'^[a-zA-Z_][a-zA-Z0-9_]*$',
        description="The name of the tool that was called",
    )
    content: Dict[str, Any] = Field(
        description="The response content from the tool"
    )

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate response content structure"""
        if not v:
            raise ValueError("Response content cannot be empty")

        # Ensure content is JSON-serializable
        try:
            json.dumps(v)
        except (TypeError, ValueError):
            raise ValueError("Response content must be JSON-serializable")

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
