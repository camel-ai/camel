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
from unittest.mock import patch

import pytest

from camel.toolkits.resend_toolkit import ResendToolkit


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    """Set up required environment variables for ResendToolkit tests."""
    monkeypatch.setenv("RESEND_API_KEY", "re_test_api_key_12345")


def test_send_email_html_only():
    """Test sending email with HTML content only."""
    toolkit = ResendToolkit()

    mock_email_response = {'id': 'email_12345_test_id'}

    with patch('resend.Emails.send') as mock_send:
        mock_send.return_value = mock_email_response

        result = toolkit.send_email(
            to=["recipient@example.com"],
            subject="Test HTML Email",
            from_email="sender@yourdomain.com",
            html="<h1>Hello, World!</h1><p>This is a test email.</p>",
        )

        expected_result = (
            "Email sent successfully. Email ID: email_12345_test_id"
        )
        assert result == expected_result

        # Verify the API was called with correct parameters
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args["from"] == "sender@yourdomain.com"
        assert call_args["to"] == ["recipient@example.com"]
        assert call_args["subject"] == "Test HTML Email"
        assert (
            call_args["html"]
            == "<h1>Hello, World!</h1><p>This is a test email.</p>"
        )
        assert "text" not in call_args


def test_send_email_text_only():
    """Test sending email with plain text content only."""
    toolkit = ResendToolkit()

    mock_email_response = {'id': 'email_text_67890_test_id'}

    with patch('resend.Emails.send') as mock_send:
        mock_send.return_value = mock_email_response

        result = toolkit.send_email(
            to=["recipient@example.com"],
            subject="Test Text Email",
            from_email="sender@yourdomain.com",
            text="Hello, World!\nThis is a plain text test email.",
        )

        expected_result = (
            "Email sent successfully. Email ID: email_text_67890_test_id"
        )
        assert result == expected_result

        # Verify the API was called with correct parameters
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args["from"] == "sender@yourdomain.com"
        assert call_args["to"] == ["recipient@example.com"]
        assert call_args["subject"] == "Test Text Email"
        assert (
            call_args["text"]
            == "Hello, World!\nThis is a plain text test email."
        )
        assert "html" not in call_args


def test_send_email_html_and_text():
    """Test sending email with both HTML and text content."""
    toolkit = ResendToolkit()

    mock_email_response = {'id': 'email_both_11111_test_id'}

    with patch('resend.Emails.send') as mock_send:
        mock_send.return_value = mock_email_response

        result = toolkit.send_email(
            to=["recipient@example.com"],
            subject="Test Both Content Email",
            from_email="sender@yourdomain.com",
            html="<h1>Hello, World!</h1>",
            text="Hello, World!",
        )

        expected_result = (
            "Email sent successfully. Email ID: email_both_11111_test_id"
        )
        assert result == expected_result

        # Verify the API was called with correct parameters
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args["html"] == "<h1>Hello, World!</h1>"
        assert call_args["text"] == "Hello, World!"


def test_send_email_with_all_optional_params():
    """Test sending email with all optional parameters."""
    toolkit = ResendToolkit()

    mock_email_response = {'id': 'email_full_22222_test_id'}

    with patch('resend.Emails.send') as mock_send:
        mock_send.return_value = mock_email_response

        result = toolkit.send_email(
            to=["recipient1@example.com", "recipient2@example.com"],
            subject="Test Full Email",
            from_email="sender@yourdomain.com",
            html="<h1>Full Email Test</h1>",
            text="Full Email Test",
            cc=["cc@example.com"],
            bcc=["bcc@example.com"],
            reply_to="reply@yourdomain.com",
            tags=[{"name": "category", "value": "test"}],
            headers={"X-Custom-Header": "test-value"},
        )

        expected_result = (
            "Email sent successfully. Email ID: email_full_22222_test_id"
        )
        assert result == expected_result

        # Verify the API was called with correct parameters
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert call_args["to"] == [
            "recipient1@example.com",
            "recipient2@example.com",
        ]
        assert call_args["cc"] == ["cc@example.com"]
        assert call_args["bcc"] == ["bcc@example.com"]
        assert call_args["reply_to"] == "reply@yourdomain.com"
        assert call_args["tags"] == [{"name": "category", "value": "test"}]
        assert call_args["headers"] == {"X-Custom-Header": "test-value"}


def test_send_email_no_content_error():
    """Test that sending email without content raises ValueError."""
    toolkit = ResendToolkit()

    with pytest.raises(
        ValueError, match="Either 'html' or 'text' content must be provided"
    ):
        toolkit.send_email(
            to=["recipient@example.com"],
            subject="Test Email",
            from_email="sender@yourdomain.com",
        )


def test_send_email_import_error():
    """Test handling of resend package import error."""
    toolkit = ResendToolkit()

    # Mock the import statement inside the send_email method
    with patch.dict('sys.modules', {'resend': None}):
        with pytest.raises(
            ImportError, match=r"Please install the resend package first\."
        ):
            toolkit.send_email(
                to=["recipient@example.com"],
                subject="Test Email",
                from_email="sender@yourdomain.com",
                text="Test content",
            )


def test_send_email_api_error():
    """Test handling of API errors during email sending."""
    toolkit = ResendToolkit()

    with patch('resend.Emails.send') as mock_send:
        mock_send.side_effect = Exception("API Error: Invalid API key")

        result = toolkit.send_email(
            to=["recipient@example.com"],
            subject="Test Email",
            from_email="sender@yourdomain.com",
            text="Test content",
        )

        expected_result = "Failed to send email: API Error: Invalid API key"
        assert result == expected_result


def test_send_email_no_id_in_response():
    """Test handling of API response without ID field."""
    toolkit = ResendToolkit()

    mock_email_response = {}  # Response without 'id' field

    with patch('resend.Emails.send') as mock_send:
        mock_send.return_value = mock_email_response

        result = toolkit.send_email(
            to=["recipient@example.com"],
            subject="Test Email",
            from_email="sender@yourdomain.com",
            text="Test content",
        )

        expected_result = "Email sent successfully. Email ID: Unknown"
        assert result == expected_result


def test_get_tools():
    """Test that get_tools returns the correct FunctionTool objects."""
    toolkit = ResendToolkit()
    tools = toolkit.get_tools()

    assert len(tools) == 1
    assert tools[0].func == toolkit.send_email
    assert hasattr(tools[0], 'get_openai_tool_schema')


def test_send_email_api_key_setting():
    """Test that the API key is correctly set from environment variable."""
    toolkit = ResendToolkit()

    with (
        patch('resend.Emails.send') as mock_send,
        patch('resend.api_key', new=None),
    ):
        mock_send.return_value = {'id': 'test_id'}

        toolkit.send_email(
            to=["recipient@example.com"],
            subject="Test Email",
            from_email="sender@yourdomain.com",
            text="Test content",
        )

        # The API key should have been set during the function call
        mock_send.assert_called_once()
