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
from unittest.mock import MagicMock, Mock, patch

import pytest

from camel.utils.langfuse import (
    configure_langfuse,
    get_current_agent_session_id,
    get_langfuse_status,
    is_langfuse_available,
    set_current_agent_session_id,
    update_current_observation,
    update_langfuse_trace,
)


@pytest.fixture(autouse=True)
def reset_langfuse_state():
    r"""Reset Langfuse state before each test."""
    # Clear environment variables
    for key in [
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST",
        "LANGFUSE_DEBUG",
        "LANGFUSE_ENABLED",
    ]:
        if key in os.environ:
            del os.environ[key]

    # Reset module state
    import camel.utils.langfuse as langfuse_module

    langfuse_module._langfuse_configured = False

    yield

    # Cleanup after test
    for key in [
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST",
        "LANGFUSE_DEBUG",
        "LANGFUSE_ENABLED",
    ]:
        if key in os.environ:
            del os.environ[key]


def test_configure_langfuse_with_parameters():
    r"""Test configuring Langfuse with explicit parameters."""
    with patch("camel.utils.langfuse.get_client") as mock_get_client:
        mock_get_client.return_value = MagicMock()

        configure_langfuse(
            public_key="test_public_key",
            secret_key="test_secret_key",
            host="https://test.langfuse.com",
            debug=True,
            enabled=True,
        )

        assert os.environ["LANGFUSE_PUBLIC_KEY"] == "test_public_key"
        assert os.environ["LANGFUSE_SECRET_KEY"] == "test_secret_key"
        assert os.environ["LANGFUSE_HOST"] == "https://test.langfuse.com"
        assert os.environ["LANGFUSE_DEBUG"] == "true"
        assert os.environ["LANGFUSE_ENABLED"] == "true"
        assert is_langfuse_available() is True


def test_configure_langfuse_with_env_vars():
    r"""Test configuring Langfuse from environment variables."""
    os.environ["LANGFUSE_PUBLIC_KEY"] = "env_public_key"
    os.environ["LANGFUSE_SECRET_KEY"] = "env_secret_key"
    os.environ["LANGFUSE_HOST"] = "https://env.langfuse.com"
    os.environ["LANGFUSE_DEBUG"] = "true"

    with patch("camel.utils.langfuse.get_client") as mock_get_client:
        mock_get_client.return_value = MagicMock()

        configure_langfuse(enabled=True)

        assert os.environ["LANGFUSE_PUBLIC_KEY"] == "env_public_key"
        assert os.environ["LANGFUSE_SECRET_KEY"] == "env_secret_key"
        assert os.environ["LANGFUSE_HOST"] == "https://env.langfuse.com"
        assert is_langfuse_available() is True


def test_configure_langfuse_disabled():
    r"""Test disabling Langfuse."""
    configure_langfuse(enabled=False)

    assert os.environ.get("LANGFUSE_ENABLED") == "false"
    assert is_langfuse_available() is False


def test_configure_langfuse_default_disabled():
    r"""Test that Langfuse is disabled by default."""
    configure_langfuse()

    assert is_langfuse_available() is False


def test_is_langfuse_available():
    r"""Test checking if Langfuse is available."""
    assert is_langfuse_available() is False

    with patch("camel.utils.langfuse.get_client") as mock_get_client:
        mock_get_client.return_value = MagicMock()
        configure_langfuse(
            public_key="test_key",
            secret_key="test_secret",
            enabled=True,
        )

        assert is_langfuse_available() is True


def test_set_and_get_current_agent_session_id():
    r"""Test setting and getting agent session ID."""
    # Session ID should be None when Langfuse is not configured
    assert get_current_agent_session_id() is None

    # Configure Langfuse first
    with patch("camel.utils.langfuse.get_client") as mock_get_client:
        mock_get_client.return_value = MagicMock()
        configure_langfuse(
            public_key="test_key",
            secret_key="test_secret",
            enabled=True,
        )

        # Set session ID
        set_current_agent_session_id("test_session_123")

        # Get session ID
        assert get_current_agent_session_id() == "test_session_123"

        # Update session ID
        set_current_agent_session_id("test_session_456")
        assert get_current_agent_session_id() == "test_session_456"


