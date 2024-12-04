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
import os
from unittest.mock import MagicMock, patch

import pytest
from requests import RequestException

from camel.toolkits.whatsapp_toolkit import WhatsAppToolkit


@pytest.fixture
def whatsapp_toolkit():
    # Set environment variables for testing
    os.environ['WHATSAPP_ACCESS_TOKEN'] = 'test_token'
    os.environ['WHATSAPP_PHONE_NUMBER_ID'] = 'test_phone_number_id'
    return WhatsAppToolkit()


def test_init_missing_credentials():
    # Test initialization with missing credentials
    os.environ.pop('WHATSAPP_ACCESS_TOKEN', None)
    os.environ.pop('WHATSAPP_PHONE_NUMBER_ID', None)

    with pytest.raises(ValueError):
        WhatsAppToolkit()


@patch('requests.post')
def test_send_message_success(mock_post, whatsapp_toolkit):
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {"message_id": "test_message_id"}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = whatsapp_toolkit.send_message("1234567890", "Test message")

    assert result == {"message_id": "test_message_id"}
    mock_post.assert_called_once()


@patch('requests.post')
def test_send_message_failure(mock_post, whatsapp_toolkit):
    # Mock failed API response
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("API Error")
    mock_post.return_value = mock_response

    result = whatsapp_toolkit.send_message("1234567890", "Test message")

    assert result == "Failed to send message: API Error"
    mock_post.assert_called_once()


@patch('requests.get')
def test_get_message_templates_success(mock_get, whatsapp_toolkit):
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [{"name": "template1"}, {"name": "template2"}]
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = whatsapp_toolkit.get_message_templates()

    assert result == [{"name": "template1"}, {"name": "template2"}]
    mock_get.assert_called_once()


@patch('requests.get')
def test_get_message_templates_failure(mock_get, whatsapp_toolkit):
    # Mock failed API response
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("API Error")
    mock_response.json.return_value = {
        "error": "Failed to retrieve message templates"
    }
    mock_get.return_value = mock_response

    result = whatsapp_toolkit.get_message_templates()
    assert result == 'Failed to retrieve message templates: API Error'
    mock_get.assert_called_once()


@patch('requests.get')
def test_get_business_profile_success(mock_get, whatsapp_toolkit):
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "name": "Test Business",
        "description": "Test Description",
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = whatsapp_toolkit.get_business_profile()

    assert result == {
        "name": "Test Business",
        "description": "Test Description",
    }
    mock_get.assert_called_once()


@patch('requests.get')
def test_get_business_profile_failure(mock_get, whatsapp_toolkit):
    # Mock failed API response
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("API Error")
    mock_response.json.return_value = {
        "error": "Failed to retrieve message templates"
    }
    mock_get.return_value = mock_response

    result = whatsapp_toolkit.get_business_profile()
    assert isinstance(result, str)
    assert "Failed to retrieve business profile" in result
    assert "API Error" in result
    mock_get.assert_called_once()


def test_get_tools(whatsapp_toolkit):
    tools = whatsapp_toolkit.get_tools()

    assert len(tools) == 3
    for tool in tools:
        assert callable(tool) or hasattr(tool, 'func')
        assert callable(tool) or (
            hasattr(tool, 'func') and callable(tool.func)
        )


@patch('time.sleep')
@patch('requests.post')
def test_retry_mechanism(mock_post, mock_sleep, whatsapp_toolkit):
    # Mock failed API responses followed by a success
    mock_post.side_effect = [
        RequestException("API Error"),
        RequestException("API Error"),
        MagicMock(
            json=lambda: {"message_id": "test_message_id"},
            raise_for_status=lambda: None,
        ),
    ]

    result = whatsapp_toolkit.send_message("1234567890", "Test message")

    assert result == {"message_id": "test_message_id"}
    assert mock_post.call_count == 3
    assert mock_sleep.call_count == 2
