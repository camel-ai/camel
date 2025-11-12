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

import base64
from unittest.mock import MagicMock, patch

import pytest

from camel.toolkits import GmailToolkit


@pytest.fixture
def mock_gmail_service():
    with patch('googleapiclient.discovery.build') as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_users = MagicMock()
        mock_service.users.return_value = mock_users

        mock_messages = MagicMock()
        mock_users.messages.return_value = mock_messages

        mock_drafts = MagicMock()
        mock_users.drafts.return_value = mock_drafts

        mock_threads = MagicMock()
        mock_users.threads.return_value = mock_threads

        mock_labels = MagicMock()
        mock_users.labels.return_value = mock_labels

        mock_attachments = MagicMock()
        mock_messages.attachments.return_value = mock_attachments

        yield mock_service


@pytest.fixture
def mock_people_service():
    with patch('googleapiclient.discovery.build') as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_people = MagicMock()
        mock_service.people.return_value = mock_people

        mock_connections = MagicMock()
        mock_people.connections.return_value = mock_connections

        yield mock_service


@pytest.fixture
def gmail_toolkit(mock_gmail_service, mock_people_service):
    # Create a mock credentials object to avoid OAuth authentication
    mock_credentials = MagicMock()
    mock_credentials.valid = True
    mock_credentials.expired = False

    with (
        patch.dict(
            'os.environ',
            {
                'GOOGLE_CLIENT_ID': 'mock_client_id',
                'GOOGLE_CLIENT_SECRET': 'mock_client_secret',
                'GOOGLE_REFRESH_TOKEN': 'mock_refresh_token',
            },
        ),
        patch.object(
            GmailToolkit,
            '_authenticate',
            return_value=mock_credentials,
        ),
        patch.object(
            GmailToolkit,
            '_get_gmail_service',
            return_value=mock_gmail_service,
        ),
        patch.object(
            GmailToolkit,
            '_get_people_service',
            return_value=mock_people_service,
        ),
    ):
        toolkit = GmailToolkit()
        toolkit.gmail_service = mock_gmail_service
        toolkit.people_service = mock_people_service
        yield toolkit


def test_send_email(gmail_toolkit, mock_gmail_service):
    """Test sending an email successfully."""
    send_mock = MagicMock()
    mock_gmail_service.users().messages().send.return_value = send_mock
    send_mock.execute.return_value = {'id': 'msg123', 'threadId': 'thread123'}

    result = gmail_toolkit.send_email(
        to='test@example.com', subject='Test Subject', body='Test Body'
    )

    assert result['success'] is True
    assert result['message_id'] == 'msg123'
    assert result['thread_id'] == 'thread123'
    assert result['message'] == 'Email sent successfully'

    mock_gmail_service.users().messages().send.assert_called_once()


def test_send_email_with_attachments(gmail_toolkit, mock_gmail_service):
    """Test sending an email with attachments."""
    send_mock = MagicMock()
    mock_gmail_service.users().messages().send.return_value = send_mock
    send_mock.execute.return_value = {'id': 'msg123', 'threadId': 'thread123'}

    with (
        patch('os.path.isfile', return_value=True),
        patch('builtins.open', create=True) as mock_open,
    ):
        mock_open.return_value.__enter__.return_value.read.return_value = (
            b'test content'
        )

        result = gmail_toolkit.send_email(
            to='test@example.com',
            subject='Test Subject',
            body='Test Body',
            attachments=['/path/to/file.txt'],
        )

        assert result['success'] is True


def test_send_email_invalid_email(gmail_toolkit):
    """Test sending email with invalid email address."""
    result = gmail_toolkit.send_email(
        to='invalid-email', subject='Test Subject', body='Test Body'
    )

    assert 'error' in result
    assert 'Invalid email address' in result['error']


def test_send_email_failure(gmail_toolkit, mock_gmail_service):
    """Test sending email failure."""
    send_mock = MagicMock()
    mock_gmail_service.users().messages().send.return_value = send_mock
    send_mock.execute.side_effect = Exception("API Error")

    result = gmail_toolkit.send_email(
        to='test@example.com', subject='Test Subject', body='Test Body'
    )

    assert 'error' in result
    assert 'Failed to send email' in result['error']


