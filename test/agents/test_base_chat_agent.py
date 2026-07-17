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
import asyncio
import time
from typing import Any, ClassVar, Dict, List, Optional, Type

import pytest
from openai.types.chat import ChatCompletionMessageFunctionToolCall
from openai.types.chat.chat_completion_message_function_tool_call import (
    Function,
)
from pydantic import BaseModel

from camel.agents.base import BaseAgent
from camel.agents.base_chat_agent import BaseChatAgent, TerminationReason
from camel.agents.chat_agent import ChatAgent
from camel.memories import AgentMemory
from camel.messages import OpenAIMessage
from camel.models.stub_model import StubModel
from camel.types import (
    ChatCompletion,
    ChatCompletionMessage,
    Choice,
    CompletionUsage,
    ModelType,
)


class SequencedModel(StubModel):
    def __init__(self, responses: List[ChatCompletion]):
        super().__init__(ModelType.STUB)
        self.responses = responses
        self.received: List[List[OpenAIMessage]] = []

    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        self.received.append([dict(message) for message in messages])
        return self.responses.pop(0)


def completion(content=None, tool_calls=None):
    return ChatCompletion(
        id="test-id",
        model="test-model",
        object="chat.completion",
        created=int(time.time()),
        choices=[
            Choice(
                index=0,
                finish_reason="tool_calls" if tool_calls else "stop",
                message=ChatCompletionMessage(
                    role="assistant",
                    content=content,
                    tool_calls=tool_calls,
                ),
            )
        ],
        usage=CompletionUsage(
            prompt_tokens=4, completion_tokens=2, total_tokens=6
        ),
    )


@pytest.mark.asyncio
async def test_append_only_agent_executes_tool_with_unprocessed_memory():
    def add(a: int, b: int) -> int:
        return a + b

    tool_call = ChatCompletionMessageFunctionToolCall(
        id="call-1",
        type="function",
        function=Function(name="add", arguments='{"a": 2, "b": 3}'),
    )
    backend = SequencedModel(
        [completion(tool_calls=[tool_call]), completion(content="five")]
    )
    agent = BaseChatAgent(
        system_message="Be concise.",
        model=backend,
        tools=[add],
        token_limit=100,
        step_timeout=None,
    )

    response = await agent.astep("calculate")

    assert isinstance(agent, BaseAgent)
    assert not isinstance(agent, ChatAgent)
    assert isinstance(agent.memory, AgentMemory)
    assert response.msgs[0].content == "five"
    assert [message["role"] for message in agent.message_list] == [
        "system",
        "user",
        "assistant",
        "tool",
        "assistant",
    ]
    assert agent.message_list[3] == {
        "role": "tool",
        "tool_call_id": "call-1",
        "content": "5",
    }
    assert [message["role"] for message in backend.received[1]] == [
        "system",
        "user",
        "assistant",
        "tool",
    ]
    memory_messages, _ = agent.memory.get_context()
    assert memory_messages == agent.message_list
    assert agent.termination_reason is TerminationReason.TASK_COMPLETE
    assert response.info["training"]["total_tool_calls"] == 1


@pytest.mark.asyncio
async def test_user_turns_append_and_reset_clears_trajectory():
    backend = SequencedModel(
        [completion(content="one"), completion(content="two")]
    )
    agent = BaseChatAgent(model=backend, token_limit=100, step_timeout=None)

    await agent.astep("first")
    await agent.astep("second")
    assert [message["role"] for message in agent.message_list] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]

    agent.reset()
    assert agent.message_list == []
    assert agent.memory.retrieve() == []
    assert agent.termination_reason is TerminationReason.NOT_TERMINATED


def test_error_reason_walks_wrapped_causes():
    try:
        try:
            raise asyncio.TimeoutError("server stalled")
        except asyncio.TimeoutError as cause:
            raise RuntimeError("model failed") from cause
    except RuntimeError as error:
        assert TerminationReason.from_error(error) is TerminationReason.TIMEOUT

    class ModelConnectionError(Exception):
        pass

    assert (
        TerminationReason.from_error(ModelConnectionError())
        is TerminationReason.CONNECTION_ERROR
    )


def test_error_reason_detects_openai_context_overflow_payload():
    class OpenAIStyleBadRequestError(Exception):
        code = "context_length_exceeded"
        type = "invalid_request_error"
        body: ClassVar[Dict[str, str]] = {
            "message": "This model's maximum context length is 32768 tokens.",
            "code": "context_length_exceeded",
        }

    assert (
        TerminationReason.from_error(OpenAIStyleBadRequestError())
        is TerminationReason.CONTEXT_WINDOW_OVERFLOW
    )


