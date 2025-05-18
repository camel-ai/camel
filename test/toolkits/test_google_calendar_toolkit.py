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

from camel.toolkits import FunctionTool, GoogleCalendarToolkit


@pytest.fixture
def mock_calendar_service():
    with patch('googleapiclient.discovery.build') as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_events = MagicMock()
        mock_service.events.return_value = mock_events

        mock_calendars = MagicMock()
        mock_service.calendars.return_value = mock_calendars

        yield mock_service


@pytest.fixture
def calendar_toolkit(mock_calendar_service):
    with (
        patch('os.path.exists', return_value=True),
        patch('pickle.load'),
        patch('builtins.open'),
        patch.dict(
            'os.environ',
            {
                'GOOGLE_CLIENT_ID': 'mock_client_id',
                'GOOGLE_CLIENT_SECRET': 'mock_client_secret',
                'GOOGLE_REFRESH_TOKEN': 'mock_refresh_token',
            },
        ),
        patch.object(
            GoogleCalendarToolkit,
            '_get_calendar_service',
            return_value=mock_calendar_service,
        ),
    ):
        toolkit = GoogleCalendarToolkit()
        toolkit.service = (
            mock_calendar_service  # Ensure the service is set to our mock
        )
        yield toolkit


def test_create_event(calendar_toolkit, mock_calendar_service):
    event_mock = MagicMock()
    mock_calendar_service.events().insert.return_value = event_mock
    event_mock.execute.return_value = {
        'id': 'event123',
        'summary': 'Test Event',
        'start': {'dateTime': '2024-03-30T10:00:00'},
        'end': {'dateTime': '2024-03-30T11:00:00'},
        'htmlLink': 'https://calendar.google.com/event?id=event123',
    }

    result = calendar_toolkit.create_event(
        event_title='Test Event',
        start_time='2024-03-30T10:00:00',
        end_time='2024-03-30T11:00:00',
        description='Test Description',
        location='Test Location',
        attendees_email=['test@example.com'],
        timezone='UTC',
    )

    assert result['Event ID'] == 'event123'
    assert result['EventTitle'] == 'Test Event'  # Updated field name
    assert result['Start Time'] == '2024-03-30T10:00:00'
    assert result['End Time'] == '2024-03-30T11:00:00'
    assert result['Link'] == 'https://calendar.google.com/event?id=event123'

    mock_calendar_service.events().insert.assert_called_once()
    args, kwargs = mock_calendar_service.events().insert.call_args
    assert kwargs['calendarId'] == 'primary'
    event_body = kwargs['body']
    assert event_body['summary'] == 'Test Event'
    assert event_body['description'] == 'Test Description'
    assert event_body['location'] == 'Test Location'
    assert event_body['start']['dateTime'] == '2024-03-30T10:00:00'
    assert event_body['end']['dateTime'] == '2024-03-30T11:00:00'
    assert event_body['attendees'][0]['email'] == 'test@example.com'


def test_create_event_invalid_time_format(calendar_toolkit):
    result = calendar_toolkit.create_event(
        event_title='Test Event',
        start_time='2024/03/30 10:00',  # Invalid format
        end_time='2024-03-30T11:00:00',
    )

    assert "error" in result
    assert "Time format error" in result["error"]


def test_create_event_invalid_email(calendar_toolkit):
    result = calendar_toolkit.create_event(
        event_title='Test Event',
        start_time='2024-03-30T10:00:00',
        end_time='2024-03-30T11:00:00',
        attendees_email=['invalid-email'],
    )

    assert "error" in result
    assert "Invalid email address" in result["error"]


def test_create_event_failure(calendar_toolkit, mock_calendar_service):
    event_mock = MagicMock()
    mock_calendar_service.events().insert.return_value = event_mock
    event_mock.execute.side_effect = Exception("API Error")

    result = calendar_toolkit.create_event(
        event_title='Test Event',
        start_time='2024-03-30T10:00:00',
        end_time='2024-03-30T11:00:00',
    )

    assert "error" in result
    assert "Failed to create event" in result["error"]


