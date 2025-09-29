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

from camel.toolkits.dingtalk import (
    DingtalkToolkit,
    _get_dingtalk_access_token,
)


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """Set up environment variables for testing."""
    monkeypatch.setenv("DINGTALK_APP_KEY", "test_app_key")
    monkeypatch.setenv("DINGTALK_APP_SECRET", "test_app_secret")
    monkeypatch.setenv(
        "DINGTALK_WEBHOOK_URL",
        "https://oapi.dingtalk.com/robot/send?access_token=test_webhook_token",
    )
    monkeypatch.setenv("DINGTALK_WEBHOOK_SECRET", "test_webhook_secret")


def test_toolkit_init():
    """Test toolkit initialization."""
    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        assert toolkit.base_url == "https://oapi.dingtalk.com"


def test_get_tools():
    """Test getting available tools."""
    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        tools = toolkit.get_tools()
        # Check that we have the expected number of tools
        assert len(tools) >= 5  # send_text_message, send_markdown_message,
        # get_user_info, send_webhook_message, etc.


@patch('camel.toolkits.dingtalk.requests.get')
def test_get_access_token(mock_get):
    """Test access token retrieval."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'access_token': 'test_token',
        'expires_in': 7200,
        'errcode': 0,
    }
    mock_get.return_value = mock_response

    token = _get_dingtalk_access_token()
    assert token == 'test_token'


@patch('camel.toolkits.dingtalk._make_dingtalk_request')
def test_send_text_message(mock_request):
    """Test sending text message."""
    mock_request.return_value = {'errcode': 0}

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_send_text_message(
            'test_userid', 'Hello World'
        )
        assert 'Message sent successfully' in result


@patch('camel.toolkits.dingtalk._make_dingtalk_request')
def test_send_markdown_message(mock_request):
    """Test sending markdown message."""
    mock_request.return_value = {'errcode': 0}

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_send_markdown_message(
            'test_userid', 'Test Title', '# Hello World'
        )
        assert 'Markdown message sent successfully' in result


@patch('camel.toolkits.dingtalk._make_dingtalk_request')
def test_get_user_info(mock_request):
    """Test getting user information."""
    expected_data = {
        'userid': 'test_userid',
        'name': 'Test User',
        'errcode': 0,
    }
    mock_request.return_value = expected_data

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_get_user_info('test_userid')
        assert result == expected_data


@patch('camel.toolkits.dingtalk.requests.post')
def test_send_webhook_message(mock_post):
    """Test sending webhook message."""
    mock_response = MagicMock()
    mock_response.json.return_value = {'errcode': 0}
    mock_post.return_value = mock_response

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_send_webhook_message('Hello from webhook!')
        assert 'Webhook message sent successfully' in result


@patch('camel.toolkits.dingtalk._make_dingtalk_request')
def test_get_department_list(mock_request):
    """Test getting department list."""
    expected_data = {
        'department': [
            {'id': 1, 'name': 'Test Department'},
            {'id': 2, 'name': 'Another Department'},
        ],
        'errcode': 0,
    }
    mock_request.return_value = expected_data

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_get_department_list()
        assert result == expected_data


@patch('camel.toolkits.dingtalk._make_dingtalk_request')
def test_search_users_by_name(mock_request):
    """Test searching users by name."""
    expected_data = {
        'userlist': [
            {'userid': 'user1', 'name': 'John Doe'},
            {'userid': 'user2', 'name': 'Jane Smith'},
        ],
        'errcode': 0,
    }
    mock_request.return_value = expected_data

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_search_users_by_name('John')
        assert result == expected_data


def test_missing_credentials(monkeypatch):
    """Test initialization with missing credentials."""
    monkeypatch.delenv("DINGTALK_APP_KEY", raising=False)

    with pytest.raises(ValueError, match="Dingtalk credentials missing"):
        DingtalkToolkit()


def test_missing_webhook_url():
    """Test webhook message with missing webhook URL."""
    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()

        # Test with no webhook URL in environment
        with patch.dict('os.environ', {}, clear=True):
            result = toolkit.dingtalk_send_webhook_message('Hello')
            assert 'Webhook URL not provided' in result


@patch('camel.toolkits.dingtalk.requests.get')
def test_access_token_error_handling(mock_get):
    """Test access token retrieval with API error."""
    # Clear the global token cache
    import camel.toolkits.dingtalk as dingtalk_module

    dingtalk_module._dingtalk_access_token = None
    dingtalk_module._dingtalk_access_token_expires_at = 0

    mock_response = MagicMock()
    mock_response.json.return_value = {
        'errcode': 40001,
        'errmsg': 'Invalid app key',
    }
    mock_get.return_value = mock_response

    with pytest.raises(ValueError, match="Failed to get access token 40001"):
        _get_dingtalk_access_token()


@patch('camel.toolkits.dingtalk._make_dingtalk_request')
def test_send_text_message_error_handling(mock_request):
    """Test sending text message with API error."""
    mock_request.side_effect = Exception("Network error")

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_send_text_message('test_userid', 'Hello')
        assert 'Failed to send message' in result


@patch('camel.toolkits.dingtalk._make_dingtalk_request')
def test_get_user_info_error_handling(mock_request):
    """Test getting user info with API error."""
    mock_request.side_effect = Exception("Network error")

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_get_user_info('test_userid')
        assert 'error' in result
        assert 'Failed to get user info' in result['error']


def test_generate_signature():
    """Test signature generation for webhook."""
    from camel.toolkits.dingtalk import _generate_signature

    secret = "test_secret"
    timestamp = "1234567890"

    # Test that signature is generated (exact value depends on implementation)
    signature = _generate_signature(secret, timestamp)
    assert isinstance(signature, str)
    assert len(signature) > 0


@patch('camel.toolkits.dingtalk.requests.post')
def test_webhook_with_signature(mock_post):
    """Test webhook message with signature."""
    mock_response = MagicMock()
    mock_response.json.return_value = {'errcode': 0}
    mock_post.return_value = mock_response

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()

        # Test webhook with custom secret
        result = toolkit.dingtalk_send_webhook_message(
            'Hello with signature!', webhook_secret='custom_secret'
        )
        assert 'Webhook message sent successfully' in result

        # Verify that the request was made with signature parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'timestamp' in call_args[1]['json'] or 'timestamp' in str(
            call_args[0][0]
        )


def test_toolkit_initialization_with_token_failure():
    """Test toolkit initialization when token fetch fails."""
    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.side_effect = Exception("Token fetch failed")

        # Should not raise exception, just log warning
        toolkit = DingtalkToolkit()
        assert toolkit.base_url == "https://oapi.dingtalk.com"


# ========= Tests for new extended features =========


@patch('camel.toolkits.dingtalk._make_dingtalk_request')
def test_send_link_message(mock_request):
    """Test sending link message."""
    mock_request.return_value = {'errcode': 0}

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_send_link_message(
            'test_userid', 'Test Link', 'Click to visit', 'https://example.com'
        )
        assert 'Link message' in result and 'sent successfully' in result


@patch('camel.toolkits.dingtalk._make_dingtalk_request')
def test_send_action_card_message(mock_request):
    """Test sending action card message."""
    mock_request.return_value = {'errcode': 0}

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_send_action_card_message(
            'test_userid',
            'Action Required',
            'Please click the button below',
            'Click Here',
            'https://example.com/action',
        )
        assert 'Action card' in result and 'sent successfully' in result


@patch('camel.toolkits.dingtalk._make_dingtalk_request')
def test_get_user_by_mobile(mock_request):
    """Test getting user by mobile number."""
    expected_data = {
        'userid': 'test_userid',
        'name': 'Test User',
        'mobile': '13800000000',
        'errcode': 0,
    }
    mock_request.return_value = expected_data

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_get_user_by_mobile('13800000000')
        assert result == expected_data


def test_get_user_by_mobile_validation():
    """Test mobile number validation in get_user_by_mobile."""
    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()

        # Test invalid mobile numbers
        invalid_mobiles = [
            '1234567890',  # 10 digits
            '123456789012',  # 12 digits
            '23800000000',  # doesn't start with 1
            '12800000000',  # second digit is 2 (invalid)
            'abc1380000000',  # contains letters
            '138-0000-0000',  # contains hyphens
            '',  # empty string
        ]

        for invalid_mobile in invalid_mobiles:
            result = toolkit.dingtalk_get_user_by_mobile(invalid_mobile)
            assert 'error' in result
            assert 'Invalid mobile number format' in result['error']


@patch('camel.toolkits.dingtalk._make_dingtalk_request')
def test_get_user_by_unionid(mock_request):
    """Test getting user by unionid."""
    expected_data = {
        'userid': 'test_userid',
        'name': 'Test User',
        'unionid': 'test_unionid',
        'errcode': 0,
    }
    mock_request.return_value = expected_data

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_get_user_by_unionid('test_unionid')
        assert result == expected_data


@patch('camel.toolkits.dingtalk._make_dingtalk_request')
def test_get_department_detail(mock_request):
    """Test getting department details."""
    expected_data = {
        'id': 1,
        'name': 'Test Department',
        'parent_id': 0,
        'member_count': 10,
        'errcode': 0,
    }
    mock_request.return_value = expected_data

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_get_department_detail(1)
        assert result == expected_data


@patch('camel.toolkits.dingtalk._make_dingtalk_request')
def test_send_oa_message(mock_request):
    """Test sending OA message."""
    mock_request.return_value = {'errcode': 0}

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_send_oa_message(
            'test_userid',
            'https://example.com',
            'FFBBBBBB',
            'Important Notice',
            'System Update',
            'The system will be updated tonight.',
        )
        assert 'OA message sent successfully' in result


@patch('camel.toolkits.dingtalk._make_dingtalk_request')
def test_get_group_info(mock_request):
    """Test getting group information."""
    expected_data = {
        'chatid': 'test_chatid',
        'name': 'Test Group',
        'owner': 'owner_userid',
        'member_count': 5,
        'errcode': 0,
    }
    mock_request.return_value = expected_data

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_get_group_info('test_chatid')
        assert result == expected_data


@patch('camel.toolkits.dingtalk._make_dingtalk_request')
def test_update_group(mock_request):
    """Test updating group."""
    expected_data = {'errcode': 0}
    mock_request.return_value = expected_data

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_update_group(
            'test_chatid',
            name='New Group Name',
            add_useridlist=['user1', 'user2'],
        )
        assert result == expected_data


@patch('camel.toolkits.dingtalk._make_dingtalk_request')
def test_send_work_notification(mock_request):
    """Test sending work notification to multiple users."""
    mock_request.return_value = {'errcode': 0}

    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        result = toolkit.dingtalk_send_work_notification(
            ['user1', 'user2', 'user3'],
            'Important announcement for all team members.',
        )
        assert 'Work notification sent successfully to 3 users' in result


def test_send_work_notification_validation():
    """Test work notification input validation."""
    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()

        # Test empty user list
        result = toolkit.dingtalk_send_work_notification([], 'test message')
        assert 'userid_list cannot be empty' in result

        # Test too many users
        large_user_list = [f'user{i}' for i in range(101)]
        result = toolkit.dingtalk_send_work_notification(
            large_user_list, 'test message'
        )
        assert 'Cannot send to more than 100 users' in result


def test_extended_tools_count():
    """Test that all new tools are included."""
    with patch(
        'camel.toolkits.dingtalk._get_dingtalk_access_token'
    ) as mock_token:
        mock_token.return_value = "test_access_token"
        toolkit = DingtalkToolkit()
        tools = toolkit.get_tools()

        # Should have 22 tools total
        assert len(tools) == 22

        # Check some specific new tools are present
        tool_names = [tool.func.__name__ for tool in tools]
        assert 'dingtalk_send_link_message' in tool_names
        assert 'dingtalk_send_action_card_message' in tool_names
        assert 'dingtalk_get_user_by_mobile' in tool_names
        assert 'dingtalk_send_work_notification' in tool_names
