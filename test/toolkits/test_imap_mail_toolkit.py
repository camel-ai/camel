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

import imaplib
import os
import smtplib
import unittest
from unittest.mock import MagicMock, patch

from camel.toolkits import IMAPMailToolkit


class TestIMAPMailToolkit(unittest.TestCase):
    r"""Test cases for IMAP Mail Toolkit."""

    def setUp(self):
        r"""Set up test fixtures."""
        # Mock environment variables
        self.env_patcher = patch.dict(
            os.environ,
            {
                'IMAP_SERVER': 'imap.test.com',
                'SMTP_SERVER': 'smtp.test.com',
                'EMAIL_USERNAME': 'test@test.com',
                'EMAIL_PASSWORD': 'test_password',
            },
        )
        self.env_patcher.start()

        # Create toolkit instance
        self.toolkit = IMAPMailToolkit()

    def tearDown(self):
        r"""Clean up test fixtures."""
        self.env_patcher.stop()

    @patch('camel.toolkits.imap_mail_toolkit.imaplib.IMAP4_SSL')
    def test_get_imap_connection_success(self, mock_imap_ssl):
        r"""Test successful IMAP connection."""
        # Setup mock
        mock_imap = MagicMock()
        mock_imap_ssl.return_value = mock_imap

        # Call method
        result = self.toolkit._get_imap_connection()

        # Assertions
        self.assertEqual(result, mock_imap)
        mock_imap_ssl.assert_called_once_with('imap.test.com', 993)
        mock_imap.login.assert_called_once_with(
            'test@test.com', 'test_password'
        )

    @patch('camel.toolkits.imap_mail_toolkit.imaplib.IMAP4_SSL')
    def test_get_imap_connection_failure(self, mock_imap_ssl):
        r"""Test IMAP connection failure."""
        # Setup mock to raise exception
        mock_imap_ssl.side_effect = imaplib.IMAP4.error("Connection failed")

        # Call method and expect exception
        # (the actual exception, not ConnectionError)
        with self.assertRaises(imaplib.IMAP4.error):
            self.toolkit._get_imap_connection()

    @patch('camel.toolkits.imap_mail_toolkit.smtplib.SMTP')
    def test_get_smtp_connection_success(self, mock_smtp):
        r"""Test successful SMTP connection."""
        # Setup mock
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance

        # Call method
        result = self.toolkit._get_smtp_connection()

        # Assertions
        self.assertEqual(result, mock_smtp_instance)
        mock_smtp.assert_called_once_with('smtp.test.com', 587)
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with(
            'test@test.com', 'test_password'
        )

    @patch('camel.toolkits.imap_mail_toolkit.smtplib.SMTP')
    def test_get_smtp_connection_failure(self, mock_smtp):
        r"""Test SMTP connection failure."""
        # Setup mock to raise exception
        mock_smtp.side_effect = smtplib.SMTPException("Connection failed")

        # Call method and expect exception
        with self.assertRaises(smtplib.SMTPException):
            self.toolkit._get_smtp_connection()

    @patch.object(IMAPMailToolkit, '_get_imap_connection')
    def test_fetch_emails_success(self, mock_get_imap):
        r"""Test successful email fetching."""
        # Setup mock
        mock_imap = MagicMock()
        mock_get_imap.return_value = mock_imap
        mock_imap.select.return_value = ("OK", [b""])

        # Mock search results
        mock_imap.search.return_value = ("OK", [b"1"])
        mock_imap.fetch.return_value = ("OK", [(b"1", b"raw_email_data")])

        # Mock email message
        mock_message = MagicMock()
        mock_message.get.side_effect = lambda x, default="": {
            "Subject": "Test Subject",
            "From": "test@example.com",
            "To": "recipient@example.com",
            "Date": "Wed, 01 Jan 2024 00:00:00 +0000",
        }.get(x, default)

        with patch(
            'camel.toolkits.imap_mail_toolkit.email.message_from_bytes',
            return_value=mock_message,
        ):
            with patch.object(
                self.toolkit,
                '_extract_email_body',
                return_value={"plain": "Test body"},
            ):
                # Call method
                result = self.toolkit.fetch_emails(limit=1)

                # Assertions
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]["subject"], "Test Subject")
                self.assertEqual(result[0]["from"], "test@example.com")
                mock_imap.select.assert_called_once_with(
                    "INBOX", readonly=True
                )
                mock_imap.search.assert_called_once()
                mock_imap.fetch.assert_called_once_with(b"1", "(BODY.PEEK[])")

    @patch.object(IMAPMailToolkit, '_get_imap_connection')
    def test_fetch_emails_with_filters(self, mock_get_imap):
        r"""Test email fetching with filters."""
        # Setup mock
        mock_imap = MagicMock()
        mock_get_imap.return_value = mock_imap
        mock_imap.select.return_value = ("OK", [b""])
        mock_imap.search.return_value = ("OK", [b"1 2 3"])
        mock_imap.fetch.return_value = ("OK", [(b"1", b"raw_email_data")])

        # Mock email message
        mock_message = MagicMock()
        mock_message.get.return_value = "Test"

        with patch(
            'camel.toolkits.imap_mail_toolkit.email.message_from_bytes',
            return_value=mock_message,
        ):
            with patch.object(
                self.toolkit,
                '_extract_email_body',
                return_value={"plain": "Test body"},
            ):
                # Call method with filters
                result = self.toolkit.fetch_emails(
                    unread_only=True,
                    sender_filter="test@example.com",
                    subject_filter="Test Subject",
                )

                # Assertions
                self.assertIsInstance(result, list)
                mock_imap.select.assert_called_once_with(
                    "INBOX", readonly=True
                )
                # Check that search was called with proper criteria
                search_call = mock_imap.search.call_args[0]
                search_string = search_call[1]
                self.assertIn("UNSEEN", search_string)
                self.assertIn("FROM", search_string)
                self.assertIn("SUBJECT", search_string)

    @patch.object(IMAPMailToolkit, '_get_imap_connection')
    def test_fetch_emails_search_failure(self, mock_get_imap):
        r"""Test email fetching with search failure."""
        # Setup mock
        mock_imap = MagicMock()
        mock_get_imap.return_value = mock_imap
        mock_imap.select.return_value = ("OK", [b""])
        mock_imap.search.return_value = ("NO", [b"Error"])

        # Call method and expect exception
        with self.assertRaises(ConnectionError):
            self.toolkit.fetch_emails()

    @patch.object(IMAPMailToolkit, '_get_imap_connection')
    def test_get_email_by_id_success(self, mock_get_imap):
        r"""Test successful email retrieval by ID."""
        # Setup mock
        mock_imap = MagicMock()
        mock_get_imap.return_value = mock_imap
        mock_imap.select.return_value = ("OK", [b""])
        mock_imap.fetch.return_value = ("OK", [(b"1", b"raw_email_data")])

        # Mock email message
        mock_message = MagicMock()
        mock_message.get.side_effect = lambda x, default="": {
            "Subject": "Test Subject",
            "From": "test@example.com",
            "To": "recipient@example.com",
            "Date": "Wed, 01 Jan 2024 00:00:00 +0000",
            "Message-ID": "test-id@example.com",
            "In-Reply-To": "",
            "References": "",
            "X-Priority": "3",
        }.get(x, default)

        with patch(
            'camel.toolkits.imap_mail_toolkit.email.message_from_bytes',
            return_value=mock_message,
        ):
            with patch.object(
                self.toolkit,
                '_extract_email_body',
                return_value={"plain": "Test body"},
            ):
                # Call method
                result = self.toolkit.get_email_by_id("123")

                # Assertions
                self.assertEqual(result["id"], "123")
                self.assertEqual(result["subject"], "Test Subject")
                self.assertEqual(result["from"], "test@example.com")
                mock_imap.select.assert_called_once_with(
                    "INBOX", readonly=True
                )
                mock_imap.fetch.assert_called_once_with("123", "(BODY.PEEK[])")

    @patch.object(IMAPMailToolkit, '_get_imap_connection')
    def test_get_email_by_id_fetch_failure(self, mock_get_imap):
        r"""Test email retrieval with fetch failure."""
        # Setup mock
        mock_imap = MagicMock()
        mock_get_imap.return_value = mock_imap
        mock_imap.select.return_value = ("OK", [b""])
        mock_imap.fetch.return_value = ("NO", [b"Error"])

        # Call method and expect exception
        with self.assertRaises(ConnectionError):
            self.toolkit.get_email_by_id("123")

    @patch.object(IMAPMailToolkit, '_get_smtp_connection')
    def test_send_email_success(self, mock_get_smtp):
        r"""Test successful email sending."""
        # Setup mock
        mock_smtp = MagicMock()
        mock_get_smtp.return_value = mock_smtp

        # Call method
        result = self.toolkit.send_email(
            to_recipients=["recipient@example.com"],
            subject="Test Subject",
            body="Test Body",
            html_body="<p>Test HTML</p>",
        )

        # Assertions
        self.assertIn("Email sent successfully", result)
        mock_smtp.send_message.assert_called_once()

    @patch.object(IMAPMailToolkit, '_get_smtp_connection')
    def test_send_email_with_cc_bcc(self, mock_get_smtp):
        r"""Test email sending with CC and BCC."""
        # Setup mock
        mock_smtp = MagicMock()
        mock_get_smtp.return_value = mock_smtp

        # Call method
        result = self.toolkit.send_email(
            to_recipients=["recipient@example.com"],
            subject="Test Subject",
            body="Test Body",
            cc_recipients=["cc@example.com"],
            bcc_recipients=["bcc@example.com"],
        )

        # Assertions
        self.assertIn("Email sent successfully", result)
        # Check that send_message was called with all recipients
        call_args = mock_smtp.send_message.call_args
        self.assertIn("recipient@example.com", call_args[1]["to_addrs"])
        self.assertIn("cc@example.com", call_args[1]["to_addrs"])
        self.assertIn("bcc@example.com", call_args[1]["to_addrs"])

    @patch.object(IMAPMailToolkit, '_get_smtp_connection')
    def test_send_email_failure(self, mock_get_smtp):
        r"""Test email sending failure."""
        # Setup mock to raise exception
        mock_get_smtp.side_effect = ConnectionError("SMTP connection failed")

        # Call method and expect exception
        with self.assertRaises(ConnectionError):
            self.toolkit.send_email(
                to_recipients=["recipient@example.com"],
                subject="Test Subject",
                body="Test Body",
            )

    @patch.object(IMAPMailToolkit, 'get_email_by_id')
    @patch.object(IMAPMailToolkit, 'send_email')
    def test_reply_to_email_success(self, mock_send_email, mock_get_email):
        r"""Test successful email reply."""
        # Setup mocks
        mock_get_email.return_value = {
            "subject": "Original Subject",
            "from": "original@example.com",
            "message_id": "original-id@example.com",
        }
        mock_send_email.return_value = "Reply sent successfully"

        # Call method
        result = self.toolkit.reply_to_email(
            original_email_id="123", reply_body="Reply content"
        )

        # Assertions
        self.assertIn("Reply sent successfully", result)
        mock_get_email.assert_called_once_with("123", "INBOX")
        mock_send_email.assert_called_once()

    @patch.object(IMAPMailToolkit, 'get_email_by_id')
    def test_reply_to_email_no_original(self, mock_get_email):
        r"""Test email reply when original email not found."""
        # Setup mock to raise exception
        mock_get_email.side_effect = ConnectionError("Email not found")

        # Call method and expect exception
        with self.assertRaises(ConnectionError):
            self.toolkit.reply_to_email(
                original_email_id="123", reply_body="Reply content"
            )

    @patch.object(IMAPMailToolkit, '_get_imap_connection')
    def test_move_email_to_folder_success(self, mock_get_imap):
        r"""Test successful email moving."""
        # Setup mock
        mock_imap = MagicMock()
        mock_get_imap.return_value = mock_imap
        mock_imap.select.return_value = ("OK", [b""])
        mock_imap.copy.return_value = ("OK", [b""])
        mock_imap.store.return_value = ("OK", [b""])
        mock_imap.expunge.return_value = ("OK", [b""])

        # Call method
        result = self.toolkit.move_email_to_folder(
            email_id="123", target_folder="Archive", source_folder="INBOX"
        )

        # Assertions
        self.assertIn("Email 123 moved from INBOX to Archive", result)
        mock_imap.select.assert_called_once_with("INBOX")
        mock_imap.copy.assert_called_once_with("123", "Archive")
        mock_imap.store.assert_called_once_with("123", '+FLAGS', '\\Deleted')
        mock_imap.expunge.assert_called_once()

    @patch.object(IMAPMailToolkit, '_get_imap_connection')
    def test_move_email_to_folder_failure(self, mock_get_imap):
        r"""Test email moving failure."""
        # Setup mock to raise exception
        mock_get_imap.side_effect = ConnectionError("IMAP connection failed")

        # Call method and expect exception
        with self.assertRaises(ConnectionError):
            self.toolkit.move_email_to_folder(
                email_id="123", target_folder="Archive"
            )

    @patch.object(IMAPMailToolkit, '_get_imap_connection')
    def test_delete_email_success(self, mock_get_imap):
        r"""Test successful email deletion."""
        # Setup mock
        mock_imap = MagicMock()
        mock_get_imap.return_value = mock_imap
        mock_imap.select.return_value = ("OK", [b""])
        mock_imap.copy.return_value = ("OK", [b""])
        mock_imap.store.return_value = ("OK", [b""])
        mock_imap.expunge.return_value = ("OK", [b""])

        # Call method
        result = self.toolkit.delete_email("123", permanent=False)

        # Assertions
        self.assertIn("Email 123 moved to trash", result)
        mock_imap.select.assert_called_once_with("INBOX")
        mock_imap.store.assert_called_once_with("123", '+FLAGS', '\\Deleted')
        mock_imap.expunge.assert_called_once()

    @patch.object(IMAPMailToolkit, '_get_imap_connection')
    def test_delete_email_permanent(self, mock_get_imap):
        r"""Test permanent email deletion."""
        # Setup mock
        mock_imap = MagicMock()
        mock_get_imap.return_value = mock_imap
        mock_imap.select.return_value = ("OK", [b""])
        mock_imap.store.return_value = ("OK", [b""])
        mock_imap.expunge.return_value = ("OK", [b""])

        # Call method
        result = self.toolkit.delete_email("123", permanent=True)

        # Assertions
        self.assertIn("Email 123 permanently deleted", result)
        mock_imap.select.assert_called_once_with("INBOX")
        mock_imap.store.assert_called_once_with("123", '+FLAGS', '\\Deleted')
        mock_imap.expunge.assert_called_once()

    @patch.object(IMAPMailToolkit, '_get_imap_connection')
    def test_delete_email_copy_failure_fallback(self, mock_get_imap):
        r"""Test soft delete fallback when trash copy fails."""
        # Setup mock
        mock_imap = MagicMock()
        mock_get_imap.return_value = mock_imap
        mock_imap.select.return_value = ("OK", [b""])
        mock_imap.copy.return_value = ("NO", [b"Error"])
        mock_imap.store.return_value = ("OK", [b""])
        mock_imap.expunge.return_value = ("OK", [b""])

        # Call method
        result = self.toolkit.delete_email("123", permanent=False)

        # Assertions
        self.assertIn("Email 123 marked as deleted", result)
        mock_imap.copy.assert_called_once_with("123", "Trash")
        mock_imap.store.assert_called_once_with("123", '+FLAGS', '\\Deleted')
        mock_imap.expunge.assert_called_once()

    @patch.object(IMAPMailToolkit, '_get_imap_connection')
    def test_delete_email_failure(self, mock_get_imap):
        r"""Test email deletion failure."""
        # Setup mock to raise exception
        mock_get_imap.side_effect = ConnectionError("IMAP connection failed")

        # Call method and expect exception
        with self.assertRaises(ConnectionError):
            self.toolkit.delete_email("123")

    def test_extract_email_body_plain_text(self):
        r"""Test email body extraction for plain text."""
        # Create mock email message
        mock_message = MagicMock()
        mock_message.is_multipart.return_value = False
        mock_message.get_content_type.return_value = "text/plain"
        mock_message.get_payload.return_value = b"Plain text content"

        # Call method
        result = self.toolkit._extract_email_body(mock_message)

        # Assertions
        self.assertEqual(result["plain"], "Plain text content")
        self.assertEqual(result["html"], "")

    def test_extract_email_body_html(self):
        r"""Test email body extraction for HTML."""
        # Create mock email message
        mock_message = MagicMock()
        mock_message.is_multipart.return_value = False
        mock_message.get_content_type.return_value = "text/html"
        mock_message.get_payload.return_value = b"<p>HTML content</p>"

        # Call method
        result = self.toolkit._extract_email_body(mock_message)

        # Assertions
        self.assertEqual(result["plain"], "")
        self.assertEqual(result["html"], "<p>HTML content</p>")

    def test_extract_email_body_multipart(self):
        r"""Test email body extraction for multipart message."""
        # Create mock email message
        mock_message = MagicMock()
        mock_message.is_multipart.return_value = True

        # Create mock parts
        mock_part1 = MagicMock()
        mock_part1.get_content_type.return_value = "text/plain"
        mock_part1.get.return_value = "inline"  # Not an attachment
        mock_part1.get_payload.return_value = b"Plain text content"

        mock_part2 = MagicMock()
        mock_part2.get_content_type.return_value = "text/html"
        mock_part2.get.return_value = "inline"  # Not an attachment
        mock_part2.get_payload.return_value = b"<p>HTML content</p>"

        # Mock the main message to have no content disposition
        mock_message.get.return_value = None
        mock_message.walk.return_value = [mock_message, mock_part1, mock_part2]

        # Call method
        result = self.toolkit._extract_email_body(mock_message)

        # Assertions
        self.assertEqual(result["plain"], "Plain text content")
        self.assertEqual(result["html"], "<p>HTML content</p>")

    def test_get_tools(self):
        r"""Test getting available tools."""
        # Call method
        tools = self.toolkit.get_tools()

        # Assertions
        self.assertIsInstance(tools, list)
        self.assertEqual(len(tools), 6)  # 6 public methods

        # Check that all expected tools are present
        tool_names = [tool.func.__name__ for tool in tools]
        expected_tools = [
            'fetch_emails',
            'get_email_by_id',
            'send_email',
            'reply_to_email',
            'move_email_to_folder',
            'delete_email',
        ]

        for expected_tool in expected_tools:
            self.assertIn(expected_tool, tool_names)

    def test_toolkit_initialization_with_credentials(self):
        r"""Test toolkit initialization with direct credentials."""
        # Create toolkit with direct credentials
        toolkit = IMAPMailToolkit(
            imap_server="custom.imap.com",
            smtp_server="custom.smtp.com",
            username="custom@example.com",
            password="custom_password",
        )

        # Assertions
        self.assertEqual(toolkit.imap_server, "custom.imap.com")
        self.assertEqual(toolkit.smtp_server, "custom.smtp.com")
        self.assertEqual(toolkit.username, "custom@example.com")
        self.assertEqual(toolkit.password, "custom_password")

    def test_get_imap_connection_missing_credentials(self):
        r"""Test IMAP connection with missing credentials."""
        # Test missing IMAP server - must clear envs
        with patch.dict(os.environ, {}, clear=True):
            toolkit = IMAPMailToolkit(
                imap_server=None,
                smtp_server="smtp.test.com",
                username="test@test.com",
                password="test_password",
            )

            with self.assertRaises(ValueError) as context:
                toolkit._get_imap_connection()

            self.assertIn("IMAP server", str(context.exception))

        # Test missing username - must clear envs
        with patch.dict(os.environ, {}, clear=True):
            toolkit = IMAPMailToolkit(
                imap_server="imap.test.com",
                smtp_server="smtp.test.com",
                username=None,
                password="test_password",
            )

            with self.assertRaises(ValueError) as context:
                toolkit._get_imap_connection()

            self.assertIn("username", str(context.exception))

        # Test missing password - must clear envs
        with patch.dict(os.environ, {}, clear=True):
            toolkit = IMAPMailToolkit(
                imap_server="imap.test.com",
                smtp_server="smtp.test.com",
                username="test@test.com",
                password=None,
            )

            with self.assertRaises(ValueError) as context:
                toolkit._get_imap_connection()

            self.assertIn("password", str(context.exception))

    def test_get_smtp_connection_missing_credentials(self):
        r"""Test SMTP connection with missing credentials."""
        # Test missing SMTP server - must clear envs
        with patch.dict(os.environ, {}, clear=True):
            toolkit = IMAPMailToolkit(
                imap_server="imap.test.com",
                smtp_server=None,
                username="test@test.com",
                password="test_password",
            )

            with self.assertRaises(ValueError) as context:
                toolkit._get_smtp_connection()

            self.assertIn("SMTP server", str(context.exception))

        # Test missing username - must clear envs
        with patch.dict(os.environ, {}, clear=True):
            toolkit = IMAPMailToolkit(
                imap_server="imap.test.com",
                smtp_server="smtp.test.com",
                username=None,
                password="test_password",
            )

            with self.assertRaises(ValueError) as context:
                toolkit._get_smtp_connection()

            self.assertIn("username", str(context.exception))

        # Test missing password - must clear envs
        with patch.dict(os.environ, {}, clear=True):
            toolkit = IMAPMailToolkit(
                imap_server="imap.test.com",
                smtp_server="smtp.test.com",
                username="test@test.com",
                password=None,
            )

            with self.assertRaises(ValueError) as context:
                toolkit._get_smtp_connection()

            self.assertIn("password", str(context.exception))


if __name__ == '__main__':
    unittest.main()
