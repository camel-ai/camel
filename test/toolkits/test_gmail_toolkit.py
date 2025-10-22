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

from camel.toolkits import FunctionTool, GmailToolkit


@pytest.fixture
def mock_gmail_service():
    with patch('googleapiclient.discovery.build') as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_messages = MagicMock()
        mock_service.users().messages.return_value = mock_messages

        mock_labels = MagicMock()
        mock_service.users().labels.return_value = mock_labels

        mock_drafts = MagicMock()
        mock_service.users().drafts.return_value = mock_drafts

        yield mock_service


@pytest.fixture
def gmail_toolkit(mock_gmail_service):
    with (
        patch.dict(
            'os.environ',
            {'GMAIL_CREDENTIALS_PATH': 'mock_credentials.json'},
        ),
        patch.object(
            GmailToolkit,
            '_get_gmail_service',
            return_value=mock_gmail_service,
        ),
    ):
        toolkit = GmailToolkit()
        toolkit._service = mock_gmail_service
        yield toolkit


def test_send_email(gmail_toolkit, mock_gmail_service):
    send_mock = MagicMock()
    mock_gmail_service.users().messages().send.return_value = send_mock
    send_mock.execute.return_value = {
        'id': 'msg123',
        'threadId': 'thread123',
    }

    result = gmail_toolkit.send_email(
        to='test@example.com',
        subject='Test Subject',
        body='Test Body',
        cc='cc@example.com',
    )

    result_dict = eval(result)
    assert result_dict['message_id'] == 'msg123'
    assert result_dict['thread_id'] == 'thread123'
    mock_gmail_service.users().messages().send.assert_called_once()


def test_send_email_with_attachment(gmail_toolkit, mock_gmail_service):
    send_mock = MagicMock()
    mock_gmail_service.users().messages().send.return_value = send_mock
    send_mock.execute.return_value = {
        'id': 'msg123',
        'threadId': 'thread123',
    }

    with patch('pathlib.Path.exists', return_value=False):
        result = gmail_toolkit.send_email(
            to='test@example.com',
            subject='Test Subject',
            body='Test Body',
            attachment_paths=['/path/to/file.pdf'],
        )

    assert 'Error' in result
    assert 'not found' in result


def test_search_emails(gmail_toolkit, mock_gmail_service):
    list_mock = MagicMock()
    mock_gmail_service.users().messages().list.return_value = list_mock
    list_mock.execute.return_value = {
        'messages': [
            {'id': 'msg1', 'threadId': 'thread1'},
            {'id': 'msg2', 'threadId': 'thread2'},
        ]
    }

    result = gmail_toolkit.search_emails(
        query='from:test@example.com', max_results=10
    )

    import json

    result_list = json.loads(result)
    assert len(result_list) == 2
    assert result_list[0]['id'] == 'msg1'
    assert result_list[1]['id'] == 'msg2'

    mock_gmail_service.users().messages().list.assert_called_once()
    args, kwargs = mock_gmail_service.users().messages().list.call_args
    assert kwargs['q'] == 'from:test@example.com'
    assert kwargs['maxResults'] == 10


def test_search_emails_no_results(gmail_toolkit, mock_gmail_service):
    list_mock = MagicMock()
    mock_gmail_service.users().messages().list.return_value = list_mock
    list_mock.execute.return_value = {}

    result = gmail_toolkit.search_emails(query='from:nobody@example.com')

    import json

    result_dict = json.loads(result)
    assert 'message' in result_dict
    assert 'No emails found' in result_dict['message']


def test_read_email(gmail_toolkit, mock_gmail_service):
    get_mock = MagicMock()
    mock_gmail_service.users().messages().get.return_value = get_mock
    get_mock.execute.return_value = {
        'id': 'msg123',
        'threadId': 'thread123',
        'labelIds': ['INBOX'],
        'snippet': 'Test snippet',
        'payload': {
            'headers': [
                {'name': 'From', 'value': 'sender@example.com'},
                {'name': 'To', 'value': 'recipient@example.com'},
                {'name': 'Subject', 'value': 'Test Subject'},
                {'name': 'Date', 'value': 'Mon, 1 Jan 2024 12:00:00 +0000'},
            ],
            'body': {'data': 'VGVzdCBib2R5'},  # "Test body" in base64
        },
    }

    result = gmail_toolkit.read_email(message_id='msg123')

    import json

    result_dict = json.loads(result)
    assert result_dict['id'] == 'msg123'
    assert result_dict['subject'] == 'Test Subject'
    assert result_dict['from'] == 'sender@example.com'
    assert 'Test body' in result_dict['body']


def test_create_draft(gmail_toolkit, mock_gmail_service):
    create_mock = MagicMock()
    mock_gmail_service.users().drafts().create.return_value = create_mock
    create_mock.execute.return_value = {
        'id': 'draft123',
        'message': {'id': 'msg123'},
    }

    result = gmail_toolkit.create_draft(
        to='test@example.com', subject='Draft Subject', body='Draft Body'
    )

    import json

    result_dict = json.loads(result)
    assert result_dict['draft_id'] == 'draft123'
    assert result_dict['message_id'] == 'msg123'

    mock_gmail_service.users().drafts().create.assert_called_once()


