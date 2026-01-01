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

import json
import os
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from camel.toolkits import OutlookMailToolkit
from camel.toolkits.microsoft_outlook_mail_toolkit import (
    CustomAzureCredential,
)


@pytest.fixture
def mock_graph_service():
    """Mock Microsoft Graph API service with async methods."""
    with patch("msgraph.GraphServiceClient") as mock_service_client:
        mock_client = MagicMock()
        mock_service_client.return_value = mock_client

        # Mock me endpoint
        mock_me = MagicMock()
        mock_client.me = mock_me

        # Mock messages endpoint
        mock_messages = MagicMock()
        mock_me.messages = mock_messages

        # Mock send_mail endpoint (async)
        mock_send_mail = MagicMock()
        mock_me.send_mail = mock_send_mail
        mock_send_mail.post = AsyncMock()

        # Mock messages.get for listing messages (async)
        mock_messages.get = AsyncMock()

        # Mock messages.post for creating drafts (async)
        mock_messages.post = AsyncMock()

        # Mock messages.by_message_id for specific message operations
        mock_by_message_id = MagicMock()
        mock_messages.by_message_id = MagicMock(
            return_value=mock_by_message_id
        )

        # Mock get message by ID (async)
        mock_by_message_id.get = AsyncMock()

        # Mock send draft (async)
        mock_send = MagicMock()
        mock_by_message_id.send = mock_send
        mock_send.post = AsyncMock()

        # Mock delete message (async)
        mock_by_message_id.delete = AsyncMock()

        # Mock move message (async)
        mock_move = MagicMock()
        mock_by_message_id.move = mock_move
        mock_move.post = AsyncMock()

        # Mock attachments (async)
        mock_attachments = MagicMock()
        mock_by_message_id.attachments = mock_attachments
        mock_attachments.get = AsyncMock()

        # Mock reply endpoint (async)
        mock_reply = MagicMock()
        mock_by_message_id.reply = mock_reply
        mock_reply.post = AsyncMock()

        # Mock reply_all endpoint (async)
        mock_reply_all = MagicMock()
        mock_by_message_id.reply_all = mock_reply_all
        mock_reply_all.post = AsyncMock()

        # Mock patch endpoint for updating messages (async)
        mock_by_message_id.patch = AsyncMock()

        # Mock mail_folders for folder-specific operations
        mock_mail_folders = MagicMock()
        mock_me.mail_folders = mock_mail_folders

        # Mock by_mail_folder_id
        mock_by_folder_id = MagicMock()
        mock_mail_folders.by_mail_folder_id = MagicMock(
            return_value=mock_by_folder_id
        )

        # Mock folder messages (async)
        mock_folder_messages = MagicMock()
        mock_by_folder_id.messages = mock_folder_messages
        mock_folder_messages.get = AsyncMock()

        yield mock_client


@pytest.fixture
def outlook_toolkit(mock_graph_service):
    """Fixture that provides a mocked OutlookMailToolkit instance."""
    # Create a mock credentials object to avoid OAuth authentication
    mock_credentials = MagicMock()
    mock_credentials.valid = True

    with (
        patch.dict(
            'os.environ',
            {
                'MICROSOFT_TENANT_ID': 'mock_tenant_id',
                'MICROSOFT_CLIENT_ID': 'mock_client_id',
                'MICROSOFT_CLIENT_SECRET': 'mock_client_secret',
            },
        ),
        patch.object(
            OutlookMailToolkit,
            '_get_dynamic_redirect_uri',
            return_value="http://localhost:12345",
        ),
        patch.object(
            OutlookMailToolkit,
            '_authenticate',
            return_value=mock_credentials,
        ),
        patch.object(
            OutlookMailToolkit,
            '_get_graph_client',
            return_value=mock_graph_service,
        ),
    ):
        toolkit = OutlookMailToolkit()
        toolkit.client = mock_graph_service
        yield toolkit


