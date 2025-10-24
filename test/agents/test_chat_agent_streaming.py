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
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from camel.agents.chat_agent import (
    ChatAgent,
    StreamContentAccumulator,
)
from camel.core import CamelModelResponse
from camel.messages import BaseMessage
from camel.models.stub_model import StubModel
from camel.types import ModelType, RoleType
from camel.types.agents import ToolCallingRecord


def _make_agent() -> ChatAgent:
    system_msg = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict=None,
        content="You are a helpful assistant.",
    )
    agent = ChatAgent(
        system_message=system_msg,
        model=StubModel(ModelType.STUB),
    )
    return agent


def test_streaming_partial_response_has_camel_payload() -> None:
    agent = _make_agent()
    accumulator = StreamContentAccumulator()
    usage = {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}

    response = agent._create_streaming_response_with_accumulator(
        accumulator=accumulator,
        new_content="Hello",
        step_token_usage=usage,
        response_id="resp-1",
        tool_call_records=None,
    )

    camel_response = response.info.get("camel_response")
    assert isinstance(camel_response, CamelModelResponse)
    assert camel_response.response_id == "resp-1"
    assert camel_response.finish_reasons == ["streaming"]
    assert camel_response.messages[0].content == "Hello"
    assert camel_response.usage and camel_response.usage.total_tokens == 3


def test_streaming_pending_tool_calls_reflected_in_camel_payload() -> None:
    agent = _make_agent()
    accumulator = StreamContentAccumulator()
    pending_tool_calls = {
        0: {
            "id": "call_123",
            "type": "function",
            "function": {"name": "add", "arguments": '{"x": 1, "y": 2}'},
            "complete": False,
        }
    }

    response = agent._create_streaming_response_with_accumulator(
        accumulator=accumulator,
        new_content="partial",
        step_token_usage={
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
        response_id="stream-1",
        tool_call_records=[],
        pending_tool_calls=pending_tool_calls,
    )

    camel_response = response.info["camel_response"]
    assert isinstance(camel_response, CamelModelResponse)
    tool_calls = list(camel_response.tool_calls)
    assert len(tool_calls) == 1
    assert tool_calls[0].name == "add"
    assert tool_calls[0].arguments == '{"x": 1, "y": 2}'
    assert tool_calls[0].id == "call_123"


def test_streaming_final_response_uses_camel_builder() -> None:
    agent = _make_agent()
    tool_record = ToolCallingRecord(
        tool_name="multiply",
        args={"x": 3, "y": 4},
        result=12,
        tool_call_id="tool-456",
    )

    camel_response = agent._build_camel_response_from_stream(
        content="Done.",
        finish_reasons=["stop"],
        usage_dict={
            "prompt_tokens": 5,
            "completion_tokens": 7,
            "total_tokens": 12,
        },
        tool_call_records=[tool_record],
        response_id="final-1",
    )

    assert camel_response.response_id == "final-1"
    assert camel_response.finish_reasons == ["stop"]
    assert camel_response.usage and camel_response.usage.total_tokens == 12
    tool_calls = list(camel_response.tool_calls)
    assert len(tool_calls) == 1
    assert tool_calls[0].name == "multiply"
    assert tool_calls[0].arguments == '{"x": 3, "y": 4}'


def test_streaming_error_response_has_camel_payload() -> None:
    agent = _make_agent()
    error = agent._create_error_response(
        "something went wrong",
        [
            ToolCallingRecord(
                tool_name="noop",
                args={},
                result=None,
                tool_call_id="noop-1",
            )
        ],
    )

    camel_response = error.info["camel_response"]
    assert isinstance(camel_response, CamelModelResponse)
    assert camel_response.finish_reasons == ["error"]
    assert camel_response.messages[0].content.startswith("Error:")