def test_error_reason_detects_http_response_context_overflow():
    class Response:
        status_code = 400
        text = "The input is longer than the model's context length."

        def json(self):
            return {
                "error": {
                    "message": (
                        "Requested token count exceeds the model's maximum "
                        "context length"
                    )
                }
            }

    class HTTPStatusError(Exception):
        response = Response()

    try:
        raise RuntimeError("model request failed") from HTTPStatusError()
    except RuntimeError as error:
        assert (
            TerminationReason.from_error(error)
            is TerminationReason.CONTEXT_WINDOW_OVERFLOW
        )


def test_error_reason_does_not_treat_all_bad_requests_as_context_overflow():
    class Response:
        status_code = 400
        text = "The input JSON is invalid."

        def json(self):
            return {
                "error": {
                    "message": "The input JSON is invalid.",
                    "type": "BadRequestError",
                    "code": 400,
                }
            }

    class HTTPStatusError(Exception):
        response = Response()

    assert (
        TerminationReason.from_error(HTTPStatusError())
        is TerminationReason.UNCLASSIFIED_ERROR
    )


@pytest.mark.asyncio
async def test_multiple_tool_calls_execute_sequentially_without_a_cap():
    active = 0
    max_active = 0
    events = []

    async def echo(value: int) -> int:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        events.append(("start", value))
        await asyncio.sleep(0)
        events.append(("end", value))
        active -= 1
        return value

    calls = [
        ChatCompletionMessageFunctionToolCall(
            id=f"call-{i}",
            type="function",
            function=Function(name="echo", arguments=f'{{"value": {i}}}'),
        )
        for i in range(2)
    ]
    backend = SequencedModel(
        [completion(tool_calls=calls), completion(content="done")]
    )
    agent = BaseChatAgent(
        model=backend,
        tools=[echo],
        token_limit=100,
        step_timeout=None,
    )

    result = await agent.astep("call tools")

    assert [record.result for record in result.info["tool_calls"]] == [0, 1]
    assert max_active == 1
    assert events == [("start", 0), ("end", 0), ("start", 1), ("end", 1)]
    assert not hasattr(agent, "parallel_internal_tools")
    assert agent.meta_info_record["max_tool_calls_per_turn"] == 2
    assert agent.meta_info_record["total_tool_calls"] == 2
    assert agent.termination_reason is TerminationReason.TASK_COMPLETE


@pytest.mark.asyncio
async def test_length_finish_reason_tracks_output_token_limit():
    response = completion(content="truncated")
    response.choices[0].finish_reason = "length"
    agent = BaseChatAgent(
        model=SequencedModel([response]),
        token_limit=100,
        step_timeout=None,
    )

    result = await agent.astep("write")

    assert result.terminated
    assert agent.termination_reason is TerminationReason.MAX_TOKENS_REACHED


@pytest.mark.asyncio
async def test_prompt_over_token_limit_tracks_context_overflow():
    agent = BaseChatAgent(
        model=SequencedModel([completion(content="answer")]),
        token_limit=3,
        step_timeout=None,
    )

    result = await agent.astep("write")

    assert result.terminated
    assert (
        agent.termination_reason is TerminationReason.CONTEXT_WINDOW_OVERFLOW
    )


@pytest.mark.asyncio
async def test_mcp_async_call_path_is_preserved():
    class MCPCallable:
        async def async_call(self, value: str):
            return f"mcp:{value}"

    class MCPFunctionTool:
        func = MCPCallable()

        def get_openai_tool_schema(self):
            return {
                "type": "function",
                "function": {"name": "mcp_echo", "parameters": {}},
            }

    tool_call = ChatCompletionMessageFunctionToolCall(
        id="mcp-call",
        type="function",
        function=Function(name="mcp_echo", arguments='{"value": "hello"}'),
    )
    backend = SequencedModel(
        [completion(tool_calls=[tool_call]), completion(content="done")]
    )
    agent = BaseChatAgent(model=backend, token_limit=100, step_timeout=None)
    agent._internal_tools["mcp_echo"] = MCPFunctionTool()

    result = await agent.astep("use MCP")

    assert result.info["tool_calls"][0].result == "mcp:hello"
    assert agent.message_list[-2]["content"] == "mcp:hello"


def test_sync_step_is_intentionally_unsupported():
    agent = BaseChatAgent(
        model=SequencedModel([completion(content="unused")]), token_limit=100
    )

    with pytest.raises(NotImplementedError, match="use astep"):
        agent.step("hello")


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
