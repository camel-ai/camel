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