@pytest.mark.asyncio
async def test_send_email(outlook_toolkit, mock_graph_service):
    """Test sending an email successfully."""
    mock_graph_service.me.send_mail.post.return_value = None

    result = await outlook_toolkit.outlook_send_email(
        to_email=['test@example.com'],
        subject='Test Subject',
        content='Test Body',
    )

    assert result['status'] == 'success'
    assert result['message'] == 'Email sent successfully'
    assert result['recipients'] == ['test@example.com']
    assert result['subject'] == 'Test Subject'

    mock_graph_service.me.send_mail.post.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_with_attachments(
    outlook_toolkit, mock_graph_service
):
    """Test sending an email with attachments."""
    mock_graph_service.me.send_mail.post.return_value = None

    with (
        patch('os.path.isfile', return_value=True),
        patch('builtins.open', create=True) as mock_file_open,
    ):
        mock_file = mock_file_open.return_value.__enter__.return_value
        mock_file.read.return_value = b'test content'

        result = await outlook_toolkit.outlook_send_email(
            to_email=['test@example.com'],
            subject='Test Subject',
            content='Test Body',
            attachments=['/path/to/file.txt'],
        )

        assert result['status'] == 'success'
        mock_graph_service.me.send_mail.post.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_invalid_email(outlook_toolkit):
    """Test sending email with invalid email address."""
    result = await outlook_toolkit.outlook_send_email(
        to_email=['invalid-email'],
        subject='Test Subject',
        content='Test Body',
    )

    assert 'error' in result
    assert 'Invalid email address' in result['error']


@pytest.mark.asyncio
async def test_send_email_failure(outlook_toolkit, mock_graph_service):
    """Test sending email failure."""
    mock_graph_service.me.send_mail.post.side_effect = Exception("API Error")

    result = await outlook_toolkit.outlook_send_email(
        to_email=['test@example.com'],
        subject='Test Subject',
        content='Test Body',
    )

    assert 'error' in result
    assert 'Failed to send email' in result['error']


@pytest.mark.asyncio
async def test_create_email_draft(outlook_toolkit, mock_graph_service):
    """Test creating an email draft."""
    mock_draft_result = MagicMock()
    mock_draft_result.id = 'draft123'
    mock_graph_service.me.messages.post.return_value = mock_draft_result

    result = await outlook_toolkit.outlook_create_draft_email(
        to_email=['test@example.com'],
        subject='Test Subject',
        content='Test Body',
    )

    assert result['status'] == 'success'
    assert result['draft_id'] == 'draft123'
    assert result['message'] == 'Draft email created successfully'
    assert result['recipients'] == ['test@example.com']
    assert result['subject'] == 'Test Subject'

    mock_graph_service.me.messages.post.assert_called_once()


def test_browser_auth_persists_refresh_token(tmp_path):
    toolkit = OutlookMailToolkit.__new__(OutlookMailToolkit)
    toolkit.scopes = ["Mail.Send", "Mail.ReadWrite"]
    toolkit.redirect_uri = "http://localhost:12345"
    toolkit.refresh_token_file_path = tmp_path / "refresh_token.json"
    toolkit.timeout = 5
    toolkit.tenant_id = "common"
    toolkit.client_id = "mock_client_id"
    toolkit.client_secret = "mock_client_secret"

    toolkit._get_auth_url = MagicMock(return_value="https://example.com/auth")
    toolkit._get_authorization_code_via_browser = MagicMock(
        return_value="mock_auth_code"
    )

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
        "expires_in": 3600,
    }

    with patch(
        "camel.toolkits.microsoft_outlook_mail_toolkit.requests.post",
        return_value=mock_response,
    ):
        credentials = toolkit._authenticate_using_browser()

    assert isinstance(credentials, CustomAzureCredential)
    assert credentials.refresh_token == "mock_refresh_token"
    assert credentials._access_token == "mock_access_token"

    with open(toolkit.refresh_token_file_path, "r") as f:
        token_data = json.load(f)
    assert token_data["refresh_token"] == "mock_refresh_token"


