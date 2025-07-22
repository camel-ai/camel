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
from slack_sdk.errors import SlackApiError

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


def test_send_slack_message_with_blockkit_blocks(slack_toolkit):
    """Test sending a message with Block Kit blocks."""
    with patch(
        "camel.toolkits.slack_toolkit.SlackToolkit._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client
        mock_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
        }

        # Block Kit blocks with header, section, and action buttons
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Project Update",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Status:* ✅ Complete\n*Progress:* 100%",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Details",
                            "emoji": True,
                        },
                        "value": "view_details",
                        "action_id": "view_details_btn",
                    }
                ],
            },
        ]

        response = slack_toolkit.send_slack_message(
            "Test message", "C1234567890", blocks=blocks
        )

        assert "Message: Test message sent successfully" in response
        mock_client.chat_postMessage.assert_called_once_with(
            channel="C1234567890", text="Test message", blocks=blocks
        )


def test_send_slack_message_with_ephemeral_blockkit_blocks(slack_toolkit):
    """Test sending an ephemeral message with Block Kit blocks."""
    with patch(
        "camel.toolkits.slack_toolkit.SlackToolkit._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client
        mock_client.chat_postEphemeral.return_value = {
            "ok": True,
            "message_ts": "1234567890.123456",
        }

        # Block Kit blocks for ephemeral message
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "This is a private message with Block Kit",
                },
            },
            {
                "type": "input",
                "block_id": "feedback_input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "feedback_text",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Enter feedback...",
                    },
                },
                "label": {
                    "type": "plain_text",
                    "text": "Feedback",
                    "emoji": True,
                },
            },
        ]

        response = slack_toolkit.send_slack_message(
            "Private message", "C1234567890", user="U1234567890", blocks=blocks
        )

        assert "Message: Private message sent successfully" in response
        mock_client.chat_postEphemeral.assert_called_once_with(
            channel="C1234567890",
            text="Private message",
            user="U1234567890",
            blocks=blocks,
        )


def test_send_slack_message_with_blockkit_edge_cases(slack_toolkit):
    """Test sending messages with Block Kit edge cases and error handling."""
    with patch(
        "camel.toolkits.slack_toolkit.SlackToolkit._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client

        # Test empty blocks
        mock_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
        }
        response = slack_toolkit.send_slack_message(
            "Empty blocks test", "C1234567890", blocks=[]
        )
        assert "Message: Empty blocks test sent successfully" in response

        # Test None blocks
        response = slack_toolkit.send_slack_message(
            "None blocks test", "C1234567890", blocks=None
        )
        assert "Message: None blocks test sent successfully" in response

        mock_client.chat_postMessage.side_effect = SlackApiError(
            message="The request to the Slack API failed.",
            response={"error": "invalid_blocks"},
        )

        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}
        ]
        response = slack_toolkit.send_slack_message(
            "Error test", "C1234567890", blocks=blocks
        )
        assert "Error creating conversation: invalid_blocks" in response


def test_make_button(slack_toolkit):
    """Test creating a button element with text_object dict."""
    # Use a dict for the text field to reflect the text_object helper
    text_dict = {"type": "plain_text", "text": "Click me"}
    button = slack_toolkit.make_button(
        text=text_dict,
        action_id="test_button",
        value="button_value",
        style="primary",
    )

    expected = {
        "type": "button",
        "text": {"type": "plain_text", "text": "Click me"},
        "action_id": "test_button",
        "value": "button_value",
        "style": "primary",
    }
    assert button == expected

    # Test without optional parameters, also using a dict for text
    simple_text_dict = {"type": "plain_text", "text": "Simple button"}
    button_simple = slack_toolkit.make_button(
        text=simple_text_dict, action_id="simple_button"
    )

    expected_simple = {
        "type": "button",
        "text": {"type": "plain_text", "text": "Simple button"},
        "action_id": "simple_button",
    }
    assert button_simple == expected_simple


def test_make_select_menu(slack_toolkit):
    """Test creating a select menu element."""
    # Use dicts for the text field to reflect the text_object helper
    option1 = slack_toolkit.make_option(
        {"type": "plain_text", "text": "Option 1"}, "value1"
    )
    option2 = slack_toolkit.make_option(
        {"type": "plain_text", "text": "Option 2"}, "value2"
    )
    options = [option1, option2]

    select_menu = slack_toolkit.make_select_menu(
        action_id="test_select",
        options=options,
        placeholder={"type": "plain_text", "text": "Choose an option"},
    )

    expected = {
        "type": "static_select",
        "action_id": "test_select",
        "options": [
            {
                "text": {"type": "plain_text", "text": "Option 1"},
                "value": "value1",
            },
            {
                "text": {"type": "plain_text", "text": "Option 2"},
                "value": "value2",
            },
        ],
        "placeholder": {"type": "plain_text", "text": "Choose an option"},
        "focus_on_load": False,
    }
    assert select_menu == expected

    # Test without placeholder
    select_menu_no_placeholder = slack_toolkit.make_select_menu(
        action_id="test_select_no_placeholder", options=options
    )

    expected_no_placeholder = {
        "type": "static_select",
        "action_id": "test_select_no_placeholder",
        "options": [
            {
                "text": {"type": "plain_text", "text": "Option 1"},
                "value": "value1",
            },
            {
                "text": {"type": "plain_text", "text": "Option 2"},
                "value": "value2",
            },
        ],
        "focus_on_load": False,
    }
    assert select_menu_no_placeholder == expected_no_placeholder


