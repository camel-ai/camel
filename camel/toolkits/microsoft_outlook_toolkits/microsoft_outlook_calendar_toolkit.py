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

from pathlib import Path
from typing import Any, List, Optional

from dotenv import load_dotenv

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer
from camel.utils.commons import run_async

from ._auth_utils import (
    MicrosoftAuthenticator,
)

load_dotenv()
logger = get_logger(__name__)


@MCPServer()
class OutlookCalendarToolkit(BaseToolkit):
    """A comprehensive toolkit for Microsoft Outlook Calendar operations.

    This class provides methods for managing outlook calendar and
    calendar events.
    API keys can be accessed in microsoft azure portal (https://portal.azure.com/)
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        refresh_token_file_path: Optional[str] = None,
    ):
        """Initializes a new instance of the OutlookCalendarToolkit.
        Args:
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
            refresh_token_file_path (Optional[str]): The file path where
                refresh token is stored. If None, authentication using web
                browser will be required on each initialization. If provided,
                the refresh token is read from the file, used, and
                automatically updated when it nears expiry.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

        self.scopes = ["Calendars.ReadWrite"]
        token_path = (
            Path(refresh_token_file_path) if refresh_token_file_path else None
        )

        # Use shared authenticator for Microsoft OAuth
        authenticator = MicrosoftAuthenticator(
            scopes=self.scopes,
            refresh_token_file_path=token_path,
        )
        self.credentials = authenticator.authenticate()
        self.client = authenticator.get_graph_client(
            credentials=self.credentials, scopes=self.scopes
        )

    def _map_color_to_CalendarColor(self, color: str):
        """Maps a string color to the CalendarColor enum."""

        from msgraph.generated.models.calendar_color import CalendarColor

        # Define the mapping from string to CalendarColor enum
        color_map = {
            'auto': CalendarColor.Auto,
            'lightBlue': CalendarColor.LightBlue,
            'lightGreen': CalendarColor.LightGreen,
            'lightOrange': CalendarColor.LightOrange,
            'lightGray': CalendarColor.LightGray,
            'lightYellow': CalendarColor.LightYellow,
            'lightTeal': CalendarColor.LightTeal,
            'lightPink': CalendarColor.LightPink,
            'lightBrown': CalendarColor.LightBrown,
            'lightRed': CalendarColor.LightRed,
            'maxColor': CalendarColor.MaxColor,
        }

        return color_map.get(color, CalendarColor.Auto)

    async def create_calendar(
        self,
        name: str,
        color: str = "auto",
    ) -> dict[str, str]:
        """Creates a new calendar.

        Args:
            name (str): The calendar name.
            color (Optional[str]): Specifies the color theme to distinguish
                the calendar from other calendars in a UI. Possible values:
                'auto', 'lightBlue', 'lightGreen', 'lightOrange', 'lightGray',
                'lightYellow', 'lightTeal', 'lightPink', 'lightBrown',
                'lightRed', 'maxColor'. (default: :obj:`auto`)

        Returns:
            dict[str, str]: A dictionary containing the status and details
                of the created calendar or an error message.

        """
        from msgraph.generated.models.calendar import Calendar

        try:
            # Create calendar object with name and color
            calendar = Calendar(
                name=name, color=self._map_color_to_CalendarColor(color)
            )
            # Send request to create calendar
            result = await self.client.me.calendars.post(calendar)

            return {
                "status": "success",
                "message": "Calendar created successfully.",
                "calendar_id": result.id,
                "calendar_name": result.name,
            }

        except Exception as e:
            error_msg = f"Failed to create calendar : {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def delete_calendar(
        self,
        calendar_id: str,
    ) -> dict[str, str]:
        """Deletes a calendar by its ID.

        Args:
            calendar_id (str): The unique identifier of the calendar to be
                deleted.

        Returns:
            dict[str, str]: A dictionary containing the status and details
                of the deletion operation or an error message.

        """
        try:
            # send request to delete calendar
            await self.client.me.calendars.by_calendar_id(calendar_id).delete()
            return {
                "status": "success",
                "message": "Calendar deleted successfully.",
                "calendar_id": calendar_id,
            }

        except Exception as e:
            error_msg = f"Failed to delete calendar: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    def _extract_calendar_details(self, calendar) -> dict:
        """Extracts relevant details from a Calendar object.

        Args:
            calendar (Calendar): The Calendar object to extract details from.

        Returns:
            dict: A dictionary containing the extracted calendar details.
        """
        # Extract color name from Enum
        color_name = calendar.color.value

        return {
            "id": calendar.id,
            "name": calendar.name,
            "color": color_name,
            "is_default_calendar": calendar.is_default_calendar,
            "can_edit": calendar.can_edit,
            "can_share": calendar.can_share,
            "can_view_private_items": calendar.can_view_private_items,
            "is_removable": calendar.is_removable,
            "is_tallying_responses": calendar.is_tallying_responses,
            "owner_email": calendar.owner.address,
            "owner_name": calendar.owner.name,
        }

    async def get_calendar(
        self,
        calendar_id: str,
    ) -> dict[str, Any]:
        """Retrieves a calendar by its ID.

        Args:
            calendar_id (str): The unique identifier of the calendar to be
                retrieved.

        Returns:
            A dictionary containing the result of the operation.
        """
        try:
            # Send request to get calendar
            cal_req = self.client.me.calendars.by_calendar_id(calendar_id)
            result = await cal_req.get()

            return {
                "status": "success",
                "calendar_details": self._extract_calendar_details(result),
            }

        except Exception as e:
            error_msg = f"Failed to get calendar: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def list_calendars(
        self,
        filter_query: Optional[str] = None,
        order_by: Optional[List[str]] = None,
        top: int = 10,
        skip: int = 0,
    ) -> dict[str, Any]:
        """Retrieves a list of calendars with optional filtering, sorting,
        and pagination.

        Warning: When using $filter and $orderby in the same query,
        properties that appear in $orderby must also appear in $filter.
        Failing to do this may result in an error.

        Args:
            filter_query (Optional[str]): OData filter for calendars.
                Examples:
                - Name: "name eq 'Calendar'"
                - Contains: "contains(name, 'work')"
                - Default: "isDefaultCalendar eq true"
                - Can edit: "canEdit eq true"
                - Combine: "canEdit eq true and isDefaultCalendar eq false"
            order_by (Optional[List[str]]): OData orderBy for sorting.
                Examples:
                - Name ascending: ["name asc"]
                - Name descending: ["name desc"]
                - Multi-field: ["canEdit desc", "name asc"]
            top (int): Maximum number of calendars to return.
                (default: :obj:`10`)
            skip (int): Number of calendars to skip for pagination.
                (default: :obj:`0`)

        Returns:
            A dictionary containing the result of the operation.
        """
        try:
            from msgraph.generated.users.item.calendars.calendars_request_builder import (  # noqa: E501
                CalendarsRequestBuilder,
            )

            # Build query parameters
            query_params = CalendarsRequestBuilder.CalendarsRequestBuilderGetQueryParameters(  # noqa: E501
                top=top,
                skip=skip,
            )

            if order_by:
                query_params.orderby = order_by

            if filter_query:
                query_params.filter = filter_query

            request_config = CalendarsRequestBuilder.CalendarsRequestBuilderGetRequestConfiguration(  # noqa: E501
                query_parameters=query_params
            )

            # Send request to list calendars
            result = await self.client.me.calendars.get(
                request_configuration=request_config
            )

            all_calendars = []
            if result and result.value:
                for calendar in result.value:
                    details = self._extract_calendar_details(calendar)
                    all_calendars.append(details)

            logger.info(f"Retrieved {len(all_calendars)} calendars")

            return {
                "status": "success",
                "calendars": all_calendars,
                "total_count": len(all_calendars),
                "skip": skip,
                "top": top,
            }

        except Exception as e:
            error_msg = f"Failed to list calendars: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def update_calendar(
        self,
        calendar_id: str,
        name: Optional[str] = None,
        color: Optional[str] = None,
    ) -> dict[str, Any]:
        """Updates an existing calendar.

        Args:
            calendar_id (str): The unique identifier of the calendar to update.
            name (Optional[str]): The new name for the calendar.
                (default: :obj:`None`)
            color (Optional[str]): Specifies the color theme to distinguish
                the calendar from other calendars in a UI. Possible values:
                'auto', 'lightBlue', 'lightGreen', 'lightOrange', 'lightGray',
                'lightYellow', 'lightTeal', 'lightPink', 'lightBrown',
                'lightRed', 'maxColor'. (default: :obj:`None`)

        Returns:
            dict[str, Any]: A dictionary containing the status and details
                of the updated calendar or an error message.
        """
        from msgraph.generated.models.calendar import Calendar

        try:
            # Build calendar update object with only provided fields
            update_fields = {}
            if name is not None:
                update_fields['name'] = name
            if color is not None:
                update_fields['color'] = self._map_color_to_CalendarColor(
                    color
                )

            calendar = Calendar(**update_fields)

            # Send request to update calendar
            await self.client.me.calendars.by_calendar_id(calendar_id).patch(
                calendar
            )

            return {
                "status": "success",
                "message": "Calendar updated successfully.",
                "updated_values": update_fields,
            }

        except Exception as e:
            error_msg = f"Failed to update calendar: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_tools(self) -> List[FunctionTool]:
        """Returns a list of FunctionTool objects representing the
        functions in the toolkit.
        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(run_async(self.create_calendar)),
            FunctionTool(run_async(self.delete_calendar)),
            FunctionTool(run_async(self.get_calendar)),
            FunctionTool(run_async(self.list_calendars)),
            FunctionTool(run_async(self.update_calendar)),
        ]
