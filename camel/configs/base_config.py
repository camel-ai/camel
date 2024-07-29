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
from __future__ import annotations

from abc import ABC
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict

from camel.toolkits import OpenAIFunction


class BaseConfig(ABC, BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        frozen=True,
        # UserWarning: conflict with protected namespace "model_"
        protected_namespaces=(),
    )

    tools: Optional[List['OpenAIFunction']] = None
    """A list of tools the model may
    call. Currently, only functions are supported as a tool. Use this
    to provide a list of functions the model may generate JSON inputs
    for. A max of 128 functions are supported.
    """

    def as_dict(self) -> dict[str, Any]:
        config_dict = self.model_dump()
        if self.tools:
            config_dict["tools"] = [
                tool.get_openai_tool_schema() for tool in self.tools
            ]
        return config_dict