def test_make_plain_text_input(slack_toolkit):
    """Test creating a plain text input element."""
    text_input = slack_toolkit.make_plain_text_input(
        action_id="test_input",
        multiline=True,
        placeholder={"type": "plain_text", "text": "Enter your message"},
    )

    expected = {
        "type": "plain_text_input",
        "action_id": "test_input",
        "multiline": True,
        "focus_on_load": False,
        "placeholder": {"type": "plain_text", "text": "Enter your message"},
    }
    assert text_input == expected

    # Test single line input without placeholder
    text_input_simple = slack_toolkit.make_plain_text_input(
        action_id="simple_input"
    )

    expected_simple = {
        "type": "plain_text_input",
        "action_id": "simple_input",
        "multiline": False,
        "focus_on_load": False,
    }
    assert text_input_simple == expected_simple


def test_make_date_picker(slack_toolkit):
    """Test creating a date picker element."""
    date_picker = slack_toolkit.make_date_picker(
        action_id="test_date",
        placeholder={"type": "plain_text", "text": "Select a date"},
        initial_date="2024-01-15",
    )

    expected = {
        "type": "datepicker",
        "action_id": "test_date",
        "placeholder": {"type": "plain_text", "text": "Select a date"},
        "initial_date": "2024-01-15",
        "focus_on_load": False,
    }
    assert date_picker == expected

    # Test without optional parameters
    date_picker_simple = slack_toolkit.make_date_picker(
        action_id="simple_date"
    )

    expected_simple = {
        "type": "datepicker",
        "action_id": "simple_date",
        "focus_on_load": False,
    }
    assert date_picker_simple == expected_simple


def test_make_image(slack_toolkit):
    """Test creating an image element."""
    image = slack_toolkit.make_image(
        image_url="https://example.com/image.jpg",
        alt_text="Example image",
    )

    expected = {
        "type": "image",
        "image_url": "https://example.com/image.jpg",
        "alt_text": "Example image",
    }
    assert image == expected

    # Test without title
    image_no_title = slack_toolkit.make_image(
        image_url="https://example.com/image.jpg", alt_text="Example image"
    )

    expected_no_title = {
        "type": "image",
        "image_url": "https://example.com/image.jpg",
        "alt_text": "Example image",
    }
    assert image_no_title == expected_no_title


def test_helper_functions_integration(slack_toolkit):
    """Test integration of helper functions with send_slack_message."""
    with patch(
        "camel.toolkits.slack_toolkit.SlackToolkit._login_slack"
    ) as mock_login:
        mock_client = MagicMock()
        mock_login.return_value = mock_client
        mock_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
        }

        # Create blocks using helper functions
        button = slack_toolkit.make_button(
            text={"type": "plain_text", "text": "Submit"},
            action_id="submit_btn",
            style="primary",
        )

        text_input = slack_toolkit.make_plain_text_input(
            action_id="feedback_input",
            placeholder={"type": "plain_text", "text": "Enter your feedback"},
        )

        options = [
            slack_toolkit.make_option(
                {"type": "plain_text", "text": "Excellent"}, "excellent"
            ),
            slack_toolkit.make_option(
                {"type": "plain_text", "text": "Good"}, "good"
            ),
            slack_toolkit.make_option(
                {"type": "plain_text", "text": "Poor"}, "poor"
            ),
        ]

        select_menu = slack_toolkit.make_select_menu(
            action_id="rating_select",
            options=options,
            placeholder={"type": "plain_text", "text": "Rate your experience"},
        )

        # Create blocks array
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Please provide your feedback:",
                },
            },
            {
                "type": "input",
                "block_id": "feedback_block",
                "element": text_input,
                "label": {"type": "plain_text", "text": "Feedback"},
            },
            {
                "type": "input",
                "block_id": "rating_block",
                "element": select_menu,
                "label": {"type": "plain_text", "text": "Rating"},
            },
            {"type": "actions", "elements": [button]},
        ]

        response = slack_toolkit.send_slack_message(
            "Feedback form", "C1234567890", blocks=blocks
        )

        assert "Message: Feedback form sent successfully" in response
        mock_client.chat_postMessage.assert_called_once_with(
            channel="C1234567890", text="Feedback form", blocks=blocks
        )
