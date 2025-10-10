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
# Copyright 2023-2024 @ CAMEL-AI.org
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for Camel chat abstractions."""

from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_function_tool_call import (
    Function as ChatCompletionMessageFunctionToolCallFunction,
)
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)
from openai.types.completion_usage import CompletionUsage

from camel.core import CamelMessage, CamelModelResponse, CamelUsage


def _build_chat_completion(tool_arguments: str = "{}") -> ChatCompletion:
    tool_call = ChatCompletionMessageToolCall(
        id="tool-1",
        type="function",
        function=ChatCompletionMessageFunctionToolCallFunction(
            name="demo_tool",
            arguments=tool_arguments,
        ),
    )
    message = ChatCompletionMessage(
        role="assistant",
        content="answer",
        tool_calls=[tool_call],
    )
    choice = Choice(
        finish_reason="stop",
        index=0,
        message=message,
        logprobs=None,
    )
    return ChatCompletion.construct(  # type: ignore[misc]
        id="resp-1",
        choices=[choice],
        usage=CompletionUsage.construct(  # type: ignore[misc]
            prompt_tokens=5,
            completion_tokens=7,
            total_tokens=12,
        ),
    )


def test_camel_message_from_chat_completion():
    completion = _build_chat_completion()
    message = CamelMessage.from_chat_completion(completion.choices[0].message)
    assert message.role == "assistant"
    assert message.content == "answer"
    assert message.tool_calls and message.tool_calls[0].name == "demo_tool"


def test_camel_model_response_from_chat_completion():
    completion = _build_chat_completion()
    camel_response = CamelModelResponse.from_chat_completion(completion)
    assert camel_response.response_id == "resp-1"
    assert camel_response.finish_reasons == ["stop"]
    assert len(camel_response.messages) == 1
    usage = camel_response.usage
    assert usage and usage.total_tokens == 12


def test_camel_usage_from_chat_completion_none():
    usage = CamelUsage.from_chat_completion(None)
    assert usage is None