def test_get_events(calendar_toolkit, mock_calendar_service):
    events_mock = MagicMock()
    mock_calendar_service.events().list.return_value = events_mock
    events_mock.execute.return_value = {
        'items': [
            {
                'id': 'event123',
                'summary': 'Test Event 1',
                'start': {'dateTime': '2024-03-30T10:00:00Z'},
                'htmlLink': 'https://calendar.google.com/event?id=event123',
            },
            {
                'id': 'event456',
                'summary': 'Test Event 2',
                'start': {'dateTime': '2024-03-30T13:00:00Z'},
                'htmlLink': 'https://calendar.google.com/event?id=event456',
            },
        ]
    }

    result = calendar_toolkit.get_events(
        max_results=10, time_min='2024-03-30T00:00:00Z'
    )

    assert len(result) == 2
    assert result[0]['Event ID'] == 'event123'
    assert result[0]['Summary'] == 'Test Event 1'
    assert result[0]['Start Time'] == '2024-03-30T10:00:00Z'
    assert result[1]['Event ID'] == 'event456'
    assert result[1]['Summary'] == 'Test Event 2'

    mock_calendar_service.events().list.assert_called_once()
    args, kwargs = mock_calendar_service.events().list.call_args
    assert kwargs['calendarId'] == 'primary'
    assert kwargs['timeMin'] == '2024-03-30T00:00:00Z'
    assert kwargs['maxResults'] == 10
    assert kwargs['singleEvents'] is True
    assert kwargs['orderBy'] == 'startTime'


def test_get_events_with_default_time(calendar_toolkit, mock_calendar_service):
    events_mock = MagicMock()
    mock_calendar_service.events().list.return_value = events_mock
    events_mock.execute.return_value = {'items': []}

    calendar_toolkit.get_events(max_results=5)

    args, kwargs = mock_calendar_service.events().list.call_args
    assert kwargs['timeMin'].endswith('Z')
    assert kwargs['maxResults'] == 5


def test_get_events_empty_result(calendar_toolkit, mock_calendar_service):
    events_mock = MagicMock()
    mock_calendar_service.events().list.return_value = events_mock
    events_mock.execute.return_value = {'items': []}

    result = calendar_toolkit.get_events()

    assert result == []


def test_get_events_failure(calendar_toolkit, mock_calendar_service):
    events_mock = MagicMock()
    mock_calendar_service.events().list.return_value = events_mock
    events_mock.execute.side_effect = Exception("API Error")

    result = calendar_toolkit.get_events()

    assert "error" in result
    assert "Failed to retrieve events" in result["error"]


def test_update_event(calendar_toolkit, mock_calendar_service):
    get_mock = MagicMock()
    update_mock = MagicMock()
    mock_calendar_service.events().get.return_value = get_mock
    mock_calendar_service.events().update.return_value = update_mock

    get_mock.execute.return_value = {
        'id': 'event123',
        'summary': 'Old Title',
        'description': 'Old Description',
        'location': 'Old Location',
        'start': {'dateTime': '2024-03-30T10:00:00Z'},
        'end': {'dateTime': '2024-03-30T11:00:00Z'},
    }

    update_mock.execute.return_value = {
        'id': 'event123',
        'summary': 'New Title',
        'description': 'New Description',
        'location': 'New Location',
        'start': {'dateTime': '2024-03-30T12:00:00Z'},
        'end': {'dateTime': '2024-03-30T13:00:00Z'},
        'htmlLink': 'https://calendar.google.com/event?id=event123',
    }

    result = calendar_toolkit.update_event(
        event_id='event123',
        event_title='New Title',
        description='New Description',
        location='New Location',
        start_time='2024-03-30T12:00:00Z',
        end_time='2024-03-30T13:00:00Z',
    )

    assert result['Event ID'] == 'event123'
    assert result['Summary'] == 'New Title'
    assert result['Start Time'] == '2024-03-30T12:00:00Z'
    assert result['End Time'] == '2024-03-30T13:00:00Z'

    mock_calendar_service.events().get.assert_called_once_with(
        calendarId='primary', eventId='event123'
    )

    args, kwargs = mock_calendar_service.events().update.call_args
    assert kwargs['calendarId'] == 'primary'
    assert kwargs['eventId'] == 'event123'
    event_body = kwargs['body']
    assert event_body['summary'] == 'New Title'
    assert event_body['description'] == 'New Description'
    assert event_body['location'] == 'New Location'
    assert event_body['start']['dateTime'] == '2024-03-30T12:00:00Z'
    assert event_body['end']['dateTime'] == '2024-03-30T13:00:00Z'