def test_send_draft(gmail_toolkit, mock_gmail_service):
    send_mock = MagicMock()
    mock_gmail_service.users().drafts().send.return_value = send_mock
    send_mock.execute.return_value = {
        'id': 'msg123',
        'threadId': 'thread123',
    }

    result = gmail_toolkit.send_draft(draft_id='draft123')

    import json

    result_dict = json.loads(result)
    assert result_dict['message_id'] == 'msg123'
    assert result_dict['thread_id'] == 'thread123'

    mock_gmail_service.users().drafts().send.assert_called_once_with(
        userId='me', body={'id': 'draft123'}
    )


def test_delete_email(gmail_toolkit, mock_gmail_service):
    trash_mock = MagicMock()
    mock_gmail_service.users().messages().trash.return_value = trash_mock
    trash_mock.execute.return_value = {}

    result = gmail_toolkit.delete_email(message_id='msg123')

    assert 'msg123' in result
    assert 'trash' in result.lower()

    mock_gmail_service.users().messages().trash.assert_called_once_with(
        userId='me', id='msg123'
    )


def test_list_labels(gmail_toolkit, mock_gmail_service):
    list_mock = MagicMock()
    mock_gmail_service.users().labels().list.return_value = list_mock
    list_mock.execute.return_value = {
        'labels': [
            {'id': 'INBOX', 'name': 'INBOX'},
            {'id': 'SENT', 'name': 'SENT'},
            {'id': 'Label_1', 'name': 'Work'},
        ]
    }

    result = gmail_toolkit.list_labels()

    import json

    labels = json.loads(result)
    assert len(labels) == 3
    assert labels[0]['id'] == 'INBOX'
    assert labels[2]['name'] == 'Work'


def test_create_label(gmail_toolkit, mock_gmail_service):
    create_mock = MagicMock()
    mock_gmail_service.users().labels().create.return_value = create_mock
    create_mock.execute.return_value = {
        'id': 'Label_123',
        'name': 'New Label',
    }

    result = gmail_toolkit.create_label(name='New Label')

    import json

    label = json.loads(result)
    assert label['id'] == 'Label_123'
    assert label['name'] == 'New Label'

    mock_gmail_service.users().labels().create.assert_called_once()


def test_add_label_to_email(gmail_toolkit, mock_gmail_service):
    modify_mock = MagicMock()
    mock_gmail_service.users().messages().modify.return_value = modify_mock
    modify_mock.execute.return_value = {}

    result = gmail_toolkit.add_label_to_email(
        message_id='msg123', label_id='Label_1'
    )

    assert 'Label_1' in result
    assert 'msg123' in result
    assert 'added' in result.lower()

    mock_gmail_service.users().messages().modify.assert_called_once()
    args, kwargs = mock_gmail_service.users().messages().modify.call_args
    assert kwargs['body']['addLabelIds'] == ['Label_1']


def test_remove_label_from_email(gmail_toolkit, mock_gmail_service):
    modify_mock = MagicMock()
    mock_gmail_service.users().messages().modify.return_value = modify_mock
    modify_mock.execute.return_value = {}

    result = gmail_toolkit.remove_label_from_email(
        message_id='msg123', label_id='Label_1'
    )

    assert 'Label_1' in result
    assert 'msg123' in result
    assert 'removed' in result.lower()

    mock_gmail_service.users().messages().modify.assert_called_once()
    args, kwargs = mock_gmail_service.users().messages().modify.call_args
    assert kwargs['body']['removeLabelIds'] == ['Label_1']


def test_mark_as_read(gmail_toolkit, mock_gmail_service):
    modify_mock = MagicMock()
    mock_gmail_service.users().messages().modify.return_value = modify_mock
    modify_mock.execute.return_value = {}

    result = gmail_toolkit.mark_as_read(message_id='msg123')

    assert 'msg123' in result
    assert 'read' in result.lower()

    mock_gmail_service.users().messages().modify.assert_called_once()
    args, kwargs = mock_gmail_service.users().messages().modify.call_args
    assert kwargs['body']['removeLabelIds'] == ['UNREAD']


def test_mark_as_unread(gmail_toolkit, mock_gmail_service):
    modify_mock = MagicMock()
    mock_gmail_service.users().messages().modify.return_value = modify_mock
    modify_mock.execute.return_value = {}

    result = gmail_toolkit.mark_as_unread(message_id='msg123')

    assert 'msg123' in result
    assert 'unread' in result.lower()

    mock_gmail_service.users().messages().modify.assert_called_once()
    args, kwargs = mock_gmail_service.users().messages().modify.call_args
    assert kwargs['body']['addLabelIds'] == ['UNREAD']


def test_get_tools(gmail_toolkit):
    tools = gmail_toolkit.get_tools()

    assert len(tools) == 12
    assert all(isinstance(tool, FunctionTool) for tool in tools)

    assert tools[0].func == gmail_toolkit.send_email
    assert tools[1].func == gmail_toolkit.search_emails
    assert tools[2].func == gmail_toolkit.read_email
    assert tools[3].func == gmail_toolkit.create_draft
    assert tools[4].func == gmail_toolkit.send_draft
    assert tools[5].func == gmail_toolkit.delete_email
    assert tools[6].func == gmail_toolkit.list_labels
    assert tools[7].func == gmail_toolkit.create_label
    assert tools[8].func == gmail_toolkit.add_label_to_email
    assert tools[9].func == gmail_toolkit.remove_label_from_email
    assert tools[10].func == gmail_toolkit.mark_as_read
    assert tools[11].func == gmail_toolkit.mark_as_unread
