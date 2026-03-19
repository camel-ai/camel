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
from copy import deepcopy
from typing import List, Optional
from unittest.mock import MagicMock

import pytest
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage

from camel.agents import (
    ChatAgent,
    MessageMiddleware,
    MiddlewareContext,
    MiddlewareError,
)
from camel.messages import OpenAIMessage
from camel.models import ModelFactory
from camel.types import (
    ChatCompletion,
    ModelPlatformType,
    ModelType,
)


def _make_model():
    return ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.DEFAULT,
    )


def _make_mock_response(content: str = "Mock response.") -> ChatCompletion:
    return ChatCompletion(
        id="mock_id",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                logprobs=None,
                message=ChatCompletionMessage(
                    content=content,
                    role="assistant",
                ),
            )
        ],
        created=123456789,
        model="gpt-4o",
        object="chat.completion",
        usage=CompletionUsage(
            completion_tokens=10,
            prompt_tokens=5,
            total_tokens=15,
        ),
    )


class InjectContextMiddleware(MessageMiddleware):
    """Prepends a system message with user context."""

    def __init__(self, context_text: str):
        self.context_text = context_text
        self.last_context: Optional[MiddlewareContext] = None

    def process_request(
        self,
        messages: List[OpenAIMessage],
        context: MiddlewareContext,
    ) -> List[OpenAIMessage]:
        self.last_context = context
        injected: OpenAIMessage = {
            "role": "system",
            "content": self.context_text,
        }
        return [injected, *list(messages)]


class ResponseModifierMiddleware(MessageMiddleware):
    """Appends a suffix to the response content."""

    def __init__(self, suffix: str):
        self.suffix = suffix

    def process_response(
        self,
        response: ChatCompletion,
        context: MiddlewareContext,
    ) -> ChatCompletion:
        modified = deepcopy(response)
        for choice in modified.choices:
            if choice.message.content:
                choice.message.content += self.suffix
        return modified


def test_request_middleware_injects_message_and_receives_context():
    model = _make_model()
    mock_response = _make_mock_response()
    model.run = MagicMock(return_value=mock_response)

    middleware = InjectContextMiddleware("User: Alice, Dept: Engineering")
    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[middleware],
    )

    response = agent.step("Hello!")
    assert response.msgs is not None
    assert len(response.msgs) > 0

    # Verify the model was called with the injected message
    messages_sent = model.run.call_args[0][0]
    assert any(
        msg.get("content") == "User: Alice, Dept: Engineering"
        for msg in messages_sent
    )

    # Verify context was correctly populated
    ctx = middleware.last_context
    assert isinstance(ctx, MiddlewareContext)
    assert ctx.agent_id == agent.agent_id
    assert ctx.iteration == 0


def test_response_middleware_modifies_content():
    model = _make_model()
    model.run = MagicMock(return_value=_make_mock_response("Original"))

    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[ResponseModifierMiddleware(" [REVIEWED]")],
    )

    response = agent.step("Hello!")
    assert response.msg.content == "Original [REVIEWED]"


def test_multiple_response_middlewares_execute_in_reverse_order():
    model = _make_model()
    model.run = MagicMock(return_value=_make_mock_response("Base"))

    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[
            ResponseModifierMiddleware(" [M1]"),
            ResponseModifierMiddleware(" [M2]"),
        ],
    )

    # Response middlewares run in reverse (onion/LIFO): M2 first, then M1
    response = agent.step("Hello!")
    assert response.msg.content == "Base [M2] [M1]"


@pytest.mark.asyncio
async def test_middleware_async_path():
    model = _make_model()
    mock_response = _make_mock_response("Async response")

    async def mock_arun(*args, **kwargs):
        return mock_response

    model.arun = mock_arun

    modifier = ResponseModifierMiddleware(" [ASYNC]")
    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[modifier],
    )

    response = await agent.astep("Hello!")
    assert response.msg.content == "Async response [ASYNC]"


class AsyncInjectMiddleware(MessageMiddleware):
    """Async middleware that injects a system message."""

    def __init__(self, context_text: str):
        self.context_text = context_text

    async def async_process_request(
        self,
        messages: List[OpenAIMessage],
        context: MiddlewareContext,
    ) -> List[OpenAIMessage]:
        injected: OpenAIMessage = {
            "role": "system",
            "content": self.context_text,
        }
        return [injected, *list(messages)]


