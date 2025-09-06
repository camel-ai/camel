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

from camel.toolkits.wechat_official_toolkit import (
    WeChatOfficialToolkit,
    _get_wechat_access_token,
)


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """Set up environment variables for testing."""
    monkeypatch.setenv("WECHAT_APP_ID", "test_app_id")
    monkeypatch.setenv("WECHAT_APP_SECRET", "test_app_secret")


def test_toolkit_init():
    """Test toolkit initialization."""
    toolkit = WeChatOfficialToolkit()
    assert toolkit.base_url == "https://api.weixin.qq.com"


def test_get_tools():
    """Test getting available tools."""
    toolkit = WeChatOfficialToolkit()
    tools = toolkit.get_tools()
    assert len(tools) == 6


@patch('camel.toolkits.wechat_official_toolkit.requests.get')
def test_get_access_token(mock_get):
    """Test access token retrieval."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'access_token': 'test_token',
        'expires_in': 7200,
    }
    mock_get.return_value = mock_response

    token = _get_wechat_access_token()
    assert token == 'test_token'


@patch('camel.toolkits.wechat_official_toolkit._make_wechat_request')
def test_send_message(mock_request):
    """Test sending customer message."""
    mock_request.return_value = {'errcode': 0}

    toolkit = WeChatOfficialToolkit()
    result = toolkit.send_customer_message('test_openid', 'Hello', 'text')
    assert 'Message sent successfully' in result


@patch('camel.toolkits.wechat_official_toolkit._make_wechat_request')
def test_get_user_info(mock_request):
    """Test getting user information."""
    expected_data = {'openid': 'test_openid', 'nickname': 'Test User'}
    mock_request.return_value = expected_data

    toolkit = WeChatOfficialToolkit()
    result = toolkit.get_user_info('test_openid')
    assert result == expected_data


def test_missing_credentials(monkeypatch):
    """Test initialization with missing credentials."""
    monkeypatch.delenv("WECHAT_APP_ID", raising=False)

    with pytest.raises(ValueError, match="WeChat credentials missing"):
        WeChatOfficialToolkit()
