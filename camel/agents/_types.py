# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, PrivateAttr

from camel.messages import BaseMessage
from camel.responses.model_response import CamelModelResponse


class ToolCallRequest(BaseModel):
    r"""The request for tool calling."""

    tool_name: str
    args: Dict[str, Any]
    tool_call_id: str
    extra_content: Optional[Dict[str, Any]] = None


class ModelResponse(BaseModel):
    r"""Agent-facing response wrapper using composition pattern.

    This class wraps a CamelModelResponse (from the adapter layer) and exposes
    only the fields needed by the agent layer. The internal CamelModelResponse
    is stored as a private attribute to maintain clear separation between
    adapter and agent concerns.

    The composition pattern ensures:
    - Provider-specific fields don't leak into agent code
    - Adapters don't need to populate agent-specific metadata
    - Single source of truth for model response data

    Attributes:
        session_id: Optional session identifier for agent tracking.
        agent_id: Optional agent identifier.

    Properties:
        response_id: Unique identifier for this response.
        output_messages: List of messages from the model.
        finish_reasons: List of finish reasons for each choice.
        tool_call_requests: Optional list of tool call requests.
        usage_dict: Token usage statistics as a dictionary.
        response: Raw provider response (for debugging/compatibility).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Private: the underlying CamelModelResponse from adapters
    _model_response: CamelModelResponse = PrivateAttr()

    # Public: Agent-specific metadata (can be extended)
    session_id: Optional[str] = None
    agent_id: Optional[str] = None

    def __init__(
        self,
        model_response: CamelModelResponse,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        **data: Any,
    ) -> None:
        """Initialize ModelResponse with a CamelModelResponse.

        Args:
            model_response: The underlying response from the adapter layer.
            session_id: Optional session identifier for agent tracking.
            agent_id: Optional agent identifier.
            **data: Additional data (for forward compatibility).
        """
        super().__init__(session_id=session_id, agent_id=agent_id, **data)
        self._model_response = model_response

    @property
    def response_id(self) -> str:
        """Unique identifier for this response."""
        return self._model_response.id

    @property
    def output_messages(self) -> List[BaseMessage]:
        """List of output messages from the model."""
        return self._model_response.output_messages

    @property
    def finish_reasons(self) -> List[str]:
        """List of finish reasons for each choice."""
        return self._model_response.finish_reasons

    @property
    def tool_call_requests(self) -> Optional[List[ToolCallRequest]]:
        """Optional list of tool call requests from the model.

        Converts CamelToolCall objects to ToolCallRequest for agent use.
        """
        tool_calls = self._model_response.tool_call_requests
        if not tool_calls:
            return None
        return [
            ToolCallRequest(
                tool_name=tc.name,
                args=tc.args,
                tool_call_id=tc.id,
            )
            for tc in tool_calls
        ]

    @property
    def usage_dict(self) -> Dict[str, Any]:
        """Token usage statistics as a dictionary.

        Returns the raw usage dict if available, otherwise synthesizes
        from normalized fields using Chat Completions field names for
        backward compatibility.
        """
        usage = self._model_response.usage
        if usage.raw:
            return dict(usage.raw)
        # Synthesize with Chat Completions field names for compatibility
        return {
            "prompt_tokens": usage.input_tokens or 0,
            "completion_tokens": usage.output_tokens or 0,
            "total_tokens": usage.total_tokens or 0,
        }

    @property
    def response(self) -> Any:
        """Raw provider response (for debugging/compatibility).

        Note: Direct access to the raw response is discouraged.
        Use specific properties like output_messages instead.
        """
        return self._model_response.raw

    def get_model_response(self) -> CamelModelResponse:
        """Get the underlying CamelModelResponse.

        This method provides explicit access to the internal response
        for advanced use cases. Prefer using the public properties
        for normal operations.

        Returns:
            The underlying CamelModelResponse object.
        """
        return self._model_response
