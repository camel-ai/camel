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

"""Tests for ScreenshotToolkit verifying no re-entrant agent.step() call."""

import os
import tempfile
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_agent():
    """Create a mock agent with model_backend."""
    agent = MagicMock()
    agent.model_backend.run.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Image analysis result"))]
    )
    agent.system_message = None
    return agent


@pytest.fixture
def toolkit():
    """Create a ScreenshotToolkit instance with a temp directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        from camel.toolkits.screenshot_toolkit import ScreenshotToolkit

        tk = ScreenshotToolkit(working_directory=tmpdir)
        yield tk


@pytest.fixture
def sample_image(toolkit):
    """Create a minimal PNG image file for testing."""
    from PIL import Image

    path = os.path.join(toolkit.screenshots_dir, "test.png")
    img = Image.new("RGB", (10, 10), color="red")
    img.save(path)
    return path


def test_read_image_calls_model_directly(toolkit, mock_agent, sample_image):
    """read_image must call model_backend.run() instead of agent.step()."""
    toolkit.register_agent(mock_agent)

    result = toolkit.read_image(sample_image, "Describe this image")

    mock_agent.model_backend.run.assert_called_once()
    mock_agent.step.assert_not_called()
    assert result == "Image analysis result"


def test_read_image_no_agent_returns_error(toolkit, sample_image):
    """read_image returns an error when no agent is registered."""
    result = toolkit.read_image(sample_image, "Describe this image")
    assert "Error" in result


def test_read_image_missing_file(toolkit, mock_agent):
    """read_image returns an error for a non-existent file."""
    toolkit.register_agent(mock_agent)
    result = toolkit.read_image("/nonexistent/path.png")
    assert "Error" in result
    mock_agent.model_backend.run.assert_not_called()


def test_read_image_passes_openai_formatted_message(
    toolkit, mock_agent, sample_image
):
    """read_image should pass an OpenAI-formatted user message to the model."""
    toolkit.register_agent(mock_agent)
    toolkit.read_image(sample_image, "What is this?")

    call_args = mock_agent.model_backend.run.call_args
    messages = call_args[0][0]
    assert isinstance(messages, list)
    assert messages[0]["role"] == "user"


def test_read_image_includes_system_message(toolkit, mock_agent, sample_image):
    """read_image should prepend the agent's system message if available."""
    sys_msg = MagicMock()
    sys_msg.to_openai_system_message.return_value = {
        "role": "system",
        "content": "You are a vision assistant.",
    }
    mock_agent.system_message = sys_msg
    toolkit.register_agent(mock_agent)

    toolkit.read_image(sample_image, "Describe")

    messages = mock_agent.model_backend.run.call_args[0][0]
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_read_image_handles_streaming_response(toolkit, mock_agent, sample_image):
    """read_image should accumulate content from streaming chunks."""
    chunk1 = MagicMock()
    chunk1.choices = [MagicMock(delta=MagicMock(content="Hello "))]
    chunk2 = MagicMock()
    chunk2.choices = [MagicMock(delta=MagicMock(content="world"))]

    class StreamResponse:
        def __iter__(self):
            return iter([chunk1, chunk2])

    mock_agent.model_backend.run.return_value = StreamResponse()
    toolkit.register_agent(mock_agent)

    result = toolkit.read_image(sample_image, "Describe")
    assert result == "Hello world"


def test_read_image_restores_on_error(
    toolkit, mock_agent, sample_image
):
    """read_image should return error message when model.run() raises."""
    mock_agent.model_backend.run.side_effect = RuntimeError("model error")
    toolkit.register_agent(mock_agent)

    result = toolkit.read_image(sample_image, "Describe")

    assert "Error" in result


def test_read_image_handles_none_content(toolkit, mock_agent, sample_image):
    """read_image should return empty string when model returns None content."""
    mock_agent.model_backend.run.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=None))]
    )
    toolkit.register_agent(mock_agent)

    result = toolkit.read_image(sample_image, "Describe")
    assert result == ""