def test_update_event_partial(calendar_toolkit, mock_calendar_service):
    get_mock = MagicMock()
    update_mock = MagicMock()
    mock_calendar_service.events().get.return_value = get_mock
    mock_calendar_service.events().update.return_value = update_mock

    get_mock.execute.return_value = {
        'id': 'event123',
        'summary': 'Old Title',
        'description': 'Description',
        'location': 'Location',
        'start': {'dateTime': '2024-03-30T10:00:00Z'},
        'end': {'dateTime': '2024-03-30T11:00:00Z'},
    }

    update_mock.execute.return_value = {
        'id': 'event123',
        'summary': 'New Title',
        'description': 'Description',
        'location': 'Location',
        'start': {'dateTime': '2024-03-30T10:00:00Z'},
        'end': {'dateTime': '2024-03-30T11:00:00Z'},
        'htmlLink': 'https://calendar.google.com/event?id=event123',
    }

    _ = calendar_toolkit.update_event(
        event_id='event123', event_title='New Title'
    )

    # Verify only summary was updated
    args, kwargs = mock_calendar_service.events().update.call_args
    event_body = kwargs['body']
    assert event_body['summary'] == 'New Title'
    assert event_body['description'] == 'Description'  # Unchanged
    assert event_body['location'] == 'Location'  # Unchanged
    assert (
        event_body['start']['dateTime'] == '2024-03-30T10:00:00Z'
    )  # Unchanged


def test_update_event_failure(calendar_toolkit, mock_calendar_service):
    get_mock = MagicMock()
    mock_calendar_service.events().get.return_value = get_mock
    get_mock.execute.side_effect = Exception("API Error")

    with pytest.raises(ValueError) as excinfo:
        calendar_toolkit.update_event(
            event_id='event123', event_title='New Title'
        )

    assert "Failed to update event" in str(excinfo.value)


def test_delete_event(calendar_toolkit, mock_calendar_service):
    delete_mock = MagicMock()
    mock_calendar_service.events().delete.return_value = delete_mock
    delete_mock.execute.return_value = {}

    result = calendar_toolkit.delete_event(event_id='event123')

    assert "Event deleted successfully" in result
    assert "event123" in result

    mock_calendar_service.events().delete.assert_called_once_with(
        calendarId='primary', eventId='event123'
    )


def test_delete_event_failure(calendar_toolkit, mock_calendar_service):
    delete_mock = MagicMock()
    mock_calendar_service.events().delete.return_value = delete_mock
    delete_mock.execute.side_effect = Exception("API Error")

    with pytest.raises(ValueError) as excinfo:
        calendar_toolkit.delete_event(event_id='event123')

    assert "Failed to delete event" in str(excinfo.value)


def test_get_calendar_details(calendar_toolkit, mock_calendar_service):
    get_mock = MagicMock()
    mock_calendar_service.calendars().get.return_value = get_mock

    get_mock.execute.return_value = {
        'id': 'primary',
        'summary': 'My Calendar',
        'description': 'Personal Calendar',
        'timeZone': 'America/New_York',
        'accessRole': 'owner',
    }

    result = calendar_toolkit.get_calendar_details()

    assert result['Calendar ID'] == 'primary'
    assert result['Summary'] == 'My Calendar'
    assert result['Description'] == 'Personal Calendar'
    assert result['Time Zone'] == 'America/New_York'
    assert result['Access Role'] == 'owner'

    mock_calendar_service.calendars().get.assert_called_once_with(
        calendarId='primary'
    )


def test_get_calendar_details_failure(calendar_toolkit, mock_calendar_service):
    get_mock = MagicMock()
    mock_calendar_service.calendars().get.return_value = get_mock
    get_mock.execute.side_effect = Exception("API Error")

    with pytest.raises(ValueError) as excinfo:
        calendar_toolkit.get_calendar_details()

    assert "Failed to retrieve calendar details" in str(excinfo.value)


def test_get_tools(calendar_toolkit):
    tools = calendar_toolkit.get_tools()

    assert len(tools) == 5
    assert all(isinstance(tool, FunctionTool) for tool in tools)

    assert tools[0].func == calendar_toolkit.create_event
    assert tools[1].func == calendar_toolkit.get_events
    assert tools[2].func == calendar_toolkit.update_event
    assert tools[3].func == calendar_toolkit.delete_event
    assert tools[4].func == calendar_toolkit.get_calendar_details
