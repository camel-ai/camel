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
"""Tests for ModelResponse composition pattern."""

from camel.agents._types import ModelResponse, ToolCallRequest
from camel.messages import BaseMessage
from camel.responses.model_response import (
    CamelModelResponse,
    CamelToolCall,
    CamelUsage,
)
from camel.types import RoleType


def _make_camel_response(
    *,
    content: str = "Hello",
    tool_calls: list[CamelToolCall] | None = None,
    input_tokens: int = 10,
    output_tokens: int = 5,
) -> CamelModelResponse:
    """Create a minimal CamelModelResponse for testing."""
    msg = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict={},
        content=content,
    )
    usage = CamelUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        raw={
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    )
    return CamelModelResponse(
        id="test-response-001",
        model="gpt-4o-mini",
        created=1730000000,
        output_messages=[msg],
        tool_call_requests=tool_calls,
        finish_reasons=["stop"],
        usage=usage,
        raw={"original": "payload"},
    )


def test_model_response_composition_basic():
    """Test basic composition pattern."""
    camel_resp = _make_camel_response(content="Test message")

    model_resp = ModelResponse(model_response=camel_resp)

    # Properties should delegate to internal CamelModelResponse
    assert model_resp.response_id == "test-response-001"
    assert len(model_resp.output_messages) == 1
    assert model_resp.output_messages[0].content == "Test message"
    assert model_resp.finish_reasons == ["stop"]


def test_model_response_usage_dict():
    """Test usage_dict property returns correct format."""
    camel_resp = _make_camel_response(input_tokens=100, output_tokens=50)

    model_resp = ModelResponse(model_response=camel_resp)

    usage = model_resp.usage_dict
    assert usage["prompt_tokens"] == 100
    assert usage["completion_tokens"] == 50
    assert usage["total_tokens"] == 150


def test_model_response_usage_dict_synthesized():
    """Test usage_dict synthesis when raw is missing."""
    msg = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict={},
        content="Test",
    )
    # Create usage without raw dict
    usage = CamelUsage(
        input_tokens=20,
        output_tokens=10,
        total_tokens=30,
        raw=None,  # No raw dict
    )
    camel_resp = CamelModelResponse(
        id="test-002",
        output_messages=[msg],
        finish_reasons=["stop"],
        usage=usage,
    )

    model_resp = ModelResponse(model_response=camel_resp)

    usage_dict = model_resp.usage_dict
    # Should synthesize with Chat Completions field names
    assert usage_dict["prompt_tokens"] == 20
    assert usage_dict["completion_tokens"] == 10
    assert usage_dict["total_tokens"] == 30


def test_model_response_tool_call_conversion():
    """Test CamelToolCall to ToolCallRequest conversion."""
    tool_calls = [
        CamelToolCall(id="call_1", name="search", args={"query": "test"}),
        CamelToolCall(id="call_2", name="fetch", args={"url": "http://x"}),
    ]
    camel_resp = _make_camel_response(tool_calls=tool_calls)

    model_resp = ModelResponse(model_response=camel_resp)

    requests = model_resp.tool_call_requests
    assert requests is not None
    assert len(requests) == 2

    # Check conversion from CamelToolCall to ToolCallRequest
    assert isinstance(requests[0], ToolCallRequest)
    assert requests[0].tool_call_id == "call_1"
    assert requests[0].tool_name == "search"
    assert requests[0].args == {"query": "test"}

    assert requests[1].tool_call_id == "call_2"
    assert requests[1].tool_name == "fetch"


def test_model_response_no_tool_calls():
    """Test tool_call_requests returns None when no tool calls."""
    camel_resp = _make_camel_response(tool_calls=None)

    model_resp = ModelResponse(model_response=camel_resp)

    assert model_resp.tool_call_requests is None


def test_model_response_raw_access():
    """Test raw response access for debugging."""
    camel_resp = _make_camel_response()

    model_resp = ModelResponse(model_response=camel_resp)

    assert model_resp.response == {"original": "payload"}


def test_model_response_get_model_response():
    """Test explicit access to underlying CamelModelResponse."""
    camel_resp = _make_camel_response()

    model_resp = ModelResponse(model_response=camel_resp)

    # get_model_response() provides explicit access
    internal = model_resp.get_model_response()
    assert internal is camel_resp
    assert internal.id == "test-response-001"


def test_model_response_agent_metadata():
    """Test agent-specific metadata fields."""
    camel_resp = _make_camel_response()

    model_resp = ModelResponse(
        model_response=camel_resp,
        session_id="session-123",
        agent_id="agent-456",
    )

    assert model_resp.session_id == "session-123"
    assert model_resp.agent_id == "agent-456"


def test_model_response_serialization_excludes_private():
    """Test that _model_response is excluded from serialization."""
    camel_resp = _make_camel_response()

    model_resp = ModelResponse(
        model_response=camel_resp,
        session_id="test-session",
    )

    # model_dump should not include _model_response
    dumped = model_resp.model_dump()
    assert "_model_response" not in dumped
    assert "model_response" not in dumped
    # Public fields should be present
    assert dumped["session_id"] == "test-session"
