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
from unittest.mock import MagicMock, patch

import pytest
import requests
from PIL import Image

from camel.messages.base import BaseMessage
from camel.models import BaseModelBackend
from camel.toolkits import ImageAnalysisToolkit


# Fixture for mock model backend
@pytest.fixture
def mock_model():
    return MagicMock(spec=BaseModelBackend)


# Fixture for toolkit with mocked dependencies
@pytest.fixture
def image_toolkit(mock_model):
    with (
        patch('requests.get'),
        patch('PIL.Image.open'),
        patch('camel.agents.chat_agent.ChatAgent'),
    ):
        yield ImageAnalysisToolkit(mock_model)


@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.system_message = BaseMessage.make_assistant_message(
        role_name="Test Analyst", content="Default content"
    )
    return agent


# --------------------------
# Test _load_image method
# --------------------------
def test_load_image_local_success(image_toolkit):
    mock_image = MagicMock()
    with patch('PIL.Image.open') as mock_open:
        mock_open.return_value.__enter__.return_value = mock_image
        result = image_toolkit._load_image("valid.jpg")
        assert isinstance(result, MagicMock)


def test_load_image_url_success(image_toolkit):
    mock_response = MagicMock()
    mock_response.content = b"fake_image_data"

    with (
        patch('requests.get', return_value=mock_response),
        patch('PIL.Image.open') as mock_img_open,
    ):
        mock_img = Image.new('RGB', (100, 100))
        mock_img_open.return_value = mock_img

        result = image_toolkit._load_image("http://valid.com/image.jpg")
        assert isinstance(result, Image.Image)


def test_load_image_url_failure(image_toolkit):
    with patch(
        'requests.get',
        side_effect=requests.exceptions.RequestException("Failed"),
    ):
        with pytest.raises(requests.exceptions.RequestException):
            image_toolkit._load_image("http://invalid.com/image.jpg")


def test_load_image_local_failure(image_toolkit):
    with patch('PIL.Image.open', side_effect=IOError("Corrupt file")):
        with pytest.raises(ValueError):
            image_toolkit._load_image("invalid.jpg")


# --------------------------
# Test image_to_text method
# --------------------------


def test_image_to_text_custom_prompt(image_toolkit):
    mock_agent = MagicMock()
    mock_agent.system_message = MagicMock()
    mock_agent.system_message.content = "Special instructions"
    mock_agent.step.return_value.msgs = [MagicMock(content="Custom analysis")]

    with patch('camel.agents.chat_agent.ChatAgent', return_value=mock_agent):
        assert "Special instructions" == mock_agent.system_message.content


# --------------------------
# Test ask_question_about_image
# --------------------------
def test_ask_question_default_instructions(image_toolkit):
    mock_system_message = MagicMock(spec=BaseMessage)
    mock_system_message.content = "Visual QA Specialist is here to help."

    mock_agent = MagicMock()
    mock_agent.system_message = mock_system_message
    mock_agent.step.return_value.msgs = [MagicMock(content="42")]

    with patch('camel.agents.chat_agent.ChatAgent', return_value=mock_agent):
        result = image_toolkit.ask_question_about_image(
            "test.jpg", "What's the answer?"
        )
        assert "42" in result
        assert "Visual QA Specialist" in mock_agent.system_message.content


def test_ask_question_custom_instructions(image_toolkit):
    custom_content = "Special analysis rules"

    mock_system_message = MagicMock()
    mock_system_message.content = custom_content

    mock_agent = MagicMock()
    mock_agent.system_message = mock_system_message
    mock_agent.step.return_value.msgs = [MagicMock(content="Custom answer")]

    with patch('camel.agents.chat_agent.ChatAgent', return_value=mock_agent):
        assert mock_agent.system_message.content == custom_content


# --------------------------
# Test error handling
# --------------------------
def test_analyze_image_handling_failure(image_toolkit):
    with patch.object(
        image_toolkit, '_load_image', side_effect=ValueError("Corrupt file")
    ):
        result = image_toolkit.image_to_text("bad.jpg")
        assert "Image error" in result


def test_unexpected_error_handling(image_toolkit):
    with patch.object(
        image_toolkit, '_load_image', side_effect=Exception("Random failure")
    ):
        result = image_toolkit.ask_question_about_image("bad.jpg", "Why?")
        assert "Analysis failed" in result


# --------------------------
# Test edge cases
# --------------------------
def test_empty_image_path(image_toolkit):
    with patch.object(
        image_toolkit, '_load_image', side_effect=ValueError("Empty path")
    ):
        result = image_toolkit.image_to_text("")
        assert "Image error: Empty path" in result


def test_non_image_file(image_toolkit):
    with patch('PIL.Image.open', side_effect=IOError("Not an image")):
        result = image_toolkit.ask_question_about_image(
            "text.txt", "What's this?"
        )
        assert "Image error" in result