@pytest.mark.asyncio
async def test_create_email_draft_with_attachments(
    outlook_toolkit, mock_graph_service
):
    """Test creating an email draft with attachments."""
    mock_draft_result = MagicMock()
    mock_draft_result.id = 'draft123'
    mock_graph_service.me.messages.post.return_value = mock_draft_result

    with (
        patch('os.path.isfile', return_value=True),
        patch('builtins.open', create=True) as mock_file_open,
    ):
        mock_file = mock_file_open.return_value.__enter__.return_value
        mock_file.read.return_value = b'test content'

        result = await outlook_toolkit.outlook_create_draft_email(
            to_email=['test@example.com'],
            subject='Test Subject',
            content='Test Body',
            attachments=['/path/to/file.txt'],
        )

        assert result['status'] == 'success'
        assert result['draft_id'] == 'draft123'
        mock_graph_service.me.messages.post.assert_called_once()


@pytest.mark.asyncio
async def test_create_email_draft_invalid_email(outlook_toolkit):
    """Test creating draft with invalid email address."""
    result = await outlook_toolkit.outlook_create_draft_email(
        to_email=['invalid-email'],
        subject='Test Subject',
        content='Test Body',
    )

    assert 'error' in result
    assert 'Invalid email address' in result['error']


@pytest.mark.asyncio
async def test_create_email_draft_failure(outlook_toolkit, mock_graph_service):
    """Test creating email draft failure."""
    mock_graph_service.me.messages.post.side_effect = Exception("API Error")

    result = await outlook_toolkit.outlook_create_draft_email(
        to_email=['test@example.com'],
        subject='Test Subject',
        content='Test Body',
    )

    assert 'error' in result
    assert 'Failed to create draft email' in result['error']


@pytest.mark.asyncio
async def test_send_draft_email(outlook_toolkit, mock_graph_service):
    """Test sending a draft email."""
    mock_graph_service.me.messages.by_message_id().send.post.return_value = (
        None
    )

    result = await outlook_toolkit.outlook_send_draft_email(
        draft_id='draft123'
    )

    assert result['status'] == 'success'
    assert result['message'] == 'Draft email sent successfully'
    assert result['draft_id'] == 'draft123'

    mock_graph_service.me.messages.by_message_id().send.post.assert_called_once()


@pytest.mark.asyncio
async def test_send_draft_email_failure(outlook_toolkit, mock_graph_service):
    """Test sending draft email failure."""
    mock_graph_service.me.messages.by_message_id().send.post.side_effect = (
        Exception("API Error")
    )

    result = await outlook_toolkit.outlook_send_draft_email(
        draft_id='draft123'
    )

    assert 'error' in result
    assert 'Failed to send draft email' in result['error']


@pytest.mark.asyncio
async def test_delete_email(outlook_toolkit, mock_graph_service):
    """Test deleting an email successfully."""
    mock_graph_service.me.messages.by_message_id().delete.return_value = None

    result = await outlook_toolkit.outlook_delete_email(message_id='msg123')

    assert result['status'] == 'success'
    assert result['message'] == 'Email deleted successfully'
    assert result['message_id'] == 'msg123'

    mock_graph_service.me.messages.by_message_id().delete.assert_called_once()


@pytest.mark.asyncio
async def test_delete_email_failure(outlook_toolkit, mock_graph_service):
    """Test deleting email failure."""
    mock_graph_service.me.messages.by_message_id().delete.side_effect = (
        Exception("API Error")
    )

    result = await outlook_toolkit.outlook_delete_email(message_id='msg123')

    assert 'error' in result
    assert 'Failed to delete email' in result['error']


