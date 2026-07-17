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

from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage

from camel.agents import BaseChatAgent, ChatAgent
from camel.models import BaseModelBackend
from camel.types import ChatCompletion, ModelType


class _DummyTokenCounter:
    def count_tokens_from_messages(self, messages):
        return len(messages)


class _CapturingModel(BaseModelBackend):
    def __init__(self):
        super().__init__(
            model_type=ModelType.GPT_4O_MINI,
            token_counter=_DummyTokenCounter(),
        )
        self.last_messages = None

    @property
    def token_counter(self):
        return self._token_counter

    def run(self, messages, response_format=None, tools=None):
        self.last_messages = messages
        return ChatCompletion(
            id="test-id",
            model="gpt-4o-mini",
            object="chat.completion",
            created=0,
            choices=[
                Choice(
                    index=0,
                    finish_reason="stop",
                    message=ChatCompletionMessage(
                        role="assistant",
                        content="done",
                    ),
                )
            ],
        )

    def _run(self, messages, response_format=None, tools=None):
        raise NotImplementedError

    async def _arun(self, messages, response_format=None, tools=None):
        raise NotImplementedError


def test_base_chat_agent_disables_context_management_by_default():
    model = _CapturingModel()
    agent = BaseChatAgent(model=model)

    assert model.context_management is False
    assert agent.summarize_threshold is None

    agent.step("Hello <think>keep-this</think>")
    assert model.last_messages is not None
    assert "<think>keep-this</think>" in model.last_messages[-1]["content"]


def test_chat_agent_keeps_context_management_enabled_by_default():
    model = _CapturingModel()
    agent = ChatAgent(model=model)

    assert model.context_management is True

    agent.step("Hello <think>remove-this</think>")
    assert model.last_messages is not None
    assert "<think>" not in model.last_messages[-1]["content"]