def test_update_langfuse_trace_no_langfuse():
    r"""Test update_langfuse_trace when Langfuse is not available."""
    result = update_langfuse_trace(
        session_id="test_session",
        user_id="test_user",
    )

    assert result is False


def test_update_langfuse_trace_no_active_span():
    r"""Test update_langfuse_trace when no active span exists."""
    with patch("camel.utils.langfuse.get_client") as mock_get_client:
        mock_get_client.return_value = MagicMock()
        configure_langfuse(
            public_key="test_key",
            secret_key="test_secret",
            enabled=True,
        )

        with patch(
            "opentelemetry.trace.get_current_span"
        ) as mock_get_span:
            mock_get_span.return_value = None

            result = update_langfuse_trace(
                session_id="test_session",
                user_id="test_user",
            )

            assert result is False


def test_update_langfuse_trace_success():
    r"""Test successful update of Langfuse trace."""
    with patch("camel.utils.langfuse.get_client") as mock_get_client:
        mock_get_client.return_value = MagicMock()
        configure_langfuse(
            public_key="test_key",
            secret_key="test_secret",
            enabled=True,
        )

        # Set session ID
        set_current_agent_session_id("test_session_123")

        # Mock OpenTelemetry span
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_span.set_attribute = MagicMock()

        with patch(
            "opentelemetry.trace.get_current_span"
        ) as mock_get_span:
            mock_get_span.return_value = mock_span

            result = update_langfuse_trace(
                user_id="test_user",
                metadata={"key1": "value1", "key2": "value2"},
                tags=["tag1", "tag2"],
            )

            assert result is True
            # Verify attributes were set
            # session_id (from get_current_agent_session_id) + user_id + 2 metadata keys + tags = 5
            assert mock_span.set_attribute.call_count == 5


def test_update_langfuse_trace_with_session_id():
    r"""Test update_langfuse_trace with explicit session_id."""
    with patch("camel.utils.langfuse.get_client") as mock_get_client:
        mock_get_client.return_value = MagicMock()
        configure_langfuse(
            public_key="test_key",
            secret_key="test_secret",
            enabled=True,
        )

        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_span.set_attribute = MagicMock()

        with patch(
            "opentelemetry.trace.get_current_span"
        ) as mock_get_span:
            mock_get_span.return_value = mock_span

            result = update_langfuse_trace(session_id="explicit_session")

            assert result is True
            mock_span.set_attribute.assert_called()


def test_update_langfuse_trace_no_attributes():
    r"""Test update_langfuse_trace with no attributes to set."""
    with patch("camel.utils.langfuse.get_client") as mock_get_client:
        mock_get_client.return_value = MagicMock()
        configure_langfuse(
            public_key="test_key",
            secret_key="test_secret",
            enabled=True,
        )

        result = update_langfuse_trace()

        assert result is False


def test_update_current_observation_no_langfuse():
    r"""Test update_current_observation when Langfuse is not available."""
    # Should not raise exception, silently fail
    update_current_observation(
        model="test_model",
        usage_details={"prompt_tokens": 10, "completion_tokens": 20},
    )


def test_update_current_observation_success():
    r"""Test successful update of current observation."""
    # Mock langfuse.get_client (not camel.utils.langfuse.get_client)
    # because update_current_observation imports it directly
    with patch("langfuse.get_client") as mock_get_client:
        mock_client = MagicMock()
        # Mock _get_current_otel_span to return a valid span
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_client._get_current_otel_span = MagicMock(return_value=mock_span)
        # Enable tracing
        mock_client._tracing_enabled = True
        mock_get_client.return_value = mock_client

        configure_langfuse(
            public_key="test_key",
            secret_key="test_secret",
            enabled=True,
        )

        update_current_observation(
            input={"messages": [{"role": "user", "content": "test"}]},
            output={"content": "response"},
            model="gpt-4",
            model_parameters={"temperature": 0.7},
            usage_details={"prompt_tokens": 10, "completion_tokens": 20},
        )

        # Verify update_current_generation was called
        mock_client.update_current_generation.assert_called_once()
        call_kwargs = mock_client.update_current_generation.call_args[1]
        assert call_kwargs["model"] == "gpt-4"
        assert call_kwargs["model_parameters"] == {"temperature": 0.7}
        assert call_kwargs["usage_details"] == {
            "prompt_tokens": 10,
            "completion_tokens": 20,
        }


