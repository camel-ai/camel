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

import pytest

from camel.configs import MoonshotConfig
from camel.models import MoonshotModel
from camel.types import ModelType


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.MOONSHOT_V1_8K,
        ModelType.MOONSHOT_V1_32K,
        ModelType.MOONSHOT_V1_128K,
        ModelType.MOONSHOT_KIMI_K2,
        ModelType.MOONSHOT_KIMI_K2_5,
        ModelType.MOONSHOT_KIMI_K2_TURBO_PREVIEW,
        ModelType.MOONSHOT_KIMI_K2_THINKING,
        ModelType.MOONSHOT_KIMI_K2_THINKING_TURBO,
    ],
)
def test_moonshot_model(model_type: ModelType, monkeypatch):
    monkeypatch.setenv("MOONSHOT_API_KEY", "test_key")
    model = MoonshotModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == MoonshotConfig().as_dict()
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
def test_moonshot_model_thinking_config(monkeypatch):
    """Test that interleaved_thinking configuration is properly set."""
    monkeypatch.setenv("MOONSHOT_API_KEY", "test_key")
    config = MoonshotConfig(interleaved_thinking=True)
    model = MoonshotModel(
        ModelType.MOONSHOT_KIMI_K2,
        model_config_dict=config.as_dict(),
    )
    assert model.model_config_dict.get("interleaved_thinking") is True
    assert model._is_thinking_enabled() is True


@pytest.mark.model_backend
def test_moonshot_model_thinking_disabled(monkeypatch):
    """Test that interleaved_thinking is disabled by default."""
    monkeypatch.setenv("MOONSHOT_API_KEY", "test_key")
    model = MoonshotModel(ModelType.MOONSHOT_V1_8K)
    assert model._is_thinking_enabled() is False


@pytest.mark.model_backend
def test_moonshot_model_inject_reasoning_content(monkeypatch):
    """Test reasoning_content injection into assistant messages."""
    monkeypatch.setenv("MOONSHOT_API_KEY", "test_key")
    config = MoonshotConfig(interleaved_thinking=True)
    model = MoonshotModel(
        ModelType.MOONSHOT_KIMI_K2,
        model_config_dict=config.as_dict(),
    )

    # Set up test messages with tool calls
    messages = [
        {"role": "user", "content": "Hello"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "call_123", "function": {"name": "test"}}],
        },
        {"role": "tool", "content": "result", "tool_call_id": "call_123"},
    ]

    # Set the last reasoning content
    model._last_reasoning = "This is my reasoning"

    # Inject reasoning content
    processed = model._inject_reasoning(messages)

    # Check that reasoning_content was injected
    assert processed[1].get("reasoning_content") == "This is my reasoning"
    # Check that _last_reasoning was cleared
    assert model._last_reasoning is None


@pytest.mark.model_backend
def test_moonshot_model_inject_reasoning_content_disabled(monkeypatch):
    """Test that reasoning_content is not injected when disabled."""
    monkeypatch.setenv("MOONSHOT_API_KEY", "test_key")
    model = MoonshotModel(ModelType.MOONSHOT_V1_8K)

    messages = [
        {"role": "user", "content": "Hello"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "call_123", "function": {"name": "test"}}],
        },
    ]

    model._last_reasoning = "This is my reasoning"
    processed = model._inject_reasoning(messages)

    # Should return original messages unchanged
    assert processed == messages
    # reasoning content should not be cleared when thinking is disabled
    assert model._last_reasoning == "This is my reasoning"


@pytest.mark.model_backend
def test_moonshot_model_extract_reasoning_content(monkeypatch):
    """Test extraction of reasoning_content from response."""
    monkeypatch.setenv("MOONSHOT_API_KEY", "test_key")
    model = MoonshotModel(ModelType.MOONSHOT_KIMI_K2)

    # Create a mock response with reasoning_content
    mock_response = MagicMock()
    mock_message = MagicMock()
    mock_message.reasoning_content = "Extracted reasoning"
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    result = model._extract_reasoning(mock_response)
    assert result == "Extracted reasoning"


@pytest.mark.model_backend
def test_moonshot_model_extract_reasoning_content_none(monkeypatch):
    """Test extraction returns None when no reasoning_content."""
    monkeypatch.setenv("MOONSHOT_API_KEY", "test_key")
    model = MoonshotModel(ModelType.MOONSHOT_KIMI_K2)

    # Create a mock response without reasoning_content
    mock_response = MagicMock()
    mock_message = MagicMock(spec=[])  # No reasoning_content attribute
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    result = model._extract_reasoning(mock_response)
    assert result is None