@pytest.mark.asyncio
async def test_move_message_to_folder(outlook_toolkit, mock_graph_service):
    """Test moving an email to a folder successfully."""
    mock_graph_service.me.messages.by_message_id().move.post.return_value = (
        None
    )

    result = await outlook_toolkit.outlook_move_message_to_folder(
        message_id='msg123', destination_folder_id='inbox'
    )

    assert result['status'] == 'success'
    assert result['message'] == 'Email moved successfully'
    assert result['message_id'] == 'msg123'
    assert result['destination_folder_id'] == 'inbox'

    mock_graph_service.me.messages.by_message_id().move.post.assert_called_once()


@pytest.mark.asyncio
async def test_move_message_to_folder_failure(
    outlook_toolkit, mock_graph_service
):
    """Test moving email failure."""
    mock_graph_service.me.messages.by_message_id().move.post.side_effect = (
        Exception("API Error")
    )

    result = await outlook_toolkit.outlook_move_message_to_folder(
        message_id='msg123', destination_folder_id='inbox'
    )

    assert 'error' in result
    assert 'Failed to move email' in result['error']


@pytest.mark.asyncio
async def test_get_attachments(outlook_toolkit, mock_graph_service):
    """Test getting attachments and saving to disk."""
    import base64

    mock_attachment = MagicMock()
    mock_attachment.name = 'document.pdf'
    mock_attachment.is_inline = False
    mock_attachment.content_bytes = base64.b64encode(b'test content')

    mock_response = MagicMock()
    mock_response.value = [mock_attachment]
    mock_attachments = mock_graph_service.me.messages.by_message_id()
    mock_attachments.attachments.get.return_value = mock_response

    with (
        patch('os.makedirs'),
        patch('os.path.exists', return_value=False),
        patch('builtins.open', create=True),
    ):
        result = await outlook_toolkit.outlook_get_attachments(
            message_id='msg123',
        )

        assert result['status'] == 'success'
        assert result['total_count'] == 1


@pytest.mark.asyncio
async def test_get_attachments_exclude_inline(
    outlook_toolkit, mock_graph_service
):
    """Test getting attachments excluding inline attachments (default)."""
    mock_attachment1 = MagicMock()
    mock_attachment1.name = 'image.png'
    mock_attachment1.is_inline = True

    mock_response = MagicMock()
    mock_response.value = [mock_attachment1]
    mock_attachments = mock_graph_service.me.messages.by_message_id()
    mock_attachments.attachments.get.return_value = mock_response

    result = await outlook_toolkit.outlook_get_attachments(
        message_id='msg123',
        include_inline_attachments=False,
    )

    assert result['status'] == 'success'
    assert result['total_count'] == 0  # Only non-inline attachment
    assert not result['attachments']


@pytest.mark.asyncio
async def test_get_attachments_include_inline(
    outlook_toolkit, mock_graph_service
):
    """Test getting attachments including inline attachments."""
    mock_attachment1 = MagicMock()
    mock_attachment1.name = 'document.pdf'
    mock_attachment1.is_inline = True

    mock_attachment2 = MagicMock()
    mock_attachment2.name = 'image.png'
    mock_attachment2.is_inline = True

    mock_response = MagicMock()
    mock_response.value = [mock_attachment1, mock_attachment2]
    mock_attachments = mock_graph_service.me.messages.by_message_id()
    mock_attachments.attachments.get.return_value = mock_response

    result = await outlook_toolkit.outlook_get_attachments(
        message_id='msg123',
        metadata_only=True,
        include_inline_attachments=True,
    )

    assert result['status'] == 'success'
    assert result['total_count'] == 2  # Both attachments included
    assert result['attachments'][0]['name'] == 'document.pdf'
    assert result['attachments'][1]['name'] == 'image.png'


@pytest.mark.asyncio
async def test_get_attachments_failure(outlook_toolkit, mock_graph_service):
    """Test getting attachments failure."""
    mock_attachments = mock_graph_service.me.messages.by_message_id()
    mock_attachments.attachments.get.side_effect = Exception("API Error")

    result = await outlook_toolkit.outlook_get_attachments(message_id='msg123')

    assert 'error' in result
    assert 'Failed to get attachments' in result['error']