def test_reply_to_email(gmail_toolkit, mock_gmail_service):
    """Test replying to an email."""
    # Mock getting original message
    get_mock = MagicMock()
    mock_gmail_service.users().messages().get.return_value = get_mock
    get_mock.execute.return_value = {
        'id': 'msg123',
        'threadId': 'thread123',
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Original Subject'},
                {'name': 'From', 'value': 'sender@example.com'},
                {'name': 'To', 'value': 'recipient@example.com'},
                {'name': 'Cc', 'value': 'cc@example.com'},
                {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'},
            ]
        },
    }

    # Mock sending reply
    send_mock = MagicMock()
    mock_gmail_service.users().messages().send.return_value = send_mock
    send_mock.execute.return_value = {
        'id': 'reply123',
        'threadId': 'thread123',
    }

    result = gmail_toolkit.reply_to_email(
        message_id='msg123', reply_body='This is a reply'
    )

    assert result['success'] is True
    assert result['message_id'] == 'reply123'
    assert result['message'] == 'Reply sent successfully'


def test_forward_email(gmail_toolkit, mock_gmail_service):
    """Test forwarding an email."""
    # Mock getting original message
    get_mock = MagicMock()
    mock_gmail_service.users().messages().get.return_value = get_mock
    get_mock.execute.return_value = {
        'id': 'msg123',
        'threadId': 'thread123',
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Original Subject'},
                {'name': 'From', 'value': 'sender@example.com'},
                {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'},
            ],
            'body': {
                'data': base64.urlsafe_b64encode(b'Original body').decode()
            },
        },
    }

    # Mock sending forward
    send_mock = MagicMock()
    mock_gmail_service.users().messages().send.return_value = send_mock
    send_mock.execute.return_value = {
        'id': 'forward123',
        'threadId': 'thread123',
    }

    result = gmail_toolkit.forward_email(
        message_id='msg123', to='forward@example.com'
    )

    assert result['success'] is True
    assert result['message_id'] == 'forward123'
    assert result['message'] == 'Email forwarded successfully'


def test_create_email_draft(gmail_toolkit, mock_gmail_service):
    """Test creating an email draft."""
    create_mock = MagicMock()
    mock_gmail_service.users().drafts().create.return_value = create_mock
    create_mock.execute.return_value = {
        'id': 'draft123',
        'message': {'id': 'msg123'},
    }

    result = gmail_toolkit.create_email_draft(
        to='test@example.com', subject='Test Subject', body='Test Body'
    )

    assert result['success'] is True
    assert result['draft_id'] == 'draft123'
    assert result['message_id'] == 'msg123'
    assert result['message'] == 'Draft created successfully'


def test_send_draft(gmail_toolkit, mock_gmail_service):
    """Test sending a draft."""
    send_mock = MagicMock()
    mock_gmail_service.users().drafts().send.return_value = send_mock
    send_mock.execute.return_value = {'id': 'msg123', 'threadId': 'thread123'}

    result = gmail_toolkit.send_draft(draft_id='draft123')

    assert result['success'] is True
    assert result['message_id'] == 'msg123'
    assert result['message'] == 'Draft sent successfully'


def test_fetch_emails(gmail_toolkit, mock_gmail_service):
    """Test fetching emails."""
    list_mock = MagicMock()
    mock_gmail_service.users().messages().list.return_value = list_mock
    list_mock.execute.return_value = {
        'messages': [{'id': 'msg123'}, {'id': 'msg456'}],
        'nextPageToken': 'next_token',
    }

    # Mock getting message details
    get_mock = MagicMock()
    mock_gmail_service.users().messages().get.return_value = get_mock
    get_mock.execute.return_value = {
        'id': 'msg123',
        'threadId': 'thread123',
        'snippet': 'Test snippet',
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Test Subject'},
                {'name': 'From', 'value': 'sender@example.com'},
                {'name': 'To', 'value': 'recipient@example.com'},
                {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'},
            ],
            'body': {'data': base64.urlsafe_b64encode(b'Test body').decode()},
        },
        'labelIds': ['INBOX'],
        'sizeEstimate': 1024,
    }

    result = gmail_toolkit.fetch_emails(query='test', max_results=10)

    assert result['success'] is True
    assert len(result['emails']) == 2
    assert result['total_count'] == 2
    assert result['next_page_token'] == 'next_token'