def test_update_current_observation_with_usage_parameter():
    r"""Test update_current_observation with 'usage' parameter instead of 'usage_details'."""
    # Mock langfuse.get_client (not camel.utils.langfuse.get_client)
    with patch("langfuse.get_client") as mock_get_client:
        mock_client = MagicMock()
        # Mock _get_current_otel_span to return a valid span
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_client._get_current_otel_span = MagicMock(return_value=mock_span)
        # Enable tracing
        mock_client._tracing_enabled = True
        mock_get_client.return_value = mock_client

        configure_langfuse(
            public_key="test_key",
            secret_key="test_secret",
            enabled=True,
        )

        # Simulate usage object (like OpenAI CompletionUsage)
        usage_obj = MagicMock()
        usage_obj.prompt_tokens = 15
        usage_obj.completion_tokens = 25
        usage_obj.total_tokens = 40
        usage_obj.__dict__ = {
            "prompt_tokens": 15,
            "completion_tokens": 25,
            "total_tokens": 40,
        }

        update_current_observation(
            model="gpt-4",
            usage=usage_obj,
        )

        # Verify usage was converted to usage_details
        mock_client.update_current_generation.assert_called_once()
        call_kwargs = mock_client.update_current_generation.call_args[1]
        assert "usage_details" in call_kwargs or call_kwargs.get("usage_details")


def test_update_current_observation_with_usage_dict():
    r"""Test update_current_observation with usage as dict."""
    # Mock langfuse.get_client (not camel.utils.langfuse.get_client)
    with patch("langfuse.get_client") as mock_get_client:
        mock_client = MagicMock()
        # Mock _get_current_otel_span to return a valid span
        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_client._get_current_otel_span = MagicMock(return_value=mock_span)
        # Enable tracing
        mock_client._tracing_enabled = True
        mock_get_client.return_value = mock_client

        configure_langfuse(
            public_key="test_key",
            secret_key="test_secret",
            enabled=True,
        )

        update_current_observation(
            model="gpt-4",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
        )

        mock_client.update_current_generation.assert_called_once()


def test_update_current_observation_exception_handling():
    r"""Test that update_current_observation handles exceptions gracefully."""
    with patch("camel.utils.langfuse.get_client") as mock_get_client:
        mock_get_client.side_effect = Exception("Test error")

        configure_langfuse(
            public_key="test_key",
            secret_key="test_secret",
            enabled=True,
        )

        # Should not raise exception
        update_current_observation(model="test_model")


def test_get_langfuse_status():
    r"""Test getting Langfuse status."""
    status = get_langfuse_status()

    assert isinstance(status, dict)
    assert "configured" in status
    assert "has_public_key" in status
    assert "has_secret_key" in status
    assert "env_enabled" in status
    assert "host" in status
    assert "debug" in status
    assert "current_session_id" in status

    assert status["configured"] is False
    assert status["current_session_id"] is None


def test_get_langfuse_status_configured():
    r"""Test getting Langfuse status when configured."""
    with patch("camel.utils.langfuse.get_client") as mock_get_client:
        mock_get_client.return_value = MagicMock()

        configure_langfuse(
            public_key="test_key",
            secret_key="test_secret",
            host="https://test.langfuse.com",
            debug=True,
            enabled=True,
        )

        set_current_agent_session_id("test_session")

        status = get_langfuse_status()

        assert status["configured"] is True
        assert status["has_public_key"] is True
        assert status["has_secret_key"] is True
        assert status["env_enabled"] is True
        assert status["host"] == "https://test.langfuse.com"
        assert status["debug"] is True
        assert status["current_session_id"] == "test_session"


if __name__ == "__main__":
    import sys

    pytest.main([sys.argv[0]])