class AsyncResponseModifierMiddleware(MessageMiddleware):
    """Async middleware that appends a suffix to response content."""

    def __init__(self, suffix: str):
        self.suffix = suffix

    async def async_process_response(
        self,
        response: ChatCompletion,
        context: MiddlewareContext,
    ) -> ChatCompletion:
        modified = deepcopy(response)
        for choice in modified.choices:
            if choice.message.content:
                choice.message.content += self.suffix
        return modified


@pytest.mark.asyncio
async def test_async_middleware_request():
    model = _make_model()
    mock_response = _make_mock_response("Hello")

    async def mock_arun(*args, **kwargs):
        return mock_response

    model.arun = mock_arun

    middleware = AsyncInjectMiddleware("Async injected context")
    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[middleware],
    )

    response = await agent.astep("Hello!")
    assert response.msgs is not None
    assert len(response.msgs) > 0


@pytest.mark.asyncio
async def test_async_middleware_response():
    model = _make_model()
    mock_response = _make_mock_response("Original")

    async def mock_arun(*args, **kwargs):
        return mock_response

    model.arun = mock_arun

    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[AsyncResponseModifierMiddleware(" [ASYNC_MOD]")],
    )

    response = await agent.astep("Hello!")
    assert response.msg.content == "Original [ASYNC_MOD]"


@pytest.mark.asyncio
async def test_async_middleware_fallback_to_sync():
    """Sync-only middleware should still work in the async path
    via the default fallback."""
    model = _make_model()
    mock_response = _make_mock_response("Base")

    async def mock_arun(*args, **kwargs):
        return mock_response

    model.arun = mock_arun

    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[ResponseModifierMiddleware(" [SYNC_FALLBACK]")],
    )

    response = await agent.astep("Hello!")
    assert response.msg.content == "Base [SYNC_FALLBACK]"


@pytest.mark.asyncio
async def test_async_middleware_error_wrapping():
    class AsyncFailingMiddleware(MessageMiddleware):
        async def async_process_request(self, messages, context):
            raise ValueError("async boom")

    model = _make_model()

    async def mock_arun(*args, **kwargs):
        return _make_mock_response()

    model.arun = mock_arun

    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[AsyncFailingMiddleware()],
    )

    with pytest.raises(MiddlewareError) as exc_info:
        await agent.astep("Hello!")

    err = exc_info.value
    assert err.middleware_name == "AsyncFailingMiddleware"
    assert err.phase == "async_process_request"
    assert "async boom" in str(err)


# --------------- Streaming path tests ---------------


def _make_stream_model():
    """Create a model with stream=True in config."""
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.DEFAULT,
    )
    model.model_config_dict["stream"] = True
    return model


def test_stream_request_middleware_applied():
    """Request middleware should be applied in the sync streaming path."""
    model = _make_stream_model()
    mock_response = _make_mock_response("Streamed")
    # Backend returns a complete ChatCompletion (non-stream fallback)
    model.run = MagicMock(return_value=mock_response)

    middleware = InjectContextMiddleware("stream-injected")
    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[middleware],
    )

    streaming_resp = agent.step("Hello!")
    # Consume the streaming response to trigger execution
    final = streaming_resp.msg

    # Verify request middleware was invoked
    messages_sent = model.run.call_args[0][0]
    assert any(
        msg.get("content") == "stream-injected" for msg in messages_sent
    )
    assert final is not None

    # Verify context iteration starts at 0
    assert middleware.last_context is not None
    assert middleware.last_context.iteration == 0


def test_stream_response_middleware_applied_on_non_stream_fallback():
    """When backend ignores stream=True and returns a complete
    ChatCompletion, response middleware should still be applied."""
    model = _make_stream_model()
    mock_response = _make_mock_response("Fallback")
    model.run = MagicMock(return_value=mock_response)

    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[ResponseModifierMiddleware(" [STREAM_RESP]")],
    )

    streaming_resp = agent.step("Hello!")
    assert streaming_resp.msg.content == "Fallback [STREAM_RESP]"


