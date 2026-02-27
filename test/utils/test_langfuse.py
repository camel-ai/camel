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
from unittest.mock import MagicMock

import camel.utils.langfuse as langfuse_utils


def _clear_langfuse_env(monkeypatch):
    keys = [
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST",
        "LANGFUSE_BASE_URL",
        "LANGFUSE_DEBUG",
        "LANGFUSE_ENABLED",
        "LANGFUSE_TRACING_ENABLED",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)


def test_configure_langfuse_enabled_sets_env_and_marks_configured(monkeypatch):
    _clear_langfuse_env(monkeypatch)
    client = MagicMock()
    monkeypatch.setattr(langfuse_utils, "LANGFUSE_AVAILABLE", True)
    monkeypatch.setattr(langfuse_utils, "get_client", lambda: client)

    langfuse_utils.configure_langfuse(
        public_key="pk-lf-test",
        secret_key="sk-lf-test",
        host="https://cloud.langfuse.com",
        debug=True,
        enabled=True,
    )

    assert langfuse_utils.is_langfuse_available() is True
    assert langfuse_utils.os.environ["LANGFUSE_PUBLIC_KEY"] == "pk-lf-test"
    assert langfuse_utils.os.environ["LANGFUSE_SECRET_KEY"] == "sk-lf-test"
    assert (
        langfuse_utils.os.environ["LANGFUSE_BASE_URL"]
        == "https://cloud.langfuse.com"
    )
    assert langfuse_utils.os.environ["LANGFUSE_ENABLED"] == "true"
    assert langfuse_utils.os.environ["LANGFUSE_TRACING_ENABLED"] == "true"


def test_configure_langfuse_disabled_sets_disabled_flags(monkeypatch):
    _clear_langfuse_env(monkeypatch)
    langfuse_utils.configure_langfuse(enabled=False)
    assert langfuse_utils.is_langfuse_available() is False
    assert langfuse_utils.os.environ["LANGFUSE_ENABLED"] == "false"
    assert langfuse_utils.os.environ["LANGFUSE_TRACING_ENABLED"] == "false"


def test_update_langfuse_trace_calls_v3_client(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(langfuse_utils, "_langfuse_configured", True)
    monkeypatch.setattr(langfuse_utils, "get_client", lambda: client)

    ok = langfuse_utils.update_langfuse_trace(
        session_id="session-1",
        user_id="user-1",
        metadata={"source": "camel"},
        tags=["tag-a"],
    )

    assert ok is True
    client.update_langfuse_trace.assert_called_once_with(
        session_id="session-1",
        user_id="user-1",
        metadata={"source": "camel"},
        tags=["tag-a"],
    )


def test_update_langfuse_trace_normalizes_non_string_tags(monkeypatch):
    class FakeTag:
        def __str__(self):
            return "fake-tag"

    client = MagicMock()
    monkeypatch.setattr(langfuse_utils, "_langfuse_configured", True)
    monkeypatch.setattr(langfuse_utils, "get_client", lambda: client)

    ok = langfuse_utils.update_langfuse_trace(
        session_id="session-1",
        tags=[FakeTag(), None],  # type: ignore[list-item]
    )

    assert ok is True
    client.update_langfuse_trace.assert_called_once_with(
        session_id="session-1",
        tags=["fake-tag"],
    )


def test_update_current_observation_maps_usage_to_generation(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(langfuse_utils, "_langfuse_configured", True)
    monkeypatch.setattr(langfuse_utils, "get_client", lambda: client)

    langfuse_utils.update_current_observation(
        usage={"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}
    )

    client.update_current_generation.assert_called_once_with(
        name=None,
        input=None,
        output=None,
        metadata=None,
        version=None,
        level=None,
        status_message=None,
        completion_start_time=None,
        model=None,
        model_parameters=None,
        usage_details={
            "prompt_tokens": 1,
            "completion_tokens": 2,
            "total_tokens": 3,
        },
        cost_details=None,
        prompt=None,
    )
    client.update_current_span.assert_not_called()


def test_update_current_observation_uses_span_without_generation_fields(
    monkeypatch,
):
    client = MagicMock()
    monkeypatch.setattr(langfuse_utils, "_langfuse_configured", True)
    monkeypatch.setattr(langfuse_utils, "get_client", lambda: client)

    langfuse_utils.update_current_observation(
        input={"messages": []},
        output={"text": "ok"},
        metadata={"source": "camel"},
    )

    client.update_current_span.assert_called_once_with(
        name=None,
        input={"messages": []},
        output={"text": "ok"},
        metadata={"source": "camel"},
        version=None,
        level=None,
        status_message=None,
    )
