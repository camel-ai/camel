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
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import camel.utils.langfuse as langfuse_utils


@pytest.fixture(autouse=True)
def reset_langfuse_state(monkeypatch):
    monkeypatch.setattr(langfuse_utils, '_langfuse_configured', False)
    monkeypatch.setattr(langfuse_utils, '_langfuse_client', None)
    monkeypatch.setattr(langfuse_utils, '_langfuse_v2_context', None)
    for key in (
        'LANGFUSE_PUBLIC_KEY',
        'LANGFUSE_SECRET_KEY',
        'LANGFUSE_BASE_URL',
        'LANGFUSE_HOST',
        'LANGFUSE_DEBUG',
        'LANGFUSE_ENABLED',
    ):
        monkeypatch.delenv(key, raising=False)


def configure(**kwargs):
    return langfuse_utils.configure_langfuse.__wrapped__(**kwargs)


def test_configure_v3_creates_client_with_explicit_settings(monkeypatch):
    client = MagicMock()
    constructor = MagicMock(return_value=client)
    monkeypatch.setattr(
        langfuse_utils,
        '_langfuse_sdk',
        SimpleNamespace(Langfuse=constructor, observe=MagicMock()),
    )

    configure(
        public_key='pk-test',
        secret_key='sk-test',
        host='https://langfuse.example.com',
        debug=True,
        enabled=True,
    )

    constructor.assert_called_once_with(
        public_key='pk-test',
        secret_key='sk-test',
        host='https://langfuse.example.com',
        debug=True,
        tracing_enabled=True,
    )
    assert langfuse_utils._langfuse_client is client
    assert langfuse_utils.is_langfuse_available()


def test_configure_v2_uses_legacy_context(monkeypatch):
    context = MagicMock()
    monkeypatch.setattr(langfuse_utils, '_langfuse_v2_context', context)
    monkeypatch.setattr(langfuse_utils, '_langfuse_sdk', SimpleNamespace())

    configure(
        public_key='pk-test',
        secret_key='sk-test',
        host='https://langfuse.example.com',
        enabled=True,
    )

    context.configure.assert_called_once_with(
        public_key='pk-test',
        secret_key='sk-test',
        host='https://langfuse.example.com',
        debug=False,
        enabled=True,
    )
    assert langfuse_utils.is_langfuse_available()


def test_configure_uses_base_url_and_rejects_missing_credentials(
    monkeypatch,
):
    constructor = MagicMock()
    monkeypatch.setattr(
        langfuse_utils,
        '_langfuse_sdk',
        SimpleNamespace(Langfuse=constructor),
    )
    monkeypatch.setenv('LANGFUSE_BASE_URL', 'https://us.example.com')

    configure(public_key='pk-test', enabled=True)

    constructor.assert_not_called()
    assert not langfuse_utils.is_langfuse_available()


def test_update_trace_uses_context_session_id(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(langfuse_utils, '_langfuse_client', client)
    monkeypatch.setattr(langfuse_utils, '_langfuse_configured', True)
    monkeypatch.setattr(
        langfuse_utils,
        '_langfuse_sdk',
        SimpleNamespace(Langfuse=MagicMock()),
    )
    langfuse_utils.set_current_agent_session_id('session-123')

    updated = langfuse_utils.update_langfuse_trace(
        user_id='user-7', metadata={'source': 'test'}, tags=['unit']
    )

    assert updated
    client.update_current_trace.assert_called_once_with(
        session_id='session-123',
        user_id='user-7',
        metadata={'source': 'test'},
        tags=['unit'],
    )


def test_v3_observation_normalizes_legacy_usage(monkeypatch):
    client = MagicMock()
    usage = SimpleNamespace(
        model_dump=lambda **kwargs: {
            'prompt_tokens': 12,
            'completion_tokens': 5,
            'total_tokens': 17,
            'ignored': None,
        }
    )
    monkeypatch.setattr(langfuse_utils, '_langfuse_client', client)
    monkeypatch.setattr(langfuse_utils, '_langfuse_configured', True)
    monkeypatch.setattr(
        langfuse_utils,
        '_langfuse_sdk',
        SimpleNamespace(Langfuse=MagicMock()),
    )

    langfuse_utils.update_current_observation(
        input={'messages': []}, model='model-x', usage=usage
    )

    client.update_current_generation.assert_called_once_with(
        input={'messages': []},
        output=None,
        model='model-x',
        model_parameters=None,
        usage_details={
            'prompt_tokens': 12,
            'completion_tokens': 5,
            'total_tokens': 17,
        },
    )


def test_v2_observation_preserves_legacy_usage(monkeypatch):
    context = MagicMock()
    usage = object()
    monkeypatch.setattr(langfuse_utils, '_langfuse_v2_context', context)
    monkeypatch.setattr(langfuse_utils, '_langfuse_configured', True)
    monkeypatch.setattr(langfuse_utils, '_langfuse_sdk', SimpleNamespace())

    langfuse_utils.update_current_observation(usage=usage)

    context.update_current_observation.assert_called_once_with(
        input=None,
        output=None,
        model=None,
        model_parameters=None,
        usage_details=None,
        usage=usage,
    )


def test_observe_resolves_native_decorator_after_configuration(monkeypatch):
    decorated_calls = []

    def sdk_observe(*args, **kwargs):
        def decorate(func):
            def wrapped(value):
                decorated_calls.append((args, kwargs, value))
                return func(value)

            return wrapped

        return decorate

    monkeypatch.setattr(
        langfuse_utils,
        '_langfuse_sdk',
        SimpleNamespace(Langfuse=MagicMock(), observe=sdk_observe),
    )

    @langfuse_utils.observe(as_type='generation')
    def double(value):
        return value * 2

    assert double(2) == 4
    assert decorated_calls == []

    monkeypatch.setattr(langfuse_utils, '_langfuse_configured', True)
    assert double(3) == 6
    assert decorated_calls == [
        ((), {'as_type': 'generation'}, 3),
    ]


@pytest.mark.asyncio
async def test_observe_preserves_async_functions(monkeypatch):
    def sdk_observe(*args, **kwargs):
        def decorate(func):
            async def wrapped(value):
                return await func(value) + 1

            return wrapped

        return decorate

    monkeypatch.setattr(
        langfuse_utils,
        '_langfuse_sdk',
        SimpleNamespace(Langfuse=MagicMock(), observe=sdk_observe),
    )
    monkeypatch.setattr(langfuse_utils, '_langfuse_configured', True)

    @langfuse_utils.observe()
    async def double(value):
        return value * 2

    assert await double(4) == 9