def test_stream_request_middleware_context_has_correct_iteration():
    """MiddlewareContext.iteration should reflect the current iteration
    count within the streaming loop."""
    model = _make_stream_model()
    mock_response = _make_mock_response("OK")
    model.run = MagicMock(return_value=mock_response)

    middleware = InjectContextMiddleware("ctx-check")
    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[middleware],
    )

    streaming_resp = agent.step("Hello!")
    _ = streaming_resp.msg

    assert middleware.last_context is not None
    assert middleware.last_context.iteration == 0


@pytest.mark.asyncio
async def test_astream_request_middleware_applied():
    """Request middleware should be applied in the async streaming path."""
    model = _make_stream_model()
    mock_response = _make_mock_response("Async streamed")

    async def mock_arun(*args, **kwargs):
        return mock_response

    model.arun = mock_arun

    middleware = InjectContextMiddleware("async-stream-injected")
    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[middleware],
    )

    # AsyncStreamingChatAgentResponse is awaitable to get final response
    final = await (await agent.astep("Hello!"))

    assert final.msg is not None
    assert middleware.last_context is not None
    assert middleware.last_context.iteration == 0


@pytest.mark.asyncio
async def test_astream_response_middleware_applied_on_non_stream_fallback():
    """When backend ignores stream=True and returns a complete
    ChatCompletion in async path, response middleware should be applied."""
    model = _make_stream_model()
    mock_response = _make_mock_response("Async fallback")

    async def mock_arun(*args, **kwargs):
        return mock_response

    model.arun = mock_arun

    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[ResponseModifierMiddleware(" [ASTREAM_RESP]")],
    )

    final = await (await agent.astep("Hello!"))
    assert final.msg.content == "Async fallback [ASTREAM_RESP]"


# --------------- Ordering / edge case tests ---------------


def test_multiple_request_middlewares_execute_in_forward_order():
    """Request middlewares should execute in registration order."""
    model = _make_model()
    model.run = MagicMock(return_value=_make_mock_response())

    call_order: List[str] = []

    class OrderTracker(MessageMiddleware):
        def __init__(self, name: str):
            self.name = name

        def process_request(self, messages, context):
            call_order.append(self.name)
            return messages

    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[OrderTracker("A"), OrderTracker("B"), OrderTracker("C")],
    )

    agent.step("Hello!")
    assert call_order == ["A", "B", "C"]


def test_no_middlewares():
    """Agent with no middlewares should work normally."""
    model = _make_model()
    model.run = MagicMock(return_value=_make_mock_response("No middleware"))

    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[],
    )

    response = agent.step("Hello!")
    assert response.msg.content == "No middleware"


def test_clone_preserves_middlewares():
    """Cloned agent should retain the same middleware instances."""
    model = _make_model()
    model.run = MagicMock(return_value=_make_mock_response("Cloned"))

    middleware = ResponseModifierMiddleware(" [CLONED]")
    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[middleware],
    )

    cloned = agent.clone()
    cloned.model_backend.models[0].run = MagicMock(
        return_value=_make_mock_response("Cloned")
    )

    response = cloned.step("Hello!")
    assert response.msg.content == "Cloned [CLONED]"


# --------------- Error wrapping tests ---------------


@pytest.mark.parametrize(
    "phase",
    ["process_request", "process_response"],
)
def test_middleware_error_wrapping(phase):
    class FailingMiddleware(MessageMiddleware):
        def process_request(self, messages, context):
            if phase == "process_request":
                raise ValueError("boom")
            return messages

        def process_response(self, response, context):
            if phase == "process_response":
                raise RuntimeError("boom")
            return response

    model = _make_model()
    model.run = MagicMock(return_value=_make_mock_response())

    agent = ChatAgent(
        system_message="You are helpful.",
        model=model,
        middlewares=[FailingMiddleware()],
    )

    with pytest.raises(MiddlewareError) as exc_info:
        agent.step("Hello!")

    err = exc_info.value
    assert err.middleware_name == "FailingMiddleware"
    assert err.phase == phase
    assert "boom" in str(err)
