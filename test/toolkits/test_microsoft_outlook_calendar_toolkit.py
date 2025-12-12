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

from camel.toolkits import OutlookCalendarToolkit


@pytest.fixture
def mock_graph_client():
    """Mock Microsoft Graph API client."""
    mock_client = MagicMock()
    return mock_client


@pytest.fixture
def outlook_calendar_toolkit(mock_graph_client):
    """Fixture that provides a mocked OutlookCalendarToolkit instance."""
    mock_credentials = MagicMock()
    mock_credentials.valid = True

    # Mock the MicrosoftAuthenticator used inside OutlookCalendarToolkit
    mock_authenticator = MagicMock()
    mock_authenticator.authenticate.return_value = mock_credentials
    mock_authenticator.get_graph_client.return_value = mock_graph_client

    with (
        patch.dict(
            'os.environ',
            {
                'MICROSOFT_TENANT_ID': 'mock_tenant_id',
                'MICROSOFT_CLIENT_ID': 'mock_client_id',
                'MICROSOFT_CLIENT_SECRET': 'mock_client_secret',
            },
        ),
        patch(
            'camel.toolkits.microsoft_outlook_toolkits'
            '.microsoft_outlook_calendar_toolkit.MicrosoftAuthenticator',
            return_value=mock_authenticator,
        ),
    ):
        toolkit = OutlookCalendarToolkit()
        yield toolkit


class TestMapColorToCalendarColor:
    """Tests for _map_color_to_CalendarColor method."""

    def test_map_color_valid(self, outlook_calendar_toolkit):
        """Test mapping a valid color."""
        from msgraph.generated.models.calendar_color import CalendarColor

        result = outlook_calendar_toolkit._map_color_to_CalendarColor(
            'lightBlue'
        )
        assert result == CalendarColor.LightBlue

    def test_map_color_invalid_returns_auto(self, outlook_calendar_toolkit):
        """Test that invalid color string returns Auto as default."""
        from msgraph.generated.models.calendar_color import CalendarColor

        result = outlook_calendar_toolkit._map_color_to_CalendarColor(
            'invalidColor'
        )
        assert result == CalendarColor.Auto