@pytest.mark.asyncio
async def test_get_attachments_with_content_and_save_path(
    outlook_toolkit, mock_graph_service
):
    """Test getting attachments with metadata_only=False and save_path."""
    import base64
    import tempfile

    original_content = b'This is a test PDF file content.'
    encoded_content = base64.b64encode(original_content)

    mock_attachment = MagicMock()
    mock_attachment.id = 'attachment-id-456'
    mock_attachment.name = 'invoice.pdf'
    mock_attachment.is_inline = False
    mock_attachment.content_bytes = encoded_content

    mock_response = MagicMock()
    mock_response.value = [mock_attachment]
    mock_attachments = mock_graph_service.me.messages.by_message_id()
    mock_attachments.attachments.get.return_value = mock_response

    with tempfile.TemporaryDirectory() as temp_dir:
        m_open = mock_open()
        with (
            patch('os.makedirs') as mock_makedirs,
            patch('os.path.exists', return_value=False),
            patch('builtins.open', m_open),
        ):
            result = await outlook_toolkit.outlook_get_attachments(
                message_id='msg456',
                metadata_only=False,
                save_path=temp_dir,
            )

            assert result['status'] == 'success'
            assert result['total_count'] == 1
            attachment_info = result['attachments'][0]
            assert attachment_info['name'] == 'invoice.pdf'
            assert 'saved_path' in attachment_info
            assert 'content_bytes' not in attachment_info

            expected_path = os.path.join(temp_dir, 'invoice.pdf')
            assert attachment_info['saved_path'] == expected_path
            mock_makedirs.assert_called_once_with(temp_dir, exist_ok=True)
            m_open.assert_called_once_with(expected_path, 'wb')
            handle = m_open()
            handle.write.assert_called_once_with(original_content)


@pytest.fixture(
    params=[
        ('Plain text email body.', 'text', 'Plain text email body.'),
        (
            '<html><body><p>HTML email body.</p></body></html>',
            'html',
            'HTML email body.',
        ),
    ],
    ids=['plain_text', 'html_to_text'],
)
def create_mock_message(request):
    """Parametrized fixture that creates mock message objects."""
    from datetime import datetime, timezone

    body_content, body_type, expected_body = request.param

    mock_msg = MagicMock()
    mock_msg.id = 'msg123'
    mock_msg.subject = 'Test Subject'
    mock_msg.body_preview = body_content[:25] + '...'
    mock_msg.is_read = False
    mock_msg.is_draft = False
    mock_msg.has_attachments = False
    mock_msg.importance = 'normal'
    mock_msg.received_date_time = datetime(
        2024, 1, 15, 10, 30, tzinfo=timezone.utc
    )
    mock_msg.sent_date_time = datetime(
        2024, 1, 15, 10, 29, tzinfo=timezone.utc
    )

    # Mock body
    mock_body = MagicMock()
    mock_body.content = body_content
    mock_body.content_type = body_type
    mock_msg.body = mock_body

    # Mock from address
    mock_from = MagicMock()
    mock_from.email_address.address = 'sender@example.com'
    mock_from.email_address.name = 'Sender Name'
    mock_msg.from_ = mock_from

    # Mock recipients
    mock_to = MagicMock()
    mock_to.email_address.address = 'recipient@example.com'
    mock_to.email_address.name = 'Recipient Name'
    mock_msg.to_recipients = [mock_to]
    mock_msg.cc_recipients = []
    mock_msg.bcc_recipients = []

    # Add expected body for assertions
    mock_msg.expected_body = expected_body

    return mock_msg


