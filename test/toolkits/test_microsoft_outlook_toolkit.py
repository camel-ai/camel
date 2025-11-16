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

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camel.toolkits import OutlookToolkit

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_graph_service():
    """Mock Microsoft Graph API service."""
    with patch("msgraph.GraphServiceClient") as mock_service_client:
        mock_client = MagicMock()
        mock_service_client.return_value = mock_client

        # Mock me endpoint
        mock_me = MagicMock()
        mock_client.me = mock_me

        # Mock messages endpoint
        mock_messages = MagicMock()
        mock_me.messages = mock_messages

        # Mock send_mail endpoint
        mock_send_mail = MagicMock()
        mock_me.send_mail = mock_send_mail
        mock_send_mail.post = AsyncMock()

        # Mock messages.get for listing messages
        mock_messages.get = AsyncMock()

        # Mock messages.post for creating drafts
        mock_messages.post = AsyncMock()

        # Mock messages.by_message_id for specific message operations
        mock_by_message_id = MagicMock()
        mock_messages.by_message_id = MagicMock(
            return_value=mock_by_message_id
        )

        # Mock get message by ID
        mock_by_message_id.get = AsyncMock()

        # Mock send draft
        mock_send = MagicMock()
        mock_by_message_id.send = mock_send
        mock_send.post = AsyncMock()

        # Mock delete message
        mock_by_message_id.delete = AsyncMock()

        # Mock move message
        mock_move = MagicMock()
        mock_by_message_id.move = mock_move
        mock_move.post = AsyncMock()

        # Mock attachments
        mock_attachments = MagicMock()
        mock_by_message_id.attachments = mock_attachments
        mock_attachments.get = AsyncMock()

        # Mock mail_folders for folder-specific operations
        mock_mail_folders = MagicMock()
        mock_me.mail_folders = mock_mail_folders

        # Mock by_mail_folder_id
        mock_by_folder_id = MagicMock()
        mock_mail_folders.by_mail_folder_id = MagicMock(
            return_value=mock_by_folder_id
        )

        # Mock folder messages
        mock_folder_messages = MagicMock()
        mock_by_folder_id.messages = mock_folder_messages
        mock_folder_messages.get = AsyncMock()

        yield mock_client


@pytest.fixture
def outlook_toolkit(mock_graph_service):
    """Fixture that provides a mocked OutlookToolkit instance."""
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
            OutlookToolkit,
            '_authenticate',
            return_value=mock_credentials,
        ),
        patch.object(
            OutlookToolkit,
            '_get_graph_client',
            return_value=mock_graph_service,
        ),
    ):
        toolkit = OutlookToolkit()
        toolkit.client = mock_graph_service
        yield toolkit


async def test_send_email(outlook_toolkit, mock_graph_service):
    """Test sending an email successfully."""
    mock_graph_service.me.send_mail.post.return_value = None

    result = await outlook_toolkit.send_email(
        to_email=['test@example.com'],
        subject='Test Subject',
        content='Test Body',
    )

    assert result['status'] == 'success'
    assert result['message'] == 'Email sent successfully'
    assert result['recipients'] == ['test@example.com']
    assert result['subject'] == 'Test Subject'

    mock_graph_service.me.send_mail.post.assert_called_once()


async def test_send_email_with_attachments(
    outlook_toolkit, mock_graph_service
):
    """Test sending an email with attachments."""
    mock_graph_service.me.send_mail.post.return_value = None

    with (
        patch('os.path.isfile', return_value=True),
        patch('builtins.open', create=True) as mock_open,
    ):
        mock_open.return_value.__enter__.return_value.read.return_value = (
            b'test content'
        )

        result = await outlook_toolkit.send_email(
            to_email=['test@example.com'],
            subject='Test Subject',
            content='Test Body',
            attachments=['/path/to/file.txt'],
        )

        assert result['status'] == 'success'
        mock_graph_service.me.send_mail.post.assert_called_once()


async def test_send_email_invalid_email(outlook_toolkit):
    """Test sending email with invalid email address."""
    result = await outlook_toolkit.send_email(
        to_email=['invalid-email'],
        subject='Test Subject',
        content='Test Body',
    )

    assert 'error' in result
    assert 'Invalid email address' in result['error']


async def test_send_email_failure(outlook_toolkit, mock_graph_service):
    """Test sending email failure."""
    mock_graph_service.me.send_mail.post.side_effect = Exception("API Error")

    result = await outlook_toolkit.send_email(
        to_email=['test@example.com'],
        subject='Test Subject',
        content='Test Body',
    )

    assert 'error' in result
    assert 'Failed to send email' in result['error']


async def test_create_email_draft(outlook_toolkit, mock_graph_service):
    """Test creating an email draft."""
    mock_draft_result = MagicMock()
    mock_draft_result.id = 'draft123'
    mock_graph_service.me.messages.post.return_value = mock_draft_result

    result = await outlook_toolkit.create_draft_email(
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


async def test_create_email_draft_with_attachments(
    outlook_toolkit, mock_graph_service
):
    """Test creating an email draft with attachments."""
    mock_draft_result = MagicMock()
    mock_draft_result.id = 'draft123'
    mock_graph_service.me.messages.post.return_value = mock_draft_result

    with (
        patch('os.path.isfile', return_value=True),
        patch('builtins.open', create=True) as mock_open,
    ):
        mock_open.return_value.__enter__.return_value.read.return_value = (
            b'test content'
        )

        result = await outlook_toolkit.create_draft_email(
            to_email=['test@example.com'],
            subject='Test Subject',
            content='Test Body',
            attachments=['/path/to/file.txt'],
        )

        assert result['status'] == 'success'
        assert result['draft_id'] == 'draft123'
        mock_graph_service.me.messages.post.assert_called_once()


async def test_create_email_draft_invalid_email(outlook_toolkit):
    """Test creating draft with invalid email address."""
    result = await outlook_toolkit.create_draft_email(
        to_email=['invalid-email'],
        subject='Test Subject',
        content='Test Body',
    )

    assert 'error' in result
    assert 'Invalid email address' in result['error']


async def test_create_email_draft_failure(outlook_toolkit, mock_graph_service):
    """Test creating email draft failure."""
    mock_graph_service.me.messages.post.side_effect = Exception("API Error")

    result = await outlook_toolkit.create_draft_email(
        to_email=['test@example.com'],
        subject='Test Subject',
        content='Test Body',
    )

    assert 'error' in result
    assert 'Failed to create draft email' in result['error']


async def test_send_draft_email(outlook_toolkit, mock_graph_service):
    """Test sending a draft email."""
    mock_graph_service.me.messages.by_message_id().send.post.return_value = (
        None
    )

    result = await outlook_toolkit.send_draft_email(draft_id='draft123')

    assert result['status'] == 'success'
    assert result['message'] == 'Draft email sent successfully'
    assert result['draft_id'] == 'draft123'

    mock_graph_service.me.messages.by_message_id().send.post.assert_called_once()


async def test_send_draft_email_failure(outlook_toolkit, mock_graph_service):
    """Test sending draft email failure."""
    mock_graph_service.me.messages.by_message_id().send.post.side_effect = (
        Exception("API Error")
    )

    result = await outlook_toolkit.send_draft_email(draft_id='draft123')

    assert 'error' in result
    assert 'Failed to send draft email' in result['error']
