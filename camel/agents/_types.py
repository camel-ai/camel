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
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from camel.core import CamelModelResponse
from camel.messages import BaseMessage


class ToolCallRequest(BaseModel):
    r"""The request for tool calling."""

    tool_name: str
    args: Dict[str, Any]
    tool_call_id: str


class ModelResponse(BaseModel):
    r"""The response from the model.

    ``response`` holds the provider-specific payload returned by the backend
    (for example a raw :class:`~openai.types.chat.ChatCompletion` or a stream
    manager). ``camel_response`` is an optional normalized
    :class:`CamelModelResponse` view derived from that payload so higher level
    code can work against CAMEL's vendor-neutral abstractions.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    response: Any
    tool_call_requests: Optional[List[ToolCallRequest]]
    output_messages: List[BaseMessage]
    finish_reasons: List[str]
    usage_dict: Dict[str, Any]
    response_id: str
    camel_response: Optional[CamelModelResponse] = None