@pytest.mark.asyncio
async def test_get_message(
    outlook_toolkit, mock_graph_service, create_mock_message
):
    """Test getting messages with different content types."""
    with patch(
        'camel.toolkits.microsoft_outlook_mail_toolkit.isinstance',
        return_value=True,
    ):
        mock_graph_service.me.messages.by_message_id().get.return_value = (
            create_mock_message
        )

        result = await outlook_toolkit.outlook_get_message(message_id='msg123')

    assert result['status'] == 'success'
    assert 'message' in result

    message = result['message']
    assert message['message_id'] == 'msg123'
    assert message['subject'] == 'Test Subject'
    assert message['body'] == create_mock_message.expected_body
    assert message['is_read'] is False
    assert message['from'][0]['address'] == 'sender@example.com'
    assert message['to_recipients'][0]['address'] == 'recipient@example.com'

    mock_graph_service.me.messages.by_message_id().get.assert_called_once()


@pytest.mark.asyncio
async def test_get_message_failure(outlook_toolkit, mock_graph_service):
    """Test get_message handles API errors correctly."""
    mock_graph_service.me.messages.by_message_id().get.side_effect = Exception(
        "API Error"
    )

    result = await outlook_toolkit.outlook_get_message(message_id='msg123')

    assert 'error' in result
    assert 'Failed to get message' in result['error']


@pytest.mark.asyncio
async def test_list_messages(
    outlook_toolkit, mock_graph_service, create_mock_message
):
    """Test listing messages with different content types."""
    with patch(
        'camel.toolkits.microsoft_outlook_mail_toolkit.isinstance',
        return_value=True,
    ):
        mock_response = MagicMock()
        mock_response.value = [create_mock_message]
        mock_graph_service.me.messages.get.return_value = mock_response

        result = await outlook_toolkit.outlook_list_messages()

    assert result['status'] == 'success'
    assert 'messages' in result
    assert result['total_count'] == 1
    assert len(result['messages']) == 1

    message = result['messages'][0]
    assert message['message_id'] == 'msg123'
    assert message['subject'] == 'Test Subject'
    assert message['body'] == create_mock_message.expected_body
    assert message['is_read'] is False
    assert message['from'][0]['address'] == 'sender@example.com'
    assert message['to_recipients'][0]['address'] == 'recipient@example.com'

    mock_graph_service.me.messages.get.assert_called_once()


@pytest.mark.asyncio
async def test_list_messages_failure(outlook_toolkit, mock_graph_service):
    """Test list_messages handles API errors correctly."""
    mock_graph_service.me.messages.get.side_effect = Exception("API Error")

    result = await outlook_toolkit.outlook_list_messages()

    assert 'error' in result
    assert 'Failed to list messages' in result['error']


@pytest.mark.asyncio
async def test_reply_to_email(outlook_toolkit, mock_graph_service):
    """Test replying to an email (reply to sender only)."""
    mock_graph_service.me.messages.by_message_id().reply.post.return_value = (
        None
    )

    result = await outlook_toolkit.outlook_reply_to_email(
        message_id='msg123',
        content='This is my reply',
        reply_all=False,
    )

    assert result['status'] == 'success'
    assert result['message'] == 'Reply sent successfully'
    assert result['message_id'] == 'msg123'
    assert result['reply_type'] == 'reply'

    mock_graph_service.me.messages.by_message_id().reply.post.assert_called_once()
    mock_graph_service.me.messages.by_message_id().reply_all.post.assert_not_called()


@pytest.mark.asyncio
async def test_reply_to_email_all(outlook_toolkit, mock_graph_service):
    """Test replying to all recipients of an email."""
    mock_reply_all = mock_graph_service.me.messages.by_message_id().reply_all
    mock_reply_all.post.return_value = None

    result = await outlook_toolkit.outlook_reply_to_email(
        message_id='msg456',
        content='This is my reply to all',
        reply_all=True,
    )

    assert result['status'] == 'success'
    assert result['message'] == 'Reply All sent successfully'
    assert result['message_id'] == 'msg456'
    assert result['reply_type'] == 'reply all'

    mock_reply_all.post.assert_called_once()
    mock_graph_service.me.messages.by_message_id().reply.post.assert_not_called()