def test_fetch_thread_by_id(gmail_toolkit, mock_gmail_service):
    """Test fetching a thread by ID."""
    get_mock = MagicMock()
    mock_gmail_service.users().threads().get.return_value = get_mock
    get_mock.execute.return_value = {
        'id': 'thread123',
        'messages': [{'id': 'msg123'}, {'id': 'msg456'}],
    }

    # Mock getting message details
    msg_get_mock = MagicMock()
    mock_gmail_service.users().messages().get.return_value = msg_get_mock
    msg_get_mock.execute.return_value = {
        'id': 'msg123',
        'threadId': 'thread123',
        'snippet': 'Test snippet',
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Test Subject'},
                {'name': 'From', 'value': 'sender@example.com'},
                {'name': 'To', 'value': 'recipient@example.com'},
                {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'},
            ],
            'body': {'data': base64.urlsafe_b64encode(b'Test body').decode()},
        },
        'labelIds': ['INBOX'],
        'sizeEstimate': 1024,
    }

    result = gmail_toolkit.fetch_thread_by_id(thread_id='thread123')

    assert result['success'] is True
    assert result['thread_id'] == 'thread123'
    assert len(result['messages']) == 2
    assert result['message_count'] == 2


def test_modify_email_labels(gmail_toolkit, mock_gmail_service):
    """Test modifying email labels."""
    modify_mock = MagicMock()
    mock_gmail_service.users().messages().modify.return_value = modify_mock
    modify_mock.execute.return_value = {
        'id': 'msg123',
        'labelIds': ['INBOX', 'IMPORTANT'],
    }

    result = gmail_toolkit.modify_email_labels(
        message_id='msg123', add_labels=['IMPORTANT'], remove_labels=['UNREAD']
    )

    assert result['success'] is True
    assert result['message_id'] == 'msg123'
    assert 'IMPORTANT' in result['label_ids']
    assert result['message'] == 'Labels modified successfully'


def test_move_to_trash(gmail_toolkit, mock_gmail_service):
    """Test moving a message to trash."""
    trash_mock = MagicMock()
    mock_gmail_service.users().messages().trash.return_value = trash_mock
    trash_mock.execute.return_value = {'id': 'msg123', 'labelIds': ['TRASH']}

    result = gmail_toolkit.move_to_trash(message_id='msg123')

    assert result['success'] is True
    assert result['message_id'] == 'msg123'
    assert 'TRASH' in result['label_ids']
    assert result['message'] == 'Message moved to trash successfully'


def test_get_attachment(gmail_toolkit, mock_gmail_service):
    """Test getting an attachment."""
    attachment_mock = MagicMock()
    mock_gmail_service.users().messages().attachments().get.return_value = (
        attachment_mock
    )
    attachment_mock.execute.return_value = {
        'data': base64.urlsafe_b64encode(b'test attachment content').decode()
    }

    result = gmail_toolkit.get_attachment(
        message_id='msg123', attachment_id='att123'
    )

    assert result['success'] is True
    assert result['file_size'] > 0
    assert 'data' in result


def test_get_attachment_save_to_file(gmail_toolkit, mock_gmail_service):
    """Test getting an attachment and saving to file."""
    attachment_mock = MagicMock()
    mock_gmail_service.users().messages().attachments().get.return_value = (
        attachment_mock
    )
    attachment_mock.execute.return_value = {
        'data': base64.urlsafe_b64encode(b'test attachment content').decode()
    }

    with patch('builtins.open', create=True) as mock_open:
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        result = gmail_toolkit.get_attachment(
            message_id='msg123',
            attachment_id='att123',
            save_path='/path/to/save.txt',
        )

        assert result['success'] is True
        assert 'saved to' in result['message']
        mock_file.write.assert_called_once()


def test_list_threads(gmail_toolkit, mock_gmail_service):
    """Test listing threads."""
    list_mock = MagicMock()
    mock_gmail_service.users().threads().list.return_value = list_mock
    list_mock.execute.return_value = {
        'threads': [
            {
                'id': 'thread123',
                'snippet': 'Test thread snippet',
                'historyId': 'hist123',
            }
        ],
        'nextPageToken': 'next_token',
    }

    result = gmail_toolkit.list_threads(query='test', max_results=10)

    assert result['success'] is True
    assert len(result['threads']) == 1
    assert result['threads'][0]['thread_id'] == 'thread123'
    assert result['total_count'] == 1


