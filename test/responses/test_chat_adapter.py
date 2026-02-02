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

import json

from openai.types.chat.chat_completion import ChoiceLogprobs
from openai.types.chat.chat_completion_token_logprob import (
    ChatCompletionTokenLogprob,
    TopLogprob,
)

from camel.responses.adapters.chat_completions import (
    adapt_chat_to_camel_response,
)
from camel.types import ChatCompletion, ChatCompletionMessage
from camel.types.enums import RoleType


def _make_chat_completion(
    *, content: str, finish_reason: str = "stop"
) -> ChatCompletion:
    """Construct a minimal ChatCompletion using pydantic.construct.

    This avoids importing heavy client dependencies and mirrors how the
    codebase itself synthesizes ChatCompletion in adapters elsewhere.
    """
    choice = dict(
        index=0,
        message=ChatCompletionMessage.construct(
            role="assistant", content=content, tool_calls=None
        ),
        finish_reason=finish_reason,
    )
    return ChatCompletion.construct(
        id="chatcmpl-test-001",
        choices=[choice],
        created=1730000000,
        model="gpt-4o-mini",
        object="chat.completion",
        usage=None,
    )


def test_adapt_chat_to_camel_response_basic():
    cc = _make_chat_completion(content="Hello, world!", finish_reason="stop")
    cmr = adapt_chat_to_camel_response(cc)

    assert cmr.id == "chatcmpl-test-001"
    assert cmr.model == "gpt-4o-mini"
    assert cmr.finish_reasons == ["stop"]
    assert (
        cmr.output_messages
        and cmr.output_messages[0].content == "Hello, world!"
    )
    assert cmr.output_messages[0].role_type == RoleType.ASSISTANT
    # usage is optional in this minimal object
    assert cmr.usage is not None
    # raw holds the original object for debugging
    assert cmr.raw is cc


def test_adapt_tool_calls_if_present():
    # Build a ChatCompletion-like object with a function tool call
    tool_call = {
        "id": "call_1",
        "type": "function",
        "function": {"name": "search", "arguments": json.dumps({"q": "x"})},
    }

    choice = dict(
        index=0,
        message=ChatCompletionMessage.construct(
            role="assistant", content="", tool_calls=[tool_call]
        ),
        finish_reason="tool_calls",
    )

    cc = ChatCompletion.construct(
        id="chatcmpl-test-002",
        choices=[choice],
        created=1730000001,
        model="gpt-4o-mini",
        object="chat.completion",
        usage=None,
    )

    cmr = adapt_chat_to_camel_response(cc)
    assert cmr.finish_reasons == ["tool_calls"]
    assert (
        cmr.tool_call_requests is not None and len(cmr.tool_call_requests) == 1
    )
    tc = cmr.tool_call_requests[0]
    assert tc.id == "call_1" and tc.name == "search" and tc.args == {"q": "x"}


def test_adapt_chat_to_camel_response_preserves_logprobs():
    top_lp = TopLogprob.construct(token="Hi", bytes=None, logprob=-0.1)
    token_lp = ChatCompletionTokenLogprob.construct(
        token="Hi", bytes=None, logprob=-0.1, top_logprobs=[top_lp]
    )
    logprobs = ChoiceLogprobs.construct(content=[token_lp])

    choice = dict(
        index=0,
        message=ChatCompletionMessage.construct(
            role="assistant", content="Hi", tool_calls=None
        ),
        finish_reason="stop",
        logprobs=logprobs,
    )

    cc = ChatCompletion.construct(
        id="chatcmpl-test-003",
        choices=[choice],
        created=1730000002,
        model="gpt-4o-mini",
        object="chat.completion",
        usage=None,
    )

    cmr = adapt_chat_to_camel_response(cc)
    assert cmr.logprobs is not None
    assert cmr.logprobs[0].content[0].token == "Hi"