@pytest.mark.asyncio
class TestCreateCalendar:
    """Tests for create_calendar method."""

    async def test_create_calendar_success(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test successful calendar creation."""
        from msgraph.generated.models.calendar_color import CalendarColor

        # Setup mock response
        mock_result = MagicMock()
        mock_result.id = 'Calendar ID'
        mock_result.name = 'Test Calendar'

        # Create async mock for the post method
        async_post_mock = AsyncMock(return_value=mock_result)
        mock_graph_client.me.calendars.post = async_post_mock

        # Call the method
        result = await outlook_calendar_toolkit.outlook_create_calendar(
            name='Test Calendar', color='lightBlue'
        )

        # Verify the result
        assert result['status'] == 'success'
        assert result['message'] == 'Calendar created successfully.'
        assert result['calendar_id'] == 'Calendar ID'
        assert result['calendar_name'] == 'Test Calendar'

        # Verify the post method was called with correct Calendar object
        async_post_mock.assert_called_once()
        calendar_arg = async_post_mock.call_args[0][0]
        assert calendar_arg.name == 'Test Calendar'
        assert calendar_arg.color == CalendarColor.LightBlue

    async def test_create_calendar_with_default_color(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test calendar creation with default color (auto)."""
        from msgraph.generated.models.calendar_color import CalendarColor

        # Setup mock response
        mock_result = MagicMock()
        mock_result.id = 'Calendar ID'
        mock_result.name = 'My Calendar'

        async_post_mock = AsyncMock(return_value=mock_result)
        mock_graph_client.me.calendars.post = async_post_mock

        # Call the method with default color
        result = await outlook_calendar_toolkit.outlook_create_calendar(
            name='My Calendar'
        )

        # Verify the result
        assert result['status'] == 'success'
        assert result['calendar_id'] == 'Calendar ID'
        assert result['calendar_name'] == 'My Calendar'

        # Verify the Calendar object was created with default color
        calendar_arg = async_post_mock.call_args[0][0]
        assert calendar_arg.name == 'My Calendar'
        assert calendar_arg.color == CalendarColor.Auto

    async def test_create_calendar_api_error(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test calendar creation when API raises an exception."""
        # Setup mock to raise an exception
        async_post_mock = AsyncMock(
            side_effect=Exception('API connection failed')
        )
        mock_graph_client.me.calendars.post = async_post_mock

        # Call the method
        result = await outlook_calendar_toolkit.outlook_create_calendar(
            name='Error Calendar'
        )

        # Verify error is returned
        assert 'error' in result
        assert 'Failed to create calendar' in result['error']
        assert 'API connection failed' in result['error']


@pytest.mark.asyncio
class TestDeleteCalendar:
    """Tests for delete_calendar method."""

    async def test_delete_calendar_success(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test successful calendar deletion."""
        # Create async mock for the delete method
        async_delete_mock = AsyncMock(return_value=None)
        mock_graph_client.me.calendars.by_calendar_id.return_value.delete = (
            async_delete_mock
        )

        # Call the method
        result = await outlook_calendar_toolkit.outlook_delete_calendar(
            calendar_id='Calendar ID'
        )

        # Verify the result
        assert result['status'] == 'success'
        assert result['message'] == 'Calendar deleted successfully.'
        assert result['calendar_id'] == 'Calendar ID'

    async def test_delete_calendar_not_found(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test calendar deletion when calendar is not found."""
        # Setup mock to raise a not found error
        async_delete_mock = AsyncMock(
            side_effect=Exception('Calendar not found')
        )
        mock_graph_client.me.calendars.by_calendar_id.return_value.delete = (
            async_delete_mock
        )

        # Call the method
        result = await outlook_calendar_toolkit.outlook_delete_calendar(
            calendar_id='Invalid ID'
        )

        # Verify error is returned
        assert 'error' in result
        assert 'Failed to delete calendar' in result['error']
        assert 'Calendar not found' in result['error']


def mock_single_calendar_response():
    from msgraph.generated.models.calendar_color import CalendarColor

    mock_owner = MagicMock(address="address")
    mock_owner.name = "name"
    calendar_response = MagicMock(
        color=CalendarColor.Auto,
        is_default_calendar="is_default_calendar",
        can_edit="can_edit",
        can_share="can_share",
        can_view_private_items="can_view_private_items",
        is_removable="is_removable",
        is_tallying_responses="is_tallying_responses",
        owner=mock_owner,
    )
    calendar_response.id = "id"
    calendar_response.name = "name"

    return calendar_response


@pytest.mark.asyncio
class TestGetCalendar:
    """Tests for get_calendar method."""

    async def test_get_calendar_success(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test successful calendar retrieval."""
        mock_calendar = mock_single_calendar_response()

        async_get_mock = AsyncMock(return_value=mock_calendar)
        mock_graph_client.me.calendars.by_calendar_id.return_value.get = (
            async_get_mock
        )

        result = await outlook_calendar_toolkit.outlook_get_calendar(
            calendar_id='id'
        )

        assert result['status'] == 'success'
        details = result['calendar_details']
        assert details['id'] == 'id'
        assert details['name'] == 'name'
        assert details['color'] == 'auto'
        assert details['owner_email'] == 'address'
        assert details['owner_name'] == 'name'
        assert details['is_default_calendar'] == 'is_default_calendar'
        assert details['can_edit'] == 'can_edit'
        assert details['can_share'] == 'can_share'
        assert details['can_view_private_items'] == 'can_view_private_items'
        assert details['is_removable'] == 'is_removable'
        assert details['is_tallying_responses'] == 'is_tallying_responses'

    async def test_get_calendar_failure(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test calendar retrieval when calendar is not found."""
        # Setup mock to raise an exception
        async_get_mock = AsyncMock(side_effect=Exception('Calendar not found'))
        mock_graph_client.me.calendars.by_calendar_id.return_value.get = (
            async_get_mock
        )

        # Call the method
        result = await outlook_calendar_toolkit.outlook_get_calendar(
            calendar_id='incorrect_id'
        )

        # Verify error is returned
        assert 'error' in result
        assert 'Failed to get calendar' in result['error']
        assert 'Calendar not found' in result['error']


@pytest.mark.asyncio
class TestListCalendars:
    """Tests for list_calendars method."""

    async def test_list_calendars_success(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test successful calendar listing."""
        mock_calendar = mock_single_calendar_response()

        mock_result = MagicMock()
        mock_result.value = [mock_calendar]

        async_get_mock = AsyncMock(return_value=mock_result)
        mock_graph_client.me.calendars.get = async_get_mock

        result = await outlook_calendar_toolkit.outlook_list_calendars()

        assert result['status'] == 'success'
        assert result['total_count'] == 1
        assert result['skip'] == 0
        assert result['top'] == 10
        assert len(result['calendars']) == 1

        details = result['calendars'][0]
        assert details['id'] == 'id'
        assert details['name'] == 'name'
        assert details['color'] == 'auto'
        assert details['owner_email'] == 'address'
        assert details['owner_name'] == 'name'

    async def test_list_calendars_failure(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test listing calendars when API raises an exception."""
        async_get_mock = AsyncMock(
            side_effect=Exception('API connection failed')
        )
        mock_graph_client.me.calendars.get = async_get_mock

        result = await outlook_calendar_toolkit.outlook_list_calendars()

        assert 'error' in result
        assert 'Failed to list calendars' in result['error']
        assert 'API connection failed' in result['error']


@pytest.mark.asyncio
class TestUpdateCalendar:
    """Tests for update_calendar method."""

    async def test_update_calendar_name_success(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test successful calendar name update."""
        async_patch_mock = AsyncMock(return_value=None)
        mock_graph_client.me.calendars.by_calendar_id.return_value.patch = (
            async_patch_mock
        )

        result = await outlook_calendar_toolkit.outlook_update_calendar(
            calendar_id='calendar_id', name='Updated Calendar Name'
        )

        assert result['status'] == 'success'
        assert result['updated_values']['name'] == 'Updated Calendar Name'

        calendar_arg = async_patch_mock.call_args[0][0]
        assert calendar_arg.name == 'Updated Calendar Name'

    async def test_update_calendar_color_success(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test successful calendar color update."""
        from msgraph.generated.models.calendar_color import CalendarColor

        async_patch_mock = AsyncMock(return_value=None)
        mock_graph_client.me.calendars.by_calendar_id.return_value.patch = (
            async_patch_mock
        )

        result = await outlook_calendar_toolkit.outlook_update_calendar(
            calendar_id='calendar_id', color='lightBlue'
        )

        assert result['status'] == 'success'
        assert result['updated_values']['color'] == CalendarColor.LightBlue

        calendar_arg = async_patch_mock.call_args[0][0]
        assert calendar_arg.color == CalendarColor.LightBlue

    async def test_update_calendar_failure(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test update calendar when API raises an exception."""
        async_patch_mock = AsyncMock(
            side_effect=Exception('Calendar not found')
        )
        mock_graph_client.me.calendars.by_calendar_id.return_value.patch = (
            async_patch_mock
        )

        result = await outlook_calendar_toolkit.outlook_update_calendar(
            calendar_id='invalid_id', name='New Name'
        )

        assert 'error' in result
        assert 'Failed to update calendar' in result['error']


class TestEventHelperMethods:
    """Tests for private helper methods used in event creation."""

    def test_create_attendees(self, outlook_calendar_toolkit):
        """Test creating attendees with various formats and types."""
        from msgraph.generated.models.attendee_type import AttendeeType

        # Test simple email format
        result = outlook_calendar_toolkit._create_attendees(
            ["test@gmail.com"], "required"
        )
        assert result[0].email_address.address == "test@gmail.com"
        assert result[0].type == AttendeeType.Required

        # Test 'Name <email>' format
        result = outlook_calendar_toolkit._create_attendees(
            ["John Doe <john@gmail.com>"], "optional"
        )
        assert result[0].email_address.address == "john@gmail.com"
        assert result[0].email_address.name == "John Doe"
        assert result[0].type == AttendeeType.Optional

        # Test resource type
        result = outlook_calendar_toolkit._create_attendees(
            ["room@test.com"], "resource"
        )
        assert result[0].type == AttendeeType.Resource

        # Test invalid type defaults to Required
        result = outlook_calendar_toolkit._create_attendees(
            ["test@gmail.com"], "invalid_type"
        )
        assert result[0].type == AttendeeType.Required

        # Test empty list
        result = outlook_calendar_toolkit._create_attendees([], "required")
        assert len(result) == 0

    def test_create_locations(self, outlook_calendar_toolkit):
        """Test creating locations."""
        result = outlook_calendar_toolkit._create_locations(
            ["Room A", "Building 1"]
        )
        assert len(result) == 2
        assert result[0].display_name == "Room A"
        assert result[1].display_name == "Building 1"

        # Test empty list
        assert len(outlook_calendar_toolkit._create_locations([])) == 0

    def test_create_importance(self, outlook_calendar_toolkit):
        """Test creating importance with all values and case insensitivity."""
        from msgraph.generated.models.importance import Importance

        toolkit = outlook_calendar_toolkit
        assert toolkit._create_importance("low") == Importance.Low
        assert toolkit._create_importance("normal") == Importance.Normal
        assert toolkit._create_importance("high") == Importance.High
        assert toolkit._create_importance("HIGH") == Importance.High  # case
        assert toolkit._create_importance("invalid") == Importance.Normal

    def test_create_show_as_status(self, outlook_calendar_toolkit):
        """Test creating show_as status with all values."""
        from msgraph.generated.models.free_busy_status import FreeBusyStatus

        toolkit = outlook_calendar_toolkit
        assert toolkit._create_show_as_status("free") == FreeBusyStatus.Free
        assert toolkit._create_show_as_status("busy") == FreeBusyStatus.Busy
        assert toolkit._create_show_as_status("oof") == FreeBusyStatus.Oof
        assert toolkit._create_show_as_status("invalid") == FreeBusyStatus.Busy

        # Test tentative
        result = toolkit._create_show_as_status("tentative")
        assert result == FreeBusyStatus.Tentative

        # Test workingelsewhere
        result = toolkit._create_show_as_status("workingelsewhere")
        assert result == FreeBusyStatus.WorkingElsewhere

        # Test unknown
        result = toolkit._create_show_as_status("unknown")
        assert result == FreeBusyStatus.Unknown

        # Test case insensitivity
        result = toolkit._create_show_as_status("FREE")
        assert result == FreeBusyStatus.Free

    def test_build_event(self, outlook_calendar_toolkit):
        """Test building an event with all options."""
        from msgraph.generated.models.attendee_type import AttendeeType
        from msgraph.generated.models.free_busy_status import FreeBusyStatus
        from msgraph.generated.models.importance import Importance

        event = outlook_calendar_toolkit._build_event(
            subject="Full Meeting",
            start_time="2025-12-10T10:00:00",
            end_time="2025-12-10T11:00:00",
            timezone="Pacific Standard Time",
            is_all_day=False,
            description="Meeting details",
            locations=["Room A", "Room B"],
            required_attendees=["req@test.com"],
            optional_attendees=["opt@test.com"],
            resource_attendees=["room@test.com"],
            is_online_meeting=True,
            importance="high",
            show_as="busy",
        )

        # Verify basic fields
        assert event.subject == "Full Meeting"
        assert event.start.date_time == "2025-12-10T10:00:00"
        assert event.start.time_zone == "Pacific Standard Time"
        assert event.end.date_time == "2025-12-10T11:00:00"

        # Verify body
        assert event.body.content == "Meeting details"

        # Verify locations
        assert len(event.locations) == 2
        assert event.locations[0].display_name == "Room A"
        assert event.locations[1].display_name == "Room B"

        # Verify attendees
        assert len(event.attendees) == 3
        attendee_types = [a.type for a in event.attendees]
        assert event.attendees[0].email_address.address == "req@test.com"
        assert AttendeeType.Required in attendee_types
        assert event.attendees[1].email_address.address == "opt@test.com"
        assert AttendeeType.Optional in attendee_types
        assert event.attendees[2].email_address.address == "room@test.com"
        assert AttendeeType.Resource in attendee_types

        # Verify other options
        assert event.is_online_meeting is True
        assert event.importance == Importance.High
        assert event.show_as == FreeBusyStatus.Busy


@pytest.mark.asyncio
class TestCreateCalendarEvent:
    """Tests for create_calendar_event method."""

    async def test_create_calendar_event_success(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test successful calendar event creation with all parameters."""
        # Setup mock response
        mock_result = MagicMock()
        mock_result.id = 'event_id'
        mock_result.subject = 'Team Meeting'
        mock_result.start.date_time = '2025-12-10T10:00:00'
        mock_result.end.date_time = '2025-12-10T11:00:00'

        async_post_mock = AsyncMock(return_value=mock_result)
        mock_graph_client.me.events.post = async_post_mock

        # Call the method with all parameters
        result = await outlook_calendar_toolkit.outlook_create_calendar_event(
            subject='Team Meeting',
            start_time='2025-12-10T10:00:00',
            end_time='2025-12-10T11:00:00',
            timezone='Pacific Standard Time',
            description='<p>Discussion topics</p>',
            locations=['Conference Room A'],
            required_attendees=['john@test.com'],
            optional_attendees=['jane@test.com'],
            is_online_meeting=True,
            importance='high',
            show_as='busy',
        )

        # Verify the result
        assert result['status'] == 'success'
        assert result['message'] == 'Calendar event created successfully.'
        assert result['event_id'] == 'event_id'
        assert result['event_subject'] == 'Team Meeting'

        # Verify the event object passed to post
        async_post_mock.assert_called_once()
        event_arg = async_post_mock.call_args[0][0]

        # Verify event properties
        assert event_arg.subject == 'Team Meeting'
        assert event_arg.start.date_time == '2025-12-10T10:00:00'
        assert event_arg.start.time_zone == 'Pacific Standard Time'
        assert event_arg.end.date_time == '2025-12-10T11:00:00'
        assert event_arg.body.content == '<p>Discussion topics</p>'
        assert len(event_arg.locations) == 1
        assert event_arg.locations[0].display_name == 'Conference Room A'
        assert len(event_arg.attendees) == 2
        assert event_arg.is_online_meeting is True

    async def test_create_calendar_event_in_specific_calendar(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test creating event in a specific calendar."""
        mock_result = MagicMock()
        mock_result.id = 'event_id'
        mock_result.subject = 'Calendar Event'
        mock_result.start.date_time = '2025-12-10T14:00:00'
        mock_result.end.date_time = '2025-12-10T15:00:00'

        async_post_mock = AsyncMock(return_value=mock_result)
        cal_events = mock_graph_client.me.calendars.by_calendar_id.return_value
        cal_events.events.post = async_post_mock

        result = await outlook_calendar_toolkit.outlook_create_calendar_event(
            subject='Calendar Event',
            start_time='2025-12-10T14:00:00',
            end_time='2025-12-10T15:00:00',
            calendar_id='specific_calendar_id',
        )

        assert result['status'] == 'success'
        assert result['event_id'] == 'event_id'

        # Verify calendar_id was used
        mock_graph_client.me.calendars.by_calendar_id.assert_called_with(
            'specific_calendar_id'
        )
        async_post_mock.assert_called_once()

    async def test_create_calendar_event_failure(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test calendar event creation when API raises an exception."""
        async_post_mock = AsyncMock(
            side_effect=Exception('API connection failed')
        )
        mock_graph_client.me.events.post = async_post_mock

        result = await outlook_calendar_toolkit.outlook_create_calendar_event(
            subject='Some event',
            start_time='2025-12-10T10:00:00',
            end_time='2025-12-10T11:00:00',
        )

        assert 'error' in result
        assert 'Failed to create calendar event' in result['error']
        assert 'API connection failed' in result['error']


@pytest.mark.asyncio
class TestUpdateCalendarEvent:
    """Tests for update_calendar_event method."""

    async def test_update_calendar_event_success(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test successful calendar event update."""
        mock_result = MagicMock()
        mock_result.id = 'event_id'
        mock_result.subject = 'Updated Meeting'
        mock_result.start.date_time = '2025-12-10T14:00:00'
        mock_result.end.date_time = '2025-12-10T15:00:00'

        async_patch_mock = AsyncMock(return_value=mock_result)
        mock_graph_client.me.events.by_event_id.return_value.patch = (
            async_patch_mock
        )

        result = await outlook_calendar_toolkit.outlook_update_calendar_event(
            event_id='event_id',
            subject='Updated Meeting',
            start_time='2025-12-10T14:00:00',
            end_time='2025-12-10T15:00:00',
            timezone='UTC',
            locations=['New Room'],
        )

        assert result['status'] == 'success'
        assert result['message'] == 'Calendar event updated successfully.'
        assert result['event_id'] == 'event_id'
        assert result['event_subject'] == 'Updated Meeting'

        # Verify event_id was used
        mock_graph_client.me.events.by_event_id.assert_called_with('event_id')

        # Verify the event object passed to patch
        async_patch_mock.assert_called_once()
        event_arg = async_patch_mock.call_args[0][0]
        assert event_arg.subject == 'Updated Meeting'

    async def test_update_calendar_event_failure(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test calendar event update when API raises an exception."""
        async_patch_mock = AsyncMock(side_effect=Exception('Event not found'))
        mock_graph_client.me.events.by_event_id.return_value.patch = (
            async_patch_mock
        )

        result = await outlook_calendar_toolkit.outlook_update_calendar_event(
            event_id='invalid_event_id',
            subject='New Subject',
        )

        assert 'error' in result
        assert 'Failed to update calendar event' in result['error']
        assert 'Event not found' in result['error']


@pytest.mark.asyncio
class TestDeleteCalendarEvent:
    """Tests for delete_calendar_event method."""

    async def test_delete_calendar_event_success(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test successful calendar event deletion."""
        async_delete_mock = AsyncMock(return_value=None)
        mock_graph_client.me.events.by_event_id.return_value.delete = (
            async_delete_mock
        )

        result = await outlook_calendar_toolkit.outlook_delete_calendar_event(
            event_id='event_id'
        )

        assert result['status'] == 'success'
        assert result['message'] == 'Calendar event deleted successfully.'
        assert result['event_id'] == 'event_id'

        # Verify event_id was used
        mock_graph_client.me.events.by_event_id.assert_called_with('event_id')
        async_delete_mock.assert_called_once()

    async def test_delete_calendar_event_failure(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test calendar event deletion when API raises an exception."""
        async_delete_mock = AsyncMock(side_effect=Exception('Event not found'))
        mock_graph_client.me.events.by_event_id.return_value.delete = (
            async_delete_mock
        )

        result = await outlook_calendar_toolkit.outlook_delete_calendar_event(
            event_id='invalid_event_id'
        )

        assert 'error' in result
        assert 'Failed to delete calendar event' in result['error']
        assert 'Event not found' in result['error']


class TestExtractEventHelpers:
    """Tests for event extraction helper methods."""

    def test_extract_attendees(self, outlook_calendar_toolkit):
        """Test extracting attendees from event."""
        from msgraph.generated.models.attendee import Attendee
        from msgraph.generated.models.attendee_type import AttendeeType
        from msgraph.generated.models.email_address import EmailAddress
        from msgraph.generated.models.response_status import ResponseStatus
        from msgraph.generated.models.response_type import ResponseType

        # Create attendee using actual model classes
        attendee = Attendee(
            email_address=EmailAddress(
                address="user@test.com",
                name="Test User",
            ),
            type=AttendeeType.Required,
            status=ResponseStatus(response=ResponseType.Accepted),
        )

        result = outlook_calendar_toolkit._extract_attendees([attendee])

        assert len(result) == 1
        assert result[0]["email"] == "user@test.com"
        assert result[0]["name"] == "Test User"
        assert result[0]["type"] == "required"
        assert result[0]["response"] == "accepted"

    def test_extract_attendees_empty(self, outlook_calendar_toolkit):
        """Test extracting attendees with empty list."""
        assert outlook_calendar_toolkit._extract_attendees(None) == []
        assert outlook_calendar_toolkit._extract_attendees([]) == []

    def test_extract_locations(self, outlook_calendar_toolkit):
        """Test extracting locations from event."""
        from msgraph.generated.models.location import Location
        from msgraph.generated.models.location_type import LocationType
        from msgraph.generated.models.outlook_geo_coordinates import (
            OutlookGeoCoordinates,
        )
        from msgraph.generated.models.physical_address import PhysicalAddress

        # Create location using actual model classes
        location = Location(
            display_name="Conference Room A",
            location_type=LocationType.ConferenceRoom,
            address=PhysicalAddress(
                street="123 Main St",
                city="Seattle",
                state="WA",
                country_or_region="USA",
                postal_code="98101",
            ),
            coordinates=OutlookGeoCoordinates(
                latitude=47.6062,
                longitude=-122.3321,
            ),
        )

        result = outlook_calendar_toolkit._extract_locations([location])

        assert len(result) == 1
        assert result[0]["display_name"] == "Conference Room A"
        assert result[0]["location_type"] == "conferenceRoom"
        assert result[0]["address"]["street"] == "123 Main St"
        assert result[0]["address"]["city"] == "Seattle"
        assert result[0]["coordinates"]["latitude"] == 47.6062
        assert result[0]["coordinates"]["longitude"] == -122.3321

    def test_extract_locations_minimal(self, outlook_calendar_toolkit):
        """Test extracting locations with minimal data."""
        from msgraph.generated.models.location import Location

        location = Location(display_name="Room B")

        result = outlook_calendar_toolkit._extract_locations([location])

        assert len(result) == 1
        assert result[0]["display_name"] == "Room B"
        assert result[0]["location_type"] is None
        assert result[0]["address"] is None
        assert result[0]["coordinates"] is None

    def test_extract_locations_empty(self, outlook_calendar_toolkit):
        """Test extracting locations with empty list."""
        assert outlook_calendar_toolkit._extract_locations(None) == []
        assert outlook_calendar_toolkit._extract_locations([]) == []

    def test_extract_organizer(self, outlook_calendar_toolkit):
        """Test extracting organizer from event."""
        from msgraph.generated.models.email_address import EmailAddress
        from msgraph.generated.models.recipient import Recipient

        organizer = Recipient(
            email_address=EmailAddress(
                address="organizer@test.com",
                name="Organizer Name",
            )
        )

        result = outlook_calendar_toolkit._extract_organizer(organizer)

        assert result["email"] == "organizer@test.com"
        assert result["name"] == "Organizer Name"

    def test_extract_organizer_none(self, outlook_calendar_toolkit):
        """Test extracting organizer when None."""
        from msgraph.generated.models.recipient import Recipient

        result = outlook_calendar_toolkit._extract_organizer(None)
        assert result["email"] is None
        assert result["name"] is None

        organizer = Recipient(email_address=None)
        result = outlook_calendar_toolkit._extract_organizer(organizer)
        assert result["email"] is None
        assert result["name"] is None

    def test_extract_event_details(self, outlook_calendar_toolkit):
        """Test extracting full event details."""
        from msgraph.generated.models.free_busy_status import FreeBusyStatus
        from msgraph.generated.models.importance import Importance

        # Create mock event
        mock_event = MagicMock()
        mock_event.id = "event_123"
        mock_event.subject = "Team Meeting"
        mock_event.start.date_time = "2025-12-10T10:00:00"
        mock_event.start.time_zone = "UTC"
        mock_event.end.date_time = "2025-12-10T11:00:00"
        mock_event.is_all_day = False
        mock_event.body_preview = "Meeting agenda..."
        mock_event.locations = []
        mock_event.attendees = []
        mock_event.organizer = None
        mock_event.is_online_meeting = True
        mock_event.online_meeting_url = "https://teams.microsoft.com/meet"
        mock_event.importance = Importance.High
        mock_event.show_as = FreeBusyStatus.Busy
        mock_event.is_cancelled = False

        result = outlook_calendar_toolkit._extract_event_details(mock_event)

        assert result["id"] == "event_123"
        assert result["subject"] == "Team Meeting"
        assert result["start"] == "2025-12-10T10:00:00"
        assert result["end"] == "2025-12-10T11:00:00"
        assert result["timezone"] == "UTC"
        assert result["is_all_day"] is False
        assert result["body_preview"] == "Meeting agenda..."
        assert result["is_online_meeting"] is True
        assert (
            result["online_meeting_url"] == "https://teams.microsoft.com/meet"
        )
        assert result["importance"] == "high"
        assert result["show_as"] == "busy"
        assert result["is_cancelled"] is False


@pytest.mark.asyncio
class TestGetCalendarEvent:
    """Tests for get_calendar_event method."""

    async def test_get_calendar_event_success(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test successful calendar event retrieval."""
        from msgraph.generated.models.free_busy_status import FreeBusyStatus
        from msgraph.generated.models.importance import Importance

        mock_event = MagicMock()
        mock_event.id = "event_id"
        mock_event.subject = "Test Event"
        mock_event.start.date_time = "2025-12-10T10:00:00"
        mock_event.start.time_zone = "UTC"
        mock_event.end.date_time = "2025-12-10T11:00:00"
        mock_event.is_all_day = False
        mock_event.body_preview = "Event description"
        mock_event.locations = []
        mock_event.attendees = []
        mock_event.organizer = None
        mock_event.is_online_meeting = False
        mock_event.online_meeting_url = None
        mock_event.importance = Importance.Normal
        mock_event.show_as = FreeBusyStatus.Busy
        mock_event.is_cancelled = False

        async_get_mock = AsyncMock(return_value=mock_event)
        mock_graph_client.me.events.by_event_id.return_value.get = (
            async_get_mock
        )

        result = await outlook_calendar_toolkit.outlook_get_calendar_event(
            event_id="event_id"
        )

        assert result["status"] == "success"
        assert result["event_details"]["id"] == "event_id"
        assert result["event_details"]["subject"] == "Test Event"
        assert result["event_details"]["start"] == "2025-12-10T10:00:00"

        mock_graph_client.me.events.by_event_id.assert_called_with("event_id")

    async def test_get_calendar_event_failure(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test calendar event retrieval when event not found."""
        async_get_mock = AsyncMock(side_effect=Exception("Event not found"))
        mock_graph_client.me.events.by_event_id.return_value.get = (
            async_get_mock
        )

        result = await outlook_calendar_toolkit.outlook_get_calendar_event(
            event_id="invalid_id"
        )

        assert "error" in result
        assert "Failed to get calendar event" in result["error"]
        assert "Event not found" in result["error"]


def mock_single_event_response():
    """Helper function to create a mock event response."""
    from msgraph.generated.models.free_busy_status import FreeBusyStatus
    from msgraph.generated.models.importance import Importance

    mock_event = MagicMock()
    mock_event.id = "event_id"
    mock_event.subject = "Test Event"
    mock_event.start.date_time = "2025-12-10T10:00:00"
    mock_event.start.time_zone = "UTC"
    mock_event.end.date_time = "2025-12-10T11:00:00"
    mock_event.is_all_day = False
    mock_event.body_preview = "Event description"
    mock_event.locations = []
    mock_event.attendees = []
    mock_event.organizer = None
    mock_event.is_online_meeting = False
    mock_event.online_meeting_url = None
    mock_event.importance = Importance.Normal
    mock_event.show_as = FreeBusyStatus.Busy
    mock_event.is_cancelled = False

    return mock_event


@pytest.mark.asyncio
class TestListCalendarEvents:
    """Tests for list_calendar_events method."""

    async def test_list_calendar_events_success(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test successful calendar events listing."""
        mock_event = mock_single_event_response()

        mock_result = MagicMock()
        mock_result.value = [mock_event]

        async_get_mock = AsyncMock(return_value=mock_result)
        mock_graph_client.me.events.get = async_get_mock

        result = await outlook_calendar_toolkit.outlook_list_calendar_events()

        assert result['status'] == 'success'
        assert result['total_count'] == 1
        assert result['skip'] == 0
        assert result['top'] == 10
        assert len(result['events']) == 1

        details = result['events'][0]
        assert details['id'] == 'event_id'
        assert details['subject'] == 'Test Event'
        assert details['start'] == '2025-12-10T10:00:00'
        assert details['end'] == '2025-12-10T11:00:00'
        assert details['timezone'] == 'UTC'

    async def test_list_calendar_events_failure(
        self, outlook_calendar_toolkit, mock_graph_client
    ):
        """Test listing calendar events when API raises an exception."""
        async_get_mock = AsyncMock(
            side_effect=Exception('API connection failed')
        )
        mock_graph_client.me.events.get = async_get_mock

        result = await outlook_calendar_toolkit.outlook_list_calendar_events()

        assert 'error' in result
        assert 'Failed to list calendar events' in result['error']
        assert 'API connection failed' in result['error']
