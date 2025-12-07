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
        result = await outlook_calendar_toolkit.create_calendar(
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
        result = await outlook_calendar_toolkit.create_calendar(
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
        result = await outlook_calendar_toolkit.create_calendar(
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
        result = await outlook_calendar_toolkit.delete_calendar(
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
        result = await outlook_calendar_toolkit.delete_calendar(
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

        result = await outlook_calendar_toolkit.get_calendar(calendar_id='id')

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
        result = await outlook_calendar_toolkit.get_calendar(
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

        result = await outlook_calendar_toolkit.list_calendars()

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

        result = await outlook_calendar_toolkit.list_calendars()

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

        result = await outlook_calendar_toolkit.update_calendar(
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

        result = await outlook_calendar_toolkit.update_calendar(
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

        result = await outlook_calendar_toolkit.update_calendar(
            calendar_id='invalid_id', name='New Name'
        )

        assert 'error' in result
        assert 'Failed to update calendar' in result['error']
