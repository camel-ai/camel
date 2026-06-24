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
r"""Tests for excluding the last user message from context summarization
(see issue #3371)."""

import pytest

from camel.agents import ChatAgent
from camel.models import BaseModelBackend
from camel.types import ModelType


class _DummyModel(BaseModelBackend):
    r"""Offline model stub so a ChatAgent can be built without API calls.

    ``_build_conversation_text_from_messages`` never invokes the model, so the
    run methods are intentionally not implemented.
    """

    @property
    def token_counter(self):
        return self._token_counter

    def _run(self, messages, response_format=None, tools=None):
        raise NotImplementedError

    async def _arun(self, messages, response_format=None, tools=None):
        raise NotImplementedError


@pytest.fixture
def agent() -> ChatAgent:
    return ChatAgent(model=_DummyModel(ModelType.GPT_4O_MINI))


def _conversation():
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "First question about apples."},
        {"role": "assistant", "content": "Here is the answer about apples."},
        {"role": "user", "content": "Second question about bananas."},
    ]


def test_includes_last_user_message_by_default(agent: ChatAgent):
    text, user_messages = agent._build_conversation_text_from_messages(
        _conversation()
    )
    assert "Second question about bananas." in text
    assert user_messages == [
        "First question about apples.",
        "Second question about bananas.",
    ]


def test_excludes_only_the_last_user_message(agent: ChatAgent):
    text, user_messages = agent._build_conversation_text_from_messages(
        _conversation(), exclude_last_user_message=True
    )
    # The most recent user message is dropped...
    assert "Second question about bananas." not in text
    # ...while earlier context is preserved.
    assert "First question about apples." in text
    assert "Here is the answer about apples." in text
    assert user_messages == ["First question about apples."]


def test_exclusion_is_noop_without_user_messages(agent: ChatAgent):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "assistant", "content": "Nothing to respond to yet."},
    ]
    with_flag, _ = agent._build_conversation_text_from_messages(
        messages, exclude_last_user_message=True
    )
    without_flag, _ = agent._build_conversation_text_from_messages(messages)
    assert with_flag == without_flag
    assert "Nothing to respond to yet." in with_flag


def test_excludes_last_user_message_even_when_not_final(agent: ChatAgent):
    # The last *user* message is not necessarily the final message; messages
    # produced after it (assistant/tool) must be retained.
    messages = [
        {"role": "system", "content": "System."},
        {"role": "user", "content": "Earlier user turn."},
        {"role": "user", "content": "Latest user turn."},
        {"role": "assistant", "content": "Assistant reply after user."},
    ]
    text, user_messages = agent._build_conversation_text_from_messages(
        messages, exclude_last_user_message=True
    )
    assert "Latest user turn." not in text
    assert "Earlier user turn." in text
    assert "Assistant reply after user." in text
    assert user_messages == ["Earlier user turn."]


def test_empty_string_user_content_is_not_treated_as_last(agent: ChatAgent):
    # A trailing empty user message must not be chosen as the one to exclude;
    # the real last user message should be dropped instead.
    messages = [
        {"role": "user", "content": "Real instruction."},
        {"role": "user", "content": ""},
    ]
    text, user_messages = agent._build_conversation_text_from_messages(
        messages, exclude_last_user_message=True
    )
    assert "Real instruction." not in text
    assert user_messages == []
