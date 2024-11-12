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


class ToolCall(BaseModel):
    """Represents a single tool/function call with validation"""

    name: str = Field(
        min_length=1,
        max_length=256,
        description="The name of the tool to call",
    )
    arguments: Dict[str, Any] = Field(
        description="The arguments to pass to the tool"
    )

    @field_validator('arguments')
    @classmethod
    def validate_arguments(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate argument structure and content"""

        # Try to serialize arguments to ensure they're JSON-compatible
        try:
            json.dumps(v)
        except (TypeError, ValueError):
            raise ValueError("Arguments must be JSON-serializable")

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