def test_list_drafts(gmail_toolkit, mock_gmail_service):
    """Test listing drafts."""
    list_mock = MagicMock()
    mock_gmail_service.users().drafts().list.return_value = list_mock
    list_mock.execute.return_value = {
        'drafts': [
            {
                'id': 'draft123',
                'message': {
                    'id': 'msg123',
                    'threadId': 'thread123',
                    'snippet': 'Draft snippet',
                },
            }
        ],
        'nextPageToken': 'next_token',
    }

    result = gmail_toolkit.list_drafts(max_results=10)

    assert result['success'] is True
    assert len(result['drafts']) == 1
    assert result['drafts'][0]['draft_id'] == 'draft123'
    assert result['total_count'] == 1


def test_list_gmail_labels(gmail_toolkit, mock_gmail_service):
    """Test listing Gmail labels."""
    list_mock = MagicMock()
    mock_gmail_service.users().labels().list.return_value = list_mock
    list_mock.execute.return_value = {
        'labels': [
            {
                'id': 'INBOX',
                'name': 'INBOX',
                'type': 'system',
                'messagesTotal': 10,
                'messagesUnread': 2,
                'threadsTotal': 5,
                'threadsUnread': 1,
            }
        ]
    }

    result = gmail_toolkit.list_gmail_labels()

    assert result['success'] is True
    assert len(result['labels']) == 1
    assert result['labels'][0]['id'] == 'INBOX'
    assert result['labels'][0]['name'] == 'INBOX'
    assert result['total_count'] == 1


def test_create_label(gmail_toolkit, mock_gmail_service):
    """Test creating a Gmail label."""
    create_mock = MagicMock()
    mock_gmail_service.users().labels().create.return_value = create_mock
    create_mock.execute.return_value = {
        'id': 'Label_123',
        'name': 'Test Label',
    }

    result = gmail_toolkit.create_label(
        name='Test Label',
        label_list_visibility='labelShow',
        message_list_visibility='show',
    )

    assert result['success'] is True
    assert result['label_id'] == 'Label_123'
    assert result['label_name'] == 'Test Label'
    assert result['message'] == 'Label created successfully'


def test_delete_label(gmail_toolkit, mock_gmail_service):
    """Test deleting a Gmail label."""
    delete_mock = MagicMock()
    mock_gmail_service.users().labels().delete.return_value = delete_mock
    delete_mock.execute.return_value = {}

    result = gmail_toolkit.delete_label(label_id='Label_123')

    assert result['success'] is True
    assert result['label_id'] == 'Label_123'
    assert result['message'] == 'Label deleted successfully'


def test_modify_thread_labels(gmail_toolkit, mock_gmail_service):
    """Test modifying thread labels."""
    modify_mock = MagicMock()
    mock_gmail_service.users().threads().modify.return_value = modify_mock
    modify_mock.execute.return_value = {
        'id': 'thread123',
        'labelIds': ['INBOX', 'IMPORTANT'],
    }

    result = gmail_toolkit.modify_thread_labels(
        thread_id='thread123',
        add_labels=['IMPORTANT'],
        remove_labels=['UNREAD'],
    )

    assert result['success'] is True
    assert result['thread_id'] == 'thread123'
    assert 'IMPORTANT' in result['label_ids']
    assert result['message'] == 'Thread labels modified successfully'


def test_get_profile(gmail_toolkit, mock_gmail_service):
    """Test getting Gmail profile."""
    profile_mock = MagicMock()
    mock_gmail_service.users().getProfile.return_value = profile_mock
    profile_mock.execute.return_value = {
        'emailAddress': 'user@example.com',
        'messagesTotal': 1000,
        'threadsTotal': 500,
        'historyId': 'hist123',
    }

    result = gmail_toolkit.get_profile()

    assert result['success'] is True
    assert result['profile']['email_address'] == 'user@example.com'
    assert result['profile']['messages_total'] == 1000
    assert result['profile']['threads_total'] == 500


def test_get_contacts(gmail_toolkit, mock_people_service):
    """Test getting contacts."""
    connections_mock = MagicMock()
    mock_people_service.people().connections().list.return_value = (
        connections_mock
    )
    connections_mock.execute.return_value = {
        'connections': [
            {
                'resourceName': 'people/123',
                'names': [{'displayName': 'John Doe'}],
                'emailAddresses': [{'value': 'john@example.com'}],
                'phoneNumbers': [{'value': '+1234567890'}],
                'organizations': [{'name': 'Test Company'}],
            }
        ],
        'nextPageToken': 'next_token',
    }

    result = gmail_toolkit.get_contacts(max_results=10)

    assert result['success'] is True
    assert len(result['contacts']) == 1
    assert result['contacts'][0]['resource_name'] == 'people/123'
    assert result['total_count'] == 1


