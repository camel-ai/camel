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
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from camel.utils import langfuse as lf


class _FakeModelBackend:
    r"""Minimal stand-in for a model backend using with_langfuse_trace."""

    model_type = "fake-model"

    @lf.with_langfuse_trace
    def _run(self, value):
        return value

    @lf.with_langfuse_trace
    async def _arun(self, value):
        return value


@pytest.fixture(autouse=True)
def _reset_langfuse_state():
    lf._langfuse_configured = False
    lf.set_current_agent_session_id(None)
    yield
    lf._langfuse_configured = False
    lf.set_current_agent_session_id(None)


def test_is_langfuse_available_defaults_to_false():
    assert lf.is_langfuse_available() is False


def test_configure_langfuse_disabled_by_default(monkeypatch):
    monkeypatch.delenv("LANGFUSE_ENABLED", raising=False)
    monkeypatch.setattr(lf, "Langfuse", MagicMock())

    lf.configure_langfuse(public_key="pk", secret_key="sk")

    assert lf.is_langfuse_available() is False
    lf.Langfuse.assert_not_called()


def test_configure_langfuse_enabled_initializes_client(monkeypatch):
    mock_langfuse_cls = MagicMock()
    monkeypatch.setattr(lf, "Langfuse", mock_langfuse_cls)

    lf.configure_langfuse(
        public_key="pk", secret_key="sk", host="https://x", enabled=True
    )

    assert lf.is_langfuse_available() is True
    mock_langfuse_cls.assert_called_once()
    _, kwargs = mock_langfuse_cls.call_args
    assert kwargs["public_key"] == "pk"
    assert kwargs["secret_key"] == "sk"
    assert kwargs["host"] == "https://x"
    assert kwargs["tracing_enabled"] is True


def test_update_langfuse_trace_noop_when_not_configured(monkeypatch):
    entered = MagicMock()
    monkeypatch.setattr(
        lf, "propagate_attributes", MagicMock(return_value=entered)
    )

    result = lf.update_langfuse_trace(session_id="s1")

    assert result is False
    lf.propagate_attributes.assert_not_called()


def test_update_langfuse_trace_enters_propagation_scope(monkeypatch):
    lf._langfuse_configured = True
    entered = MagicMock()
    mock_propagate = MagicMock(return_value=entered)
    monkeypatch.setattr(lf, "propagate_attributes", mock_propagate)

    result = lf.update_langfuse_trace(
        session_id="s1", user_id="u1", metadata={"k": "v"}, tags=["t1"]
    )

    assert result is True
    mock_propagate.assert_called_once_with(
        session_id="s1", user_id="u1", metadata={"k": "v"}, tags=["t1"]
    )
    entered.__enter__.assert_called_once()


def test_update_langfuse_trace_falls_back_to_current_session(monkeypatch):
    lf._langfuse_configured = True
    lf.set_current_agent_session_id("agent-session")
    mock_propagate = MagicMock(return_value=MagicMock())
    monkeypatch.setattr(lf, "propagate_attributes", mock_propagate)

    lf.update_langfuse_trace()

    _, kwargs = mock_propagate.call_args
    assert kwargs["session_id"] == "agent-session"


def test_update_current_observation_noop_when_not_configured(monkeypatch):
    mock_get_client = MagicMock()
    monkeypatch.setattr(lf, "get_client", mock_get_client)

    lf.update_current_observation(input={"a": 1})

    mock_get_client.assert_not_called()


def test_update_current_observation_maps_legacy_usage_kwarg(monkeypatch):
    lf._langfuse_configured = True
    mock_client = MagicMock()
    monkeypatch.setattr(lf, "get_client", MagicMock(return_value=mock_client))

    lf.update_current_observation(usage={"input_tokens": 3})

    mock_client.update_current_generation.assert_called_once()
    _, kwargs = mock_client.update_current_generation.call_args
    assert kwargs["usage_details"] == {"input_tokens": 3}


def test_update_current_observation_ignores_unknown_kwargs(monkeypatch):
    lf._langfuse_configured = True
    mock_client = MagicMock()
    monkeypatch.setattr(lf, "get_client", MagicMock(return_value=mock_client))

    lf.update_current_observation(
        input={"a": 1}, output={"b": 2}, totally_unknown_field="ignored"
    )

    mock_client.update_current_generation.assert_called_once()
    _, kwargs = mock_client.update_current_generation.call_args
    assert "totally_unknown_field" not in kwargs
    assert kwargs["input"] == {"a": 1}
    assert kwargs["output"] == {"b": 2}


def test_with_langfuse_trace_sync_passthrough_when_disabled():
    backend = _FakeModelBackend()
    assert backend._run("hello") == "hello"


@pytest.mark.asyncio
async def test_with_langfuse_trace_async_passthrough_when_disabled():
    backend = _FakeModelBackend()
    assert await backend._arun("hello") == "hello"


def test_with_langfuse_trace_sync_enters_propagation_scope(monkeypatch):
    lf._langfuse_configured = True
    lf.set_current_agent_session_id("session-xyz")

    calls = []

    @contextmanager
    def fake_propagate_attributes(**kwargs):
        calls.append(kwargs)
        yield

    monkeypatch.setattr(lf, "propagate_attributes", fake_propagate_attributes)

    backend = _FakeModelBackend()
    assert backend._run("hi") == "hi"

    assert len(calls) == 1
    assert calls[0]["session_id"] == "session-xyz"
    assert calls[0]["tags"] == ["CAMEL-AI", "fake-model"]
    assert calls[0]["metadata"]["model_type"] == "fake-model"


@pytest.mark.asyncio
async def test_with_langfuse_trace_async_enters_propagation_scope(
    monkeypatch,
):
    lf._langfuse_configured = True
    lf.set_current_agent_session_id("session-async")

    calls = []

    @contextmanager
    def fake_propagate_attributes(**kwargs):
        calls.append(kwargs)
        yield

    monkeypatch.setattr(lf, "propagate_attributes", fake_propagate_attributes)

    backend = _FakeModelBackend()
    result = await backend._arun("hi-async")

    assert result == "hi-async"
    assert len(calls) == 1
    assert calls[0]["session_id"] == "session-async"


def test_with_langfuse_trace_propagates_exceptions(monkeypatch):
    lf._langfuse_configured = True

    class _Backend:
        model_type = "fake-model"

        @lf.with_langfuse_trace
        def _run(self):
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        _Backend()._run()
