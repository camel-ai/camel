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

from camel.toolkits import SlackToolkit


@pytest.fixture
def slack_toolkit():
    return SlackToolkit()


def test_create_slack_channel(slack_toolkit):
    with patch(
        'camel.toolkits.slack_toolkit.SlackToolkit._login_slack'
    ) as mock_login_slack:
        mock_client = MagicMock()
        mock_login_slack.return_value = mock_client

        mock_response = {'channel': {'id': 'fake_channel_id'}}
        mock_client.conversations_create.return_value = mock_response
        mock_client.conversations_archive.return_value = {
            'fake_response_key': 'fake_response_value'
        }

        result = slack_toolkit.create_slack_channel(
            'test_channel', is_private=True
        )

        assert result == "{'fake_response_key': 'fake_response_value'}"
        mock_client.conversations_create.assert_called_once_with(
            name='test_channel', is_private=True
        )
        mock_client.conversations_archive.assert_called_once_with(
            channel='fake_channel_id'
        )


def test_join_slack_channel(slack_toolkit):
    with patch(
        "camel.toolkits.slack_toolkit.SlackToolkit._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client
        mock_client.conversations_join.return_value = {}
        response = slack_toolkit.join_slack_channel("123")
        assert response == "{}"


def test_leave_slack_channel(slack_toolkit):
    with patch(
        "camel.toolkits.slack_toolkit.SlackToolkit._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client
        mock_client.conversations_leave.return_value = {}
        response = slack_toolkit.leave_slack_channel("123")
        assert response == "{}"


def test_get_slack_channel_information(slack_toolkit):
    with patch(
        "camel.toolkits.slack_toolkit.SlackToolkit._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client
        mock_client.conversations_list.return_value = {
            "channels": [
                {
                    "id": "123",
                    "name": "test_channel",
                    "created": 123,
                    "num_members": 5,
                }
            ]
        }
        response = slack_toolkit.get_slack_channel_information()
        expected_result = """[{"id": "123", "name": "test_channel", "creat"""
        assert expected_result in response


def test_get_slack_channel_message(slack_toolkit):
    with patch(
        "camel.toolkits.slack_toolkit.SlackToolkit._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client
        mock_client.conversations_history.return_value = {
            "messages": [
                {"user": "user_id", "text": "test_message", "ts": "123"}
            ]
        }
        response = slack_toolkit.get_slack_channel_message("123")
        expected_result = (
            '[{"user": "user_id", "text": "test_message", "ts": "123"}]'
        )
        assert response == expected_result


def test_send_slack_message(slack_toolkit):
    with patch(
        "camel.toolkits.slack_toolkit.SlackToolkit._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client
        mock_client.chat_postMessage.return_value = {}
        response = slack_toolkit.send_slack_message("test_message", "123")
        assert (
            response
            == "Message: test_message sent successfully, got response: {}"
        )


def test_delete_slack_message(slack_toolkit):
    with patch(
        "camel.toolkits.slack_toolkit.SlackToolkit._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client
        mock_client.chat_delete.return_value = {}
        response = slack_toolkit.delete_slack_message("123", "123")
        assert response == "{}"


def test_get_slack_user_list(slack_toolkit):
    with patch(
        "camel.toolkits.slack_toolkit.SlackToolkit._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client
        mock_client.users_list.return_value = {
            "members": [{"id": "123", "name": "test_user"}]
        }
        response = slack_toolkit.get_slack_user_list()
        assert response == '[{"id": "123", "name": "test_user"}]'


def test_get_slack_user_info(slack_toolkit):
    with patch(
        "camel.toolkits.slack_toolkit.SlackToolkit._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client
        mock_client.users_info.return_value = {
            "user": {"id": "123", "name": "test_user"}
        }

        response = slack_toolkit.get_slack_user_info("123")
        expected_response = '{"user": {"id": "123", "name": "test_user"}}'
        assert response == expected_response