def test_search_people(gmail_toolkit, mock_people_service):
    """Test searching for people."""
    search_mock = MagicMock()
    mock_people_service.people().searchContacts.return_value = search_mock
    search_mock.execute.return_value = {
        'results': [
            {
                'person': {
                    'resourceName': 'people/123',
                    'names': [{'displayName': 'John Doe'}],
                    'emailAddresses': [{'value': 'john@example.com'}],
                    'phoneNumbers': [{'value': '+1234567890'}],
                    'organizations': [{'name': 'Test Company'}],
                }
            }
        ]
    }

    result = gmail_toolkit.search_people(query='John', max_results=10)

    assert result['success'] is True
    assert len(result['people']) == 1
    assert result['people'][0]['resource_name'] == 'people/123'
    assert result['total_count'] == 1


def test_error_handling(gmail_toolkit, mock_gmail_service):
    """Test error handling in various methods."""
    # Test send_email error
    send_mock = MagicMock()
    mock_gmail_service.users().messages().send.return_value = send_mock
    send_mock.execute.side_effect = Exception("API Error")

    result = gmail_toolkit.send_email(
        to='test@example.com', subject='Test', body='Test'
    )

    assert 'error' in result
    assert 'Failed to send email' in result['error']

    # Test fetch_emails error
    list_mock = MagicMock()
    mock_gmail_service.users().messages().list.return_value = list_mock
    list_mock.execute.side_effect = Exception("API Error")

    result = gmail_toolkit.fetch_emails()
    assert 'error' in result
    assert 'Failed to fetch emails' in result['error']


def test_email_validation(gmail_toolkit):
    """Test email validation functionality."""
    # Test valid emails
    assert gmail_toolkit._is_valid_email('test@example.com') is True
    assert gmail_toolkit._is_valid_email('user.name+tag@domain.co.uk') is True

    # Test invalid emails
    assert gmail_toolkit._is_valid_email('invalid-email') is False
    assert gmail_toolkit._is_valid_email('test@') is False
    assert gmail_toolkit._is_valid_email('@example.com') is False
    assert gmail_toolkit._is_valid_email('') is False


def test_message_creation_helpers(gmail_toolkit):
    """Test helper methods for message creation."""
    # Test header value extraction
    headers = [
        {'name': 'Subject', 'value': 'Test Subject'},
        {'name': 'From', 'value': 'sender@example.com'},
        {'name': 'To', 'value': 'recipient@example.com'},
    ]

    assert gmail_toolkit._get_header_value(headers, 'Subject') == (
        'Test Subject'
    )
    assert gmail_toolkit._get_header_value(headers, 'From') == (
        'sender@example.com'
    )
    assert gmail_toolkit._get_header_value(headers, 'NonExistent') == ''

    # Test message body extraction
    message = {
        'payload': {
            'mimeType': 'text/plain',
            'body': {
                'data': base64.urlsafe_b64encode(b'Test body content').decode()
            },
        }
    }

    body = gmail_toolkit._extract_message_body(message)
    assert body == 'Test body content'


def test_extract_attachments_regular_attachment(gmail_toolkit):
    """Test extracting a regular attachment (not inline)."""
    message = {
        'payload': {
            'parts': [
                {
                    'mimeType': 'text/plain',
                    'body': {
                        'data': base64.urlsafe_b64encode(
                            b'Email body'
                        ).decode()
                    },
                },
                {
                    'filename': 'document.pdf',
                    'mimeType': 'application/pdf',
                    'headers': [
                        {
                            'name': 'Content-Disposition',
                            'value': 'attachment; filename="document.pdf"',
                        }
                    ],
                    'body': {'attachmentId': 'ANGjdJ123', 'size': 102400},
                },
            ]
        }
    }

    attachments = gmail_toolkit._extract_attachments(
        message, include_inline=True
    )

    assert len(attachments) == 1
    assert attachments[0]['attachment_id'] == 'ANGjdJ123'
    assert attachments[0]['filename'] == 'document.pdf'
    assert attachments[0]['mime_type'] == 'application/pdf'
    assert attachments[0]['size'] == 102400
    assert attachments[0]['is_inline'] is False