@pytest.mark.asyncio
async def test_reply_to_email_failure(outlook_toolkit, mock_graph_service):
    """Test reply to email failure when using simple reply."""
    mock_graph_service.me.messages.by_message_id().reply.post.side_effect = (
        Exception("API Error: Unable to send reply")
    )

    result = await outlook_toolkit.outlook_reply_to_email(
        message_id='msg123',
        content='This reply will fail',
        reply_all=False,
    )

    assert 'error' in result
    assert 'Failed to reply to email' in result['error']
    assert 'API Error: Unable to send reply' in result['error']


@pytest.mark.asyncio
async def test_reply_to_email_all_failure(outlook_toolkit, mock_graph_service):
    """Test reply to email failure when using reply all."""
    mock_reply_all = mock_graph_service.me.messages.by_message_id().reply_all
    mock_reply_all.post.side_effect = Exception(
        "API Error: Unable to send reply all"
    )

    result = await outlook_toolkit.outlook_reply_to_email(
        message_id='msg456',
        content='This reply all will fail',
        reply_all=True,
    )

    assert 'error' in result
    assert 'Failed to reply to email' in result['error']
    assert 'API Error: Unable to send reply all' in result['error']


@pytest.mark.asyncio
async def test_update_draft_message(outlook_toolkit, mock_graph_service):
    """Test updating a draft message with all parameters."""
    mock_by_message_id = mock_graph_service.me.messages.by_message_id()
    mock_by_message_id.patch.return_value = None

    result = await outlook_toolkit.outlook_update_draft_message(
        message_id='draft123',
        subject='Updated Subject',
        content='Updated content',
        is_content_html=True,
        to_email=['new@example.com'],
        cc_recipients=['cc@example.com'],
        bcc_recipients=['bcc@example.com'],
        reply_to=['reply@example.com'],
    )

    assert result['status'] == 'success'
    assert result['message'] == 'Draft message updated successfully'
    assert result['message_id'] == 'draft123'
    assert result['updated_params']['subject'] == 'Updated Subject'
    assert result['updated_params']['content'] == 'Updated content'
    assert result['updated_params']['to_email'] == ['new@example.com']
    assert result['updated_params']['cc_recipients'] == ['cc@example.com']
    assert result['updated_params']['bcc_recipients'] == ['bcc@example.com']
    assert result['updated_params']['reply_to'] == ['reply@example.com']

    mock_by_message_id.patch.assert_called_once()


@pytest.mark.asyncio
async def test_update_draft_message_subject_only(
    outlook_toolkit, mock_graph_service
):
    """Test updating only the subject of a draft message."""
    mock_by_message_id = mock_graph_service.me.messages.by_message_id()
    mock_by_message_id.patch.return_value = None

    result = await outlook_toolkit.outlook_update_draft_message(
        message_id='draft456',
        subject='New Subject Only',
    )

    assert result['status'] == 'success'
    assert result['message_id'] == 'draft456'
    assert result['updated_params']['subject'] == 'New Subject Only'
    assert 'content' not in result['updated_params']
    assert 'to_email' not in result['updated_params']

    mock_by_message_id.patch.assert_called_once()


@pytest.mark.asyncio
async def test_update_draft_message_failure(
    outlook_toolkit, mock_graph_service
):
    """Test update draft message failure."""
    mock_by_message_id = mock_graph_service.me.messages.by_message_id()
    mock_by_message_id.patch.side_effect = Exception(
        "API Error: Unable to update draft"
    )

    result = await outlook_toolkit.outlook_update_draft_message(
        message_id='draft123',
        subject='This update will fail',
    )

    assert 'error' in result
    assert 'Failed to update draft message' in result['error']
    assert 'API Error: Unable to update draft' in result['error']
