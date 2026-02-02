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

import os
from contextlib import contextmanager

from camel.models.openai_model import OpenAIModel
from camel.responses.model_response import CamelModelResponse
from camel.types import ChatCompletion, ChatCompletionMessage, ModelType


@contextmanager
def env(var: str, value: str):
    old = os.environ.get(var)
    os.environ[var] = value
    try:
        yield
    finally:
        if old is None:
            del os.environ[var]
        else:
            os.environ[var] = old


def _fake_chat_completion(text: str = "ok") -> ChatCompletion:
    choice = dict(
        index=0,
        message=ChatCompletionMessage.construct(
            role="assistant", content=text
        ),
        finish_reason="stop",
    )
    return ChatCompletion.construct(
        id="chatcmpl-flag-001",
        choices=[choice],
        created=1730000100,
        model="gpt-4o-mini",
        object="chat.completion",
        usage=None,
    )


def test_openai_model_returns_camel_when_flag_on(monkeypatch):
    # Satisfy constructor API key check
    with (
        env("OPENAI_API_KEY", "test"),
        env("CAMEL_USE_CAMEL_RESPONSE", "true"),
    ):
        model = OpenAIModel(ModelType.GPT_4O_MINI)

        # Avoid network: stub internal request method
        monkeypatch.setattr(
            model,
            "_request_chat_completion",
            lambda messages, tools=None: _fake_chat_completion("hello"),
        )

        resp = model.run([{"role": "user", "content": "hi"}])
        assert isinstance(resp, CamelModelResponse)
        assert resp.id == "chatcmpl-flag-001"
        assert (
            resp.output_messages and resp.output_messages[0].content == "hello"
        )


def test_openai_model_returns_chat_when_flag_off(monkeypatch):
    with (
        env("OPENAI_API_KEY", "test"),
        env("CAMEL_USE_CAMEL_RESPONSE", "false"),
    ):
        model = OpenAIModel(ModelType.GPT_4O_MINI)
        monkeypatch.setattr(
            model,
            "_request_chat_completion",
            lambda messages, tools=None: _fake_chat_completion("hello"),
        )

        resp = model.run([{"role": "user", "content": "hi"}])
        assert isinstance(resp, ChatCompletion)
        assert resp.choices[0].message.content == "hello"
