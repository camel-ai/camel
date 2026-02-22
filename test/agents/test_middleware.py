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

from camel.agents import ChatAgent
from camel.agents._middleware import (
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


def test_multiple_middlewares_execute_in_order():
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

    response = agent.step("Hello!")
    assert response.msg.content == "Base [M1] [M2]"


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
