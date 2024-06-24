# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from unittest.mock import MagicMock, patch

from camel.toolkits.functions.slack_functions import (
    create_slack_channel,
    delete_slack_message,
    get_slack_channel_information,
    get_slack_channel_message,
    join_slack_channel,
    leave_slack_channel,
    send_slack_message,
)


def test_create_slack_channel():
    with patch(
        'camel.toolkits.functions.slack_functions._login_slack'
    ) as mock_login_slack:
        mock_client = MagicMock()
        mock_login_slack.return_value = mock_client

        mock_response = {'channel': {'id': 'fake_channel_id'}}
        mock_client.conversations_create.return_value = mock_response
        mock_client.conversations_archive.return_value = {
            'fake_response_key': 'fake_response_value'
        }

        result = create_slack_channel('test_channel', is_private=True)

        assert result == "{'fake_response_key': 'fake_response_value'}"
        mock_client.conversations_create.assert_called_once_with(
            name='test_channel', is_private=True
        )
        mock_client.conversations_archive.assert_called_once_with(
            channel='fake_channel_id'
        )


def test_join_slack_channel():
    with patch(
        "camel.toolkits.functions.slack_functions._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client
        mock_client.conversations_join.return_value = {}
        response = join_slack_channel("123")
        assert response == "{}"


def test_leave_slack_channel():
    with patch(
        "camel.toolkits.functions.slack_functions._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client
        mock_client.conversations_leave.return_value = {}
        response = leave_slack_channel("123")
        assert response == "{}"


def test_get_slack_channel_information():
    with patch(
        "camel.toolkits.functions.slack_functions._login_slack"
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
        response = get_slack_channel_information()
        expected_result = """[{"id": "123", "name": "test_channel", "creat"""
        assert expected_result in response


def test_get_slack_channel_message():
    with patch(
        "camel.toolkits.functions.slack_functions._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client
        mock_client.conversations_history.return_value = {
            "messages": [
                {"user": "user_id", "text": "test_message", "ts": "123"}
            ]
        }
        response = get_slack_channel_message("123")
        expected_result = (
            '[{"user": "user_id", "text": "test_message", "ts": "123"}]'
        )
        assert response == expected_result


def test_send_slack_message():
    with patch(
        "camel.toolkits.functions.slack_functions._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client
        mock_client.chat_postMessage.return_value = {}
        response = send_slack_message("test_message", "123")
        assert response == "{}"


def test_delete_slack_message():
    with patch(
        "camel.toolkits.functions.slack_functions._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client
        mock_client.chat_delete.return_value = {}
        response = delete_slack_message("123", "123")
        assert response == "{}"