def test_extract_attachments_inline_image(gmail_toolkit):
    """Test extracting inline images with Content-ID."""
    message = {
        'payload': {
            'parts': [
                {
                    'mimeType': 'text/html',
                    'body': {
                        'data': base64.urlsafe_b64encode(
                            b'<html><img src="cid:logo"></html>'
                        ).decode()
                    },
                },
                {
                    'filename': 'logo.png',
                    'mimeType': 'image/png',
                    'headers': [
                        {'name': 'Content-ID', 'value': '<logo@example.com>'}
                    ],
                    'body': {'attachmentId': 'ANGjdJ456', 'size': 2048},
                },
                {
                    'filename': 'signature.jpg',
                    'mimeType': 'image/jpeg',
                    'headers': [
                        {
                            'name': 'Content-Disposition',
                            'value': 'inline; filename="signature.jpg"',
                        }
                    ],
                    'body': {'attachmentId': 'ANGjdJ789', 'size': 3072},
                },
            ]
        }
    }

    attachments = gmail_toolkit._extract_attachments(
        message, include_inline=True
    )

    assert len(attachments) == 2
    # First inline image (Content-ID)
    assert attachments[0]['attachment_id'] == 'ANGjdJ456'
    assert attachments[0]['filename'] == 'logo.png'
    assert attachments[0]['is_inline'] is True
    # Second inline image (Content-Disposition: inline)
    assert attachments[1]['attachment_id'] == 'ANGjdJ789'
    assert attachments[1]['filename'] == 'signature.jpg'
    assert attachments[1]['is_inline'] is True


def test_extract_message_body_multipart_alternative(gmail_toolkit):
    """Test extracting body from multipart/alternative (prefers plain text)."""
    message = {
        'payload': {
            'mimeType': 'multipart/alternative',
            'parts': [
                {
                    'mimeType': 'text/plain',
                    'body': {
                        'data': base64.urlsafe_b64encode(
                            b'Plain text version'
                        ).decode()
                    },
                },
                {
                    'mimeType': 'text/html',
                    'body': {
                        'data': base64.urlsafe_b64encode(
                            b'<html><b>HTML version</b></html>'
                        ).decode()
                    },
                },
            ],
        }
    }

    body = gmail_toolkit._extract_message_body(message)

    # Should prefer plain text over HTML
    assert body == 'Plain text version'
    assert '<html>' not in body


def test_extract_message_body_nested_multipart_mixed(gmail_toolkit):
    """Test extracting body from nested multipart/mixed structure."""
    message = {
        'payload': {
            'mimeType': 'multipart/mixed',
            'parts': [
                {
                    'mimeType': 'multipart/alternative',
                    'parts': [
                        {
                            'mimeType': 'text/plain',
                            'body': {
                                'data': base64.urlsafe_b64encode(
                                    b'Main content'
                                ).decode()
                            },
                        },
                        {
                            'mimeType': 'text/html',
                            'body': {
                                'data': base64.urlsafe_b64encode(
                                    b'<html>Main content HTML</html>'
                                ).decode()
                            },
                        },
                    ],
                },
                {
                    'filename': 'attachment.pdf',
                    'mimeType': 'application/pdf',
                    'body': {'attachmentId': 'ANGjdJ999', 'size': 5000},
                },
            ],
        }
    }

    body = gmail_toolkit._extract_message_body(message)

    # Should extract plain text from nested structure
    assert 'Main content' in body
    # Should not include HTML tags
    assert '<html>' not in body


def test_extract_message_body_multiple_text_parts(gmail_toolkit):
    """Test extracting body when multiple text parts exist."""
    message = {
        'payload': {
            'mimeType': 'multipart/mixed',
            'parts': [
                {
                    'mimeType': 'text/plain',
                    'body': {
                        'data': base64.urlsafe_b64encode(
                            b'First part'
                        ).decode()
                    },
                },
                {
                    'mimeType': 'multipart/alternative',
                    'parts': [
                        {
                            'mimeType': 'text/plain',
                            'body': {
                                'data': base64.urlsafe_b64encode(
                                    b'Second part'
                                ).decode()
                            },
                        }
                    ],
                },
                {
                    'mimeType': 'text/plain',
                    'body': {
                        'data': base64.urlsafe_b64encode(
                            b'Third part'
                        ).decode()
                    },
                },
            ],
        }
    }

    body = gmail_toolkit._extract_message_body(message)

    # Should collect all text parts
    assert 'First part' in body
    assert 'Second part' in body
    assert 'Third part' in body
    # Parts should be separated by double newlines
    assert '\n\n' in body
