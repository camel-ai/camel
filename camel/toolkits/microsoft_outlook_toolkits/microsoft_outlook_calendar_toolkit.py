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
from typing import TYPE_CHECKING, Any, List, Optional

from dotenv import load_dotenv

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer
from camel.utils.commons import run_async

from ._auth_utils import (
    MicrosoftAuthenticator,
)
from ._utils import _get_invalid_emails

if TYPE_CHECKING:
    from msgraph.generated.models import attendee

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

    def _create_attendees(
        self,
        email_list: List[str],
        attendee_type: str = "required",
    ) -> List["attendee.Attendee"]:
        """Builds a list of Attendee objects from email addresses
        and attendee_type of 'required', 'optional' or 'resource'."""

        from email.utils import parseaddr

        from msgraph.generated.models import attendee, email_address
        from msgraph.generated.models.attendee_type import AttendeeType

        attendee_type_map = {
            'required': AttendeeType.Required,
            'optional': AttendeeType.Optional,
            'resource': AttendeeType.Resource,
        }

        attendees = []
        for email in email_list:
            # Extract email address from both formats: "Email", "Name <Email>"
            name, addr = parseaddr(email)
            # Create EmailAddress object
            address = email_address.EmailAddress(address=addr)
            if name:
                address.name = name
            # Create Attendee object
            atten = attendee.Attendee(
                email_address=address,
                type=attendee_type_map.get(
                    attendee_type.lower(), AttendeeType.Required
                ),
            )
            attendees.append(atten)
        return attendees

    def _create_locations(
        self,
        locations: List[str],
    ):
        """Builds a list of Location objects from names of locations."""
        from msgraph.generated.models.location import Location

        all_locations = [Location(display_name=loc) for loc in locations]
        return all_locations

    def _create_importance(
        self,
        importance: str,
    ):
        """Builds importance object."""
        from msgraph.generated.models.importance import Importance

        importance_map = {
            'low': Importance.Low,
            'normal': Importance.Normal,
            'high': Importance.High,
        }
        return importance_map.get(importance.lower(), Importance.Normal)

    def _create_show_as_status(
        self,
        show_as: str,
    ):
        """Builds show_as (free/busy status) object."""
        from msgraph.generated.models.free_busy_status import FreeBusyStatus

        show_as_map = {
            'free': FreeBusyStatus.Free,
            'tentative': FreeBusyStatus.Tentative,
            'busy': FreeBusyStatus.Busy,
            'oof': FreeBusyStatus.Oof,
            'workingelsewhere': FreeBusyStatus.WorkingElsewhere,
            'unknown': FreeBusyStatus.Unknown,
        }
        return show_as_map.get(show_as.lower(), FreeBusyStatus.Busy)

    def _build_event(
        self,
        subject: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        timezone: Optional[str] = None,
        is_all_day: Optional[bool] = None,
        description: Optional[str] = None,
        locations: Optional[List[str]] = None,
        required_attendees: Optional[List[str]] = None,
        optional_attendees: Optional[List[str]] = None,
        resource_attendees: Optional[List[str]] = None,
        is_online_meeting: Optional[bool] = None,
        importance: Optional[str] = None,
        show_as: Optional[str] = None,
    ):
        """
        Builds a complete Event object with all provided settings.

        Args:
            subject (Optional[str]): The subject/title of the event.
            start_time (Optional[str]): Start time in ISO format.
            end_time (Optional[str]): End time in ISO format.
            timezone (Optional[str]): Timezone for the event.
            is_all_day (Optional[bool]): Whether the event is an all-day event.
            description (Optional[str]): HTML content for the body.
            locations (Optional[List[str]]): List of location names.
            required_attendees (Optional[List[str]]): Required attendee emails.
            optional_attendees (Optional[List[str]]): Optional attendee emails.
            resource_attendees (Optional[List[str]]): Resource attendee emails.
            is_online_meeting (Optional[bool]): Whether to enable online
            meeting.
            importance (Optional[str]): The importance level.
            show_as (Optional[str]): The free/busy status.

        Returns:
            Event: The configured Event object.
        """
        from msgraph.generated.models.body_type import BodyType
        from msgraph.generated.models.date_time_time_zone import (
            DateTimeTimeZone,
        )
        from msgraph.generated.models.event import Event
        from msgraph.generated.models.item_body import ItemBody

        # Create start and end DateTimeTimeZone objects
        start = DateTimeTimeZone(date_time=start_time, time_zone=timezone)
        end = DateTimeTimeZone(date_time=end_time, time_zone=timezone)

        # Create the base event object
        event = Event()

        if subject:
            event.subject = subject
        if start:
            event.start = start
        if end:
            event.end = end
        if is_all_day:
            event.is_all_day = is_all_day

        if description:
            event.body = ItemBody(
                content_type=BodyType.Html, content=description
            )

        if locations:
            locations = self._create_locations(locations)
            event.locations = locations

        # Build and set attendees
        event_attendees = []
        if required_attendees:
            event_attendees.extend(
                self._create_attendees(required_attendees, "required")
            )
        if optional_attendees:
            event_attendees.extend(
                self._create_attendees(optional_attendees, "optional")
            )
        if resource_attendees:
            event_attendees.extend(
                self._create_attendees(resource_attendees, "resource")
            )
        if event_attendees:
            event.attendees = event_attendees

        # Set online meeting settings
        if is_online_meeting:
            event.is_online_meeting = True

        # Set importance
        if importance:
            event.importance = self._create_importance(importance)

        # Set show_as (free/busy status)
        if show_as:
            event.show_as = self._create_show_as_status(show_as)

        return event

    async def create_calendar_event(
        self,
        subject: str,
        start_time: str,
        end_time: str,
        timezone: str = "UTC",
        description: Optional[str] = None,
        locations: Optional[List[str]] = None,
        required_attendees: Optional[List[str]] = None,
        optional_attendees: Optional[List[str]] = None,
        resource_attendees: Optional[List[str]] = None,
        is_online_meeting: bool = False,
        is_all_day: bool = False,
        importance: str = "normal",
        show_as: str = "busy",
        calendar_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Creates a new calendar event in the user's Outlook calendar.

        Args:
            subject (str): The subject/title of the event.
            start_time (str): Start time in ISO format (YYYY-MM-DDTHH:MM:SS).
            end_time (str): End time in ISO format (YYYY-MM-DDTHH:MM:SS).
            timezone (str): Timezone for the event (e.g., 'UTC',
                'Pacific Standard Time'). (default: :obj:`UTC`)
            description (Optional[str]): HTML content for the body of the
                event. (default: :obj:`None`)
            locations (Optional[List[str]]): List of display names for
                locations of the event. Multiple locations can be specified.
                (default: :obj:`None`)
            required_attendees (Optional[List[str]]): Email addresses of
                attendees marked as required. Supports formats: "email" or
                "Name <email>". (default: :obj:`None`)
            optional_attendees (Optional[List[str]]): Email addresses of
                attendees marked as optional. Supports formats: "email" or
                "Name <email>". (default: :obj:`None`)
            resource_attendees (Optional[List[str]]): Email addresses of room
                or equipment mailboxes to be booked as resources. Supports
                formats: "email" or "Name <email>". (default: :obj:`None`)
            is_online_meeting (bool): Whether to enable online meeting
                (e.g., Teams). (default: :obj:`False`)
            is_all_day (bool): Whether the event is an all-day event.
                (default: :obj:`False`)
            importance (str): The importance of the event. Possible values:
                'low', 'normal', 'high'. (default: :obj:`normal`)
            show_as (str): The status to show during the event. Possible
                values: 'free', 'tentative', 'busy', 'oof', 'workingElsewhere',
                'unknown'. (default: :obj:`busy`)
            calendar_id (Optional[str]): The ID of a specific calendar to
                create the event in. If None, creates in the default calendar.
                (default: :obj:`None`)

        Returns:
            dict[str, Any]: A dictionary containing the status and details
                of the created event, or an error message.
        """
        try:
            # Validate all email addresses
            invalid_emails = _get_invalid_emails(
                required_attendees, optional_attendees, resource_attendees
            )
            if invalid_emails:
                error_msg = (
                    f"Invalid email address(es) provided: "
                    f"{', '.join(invalid_emails)}"
                )
                logger.error(error_msg)
                return {"error": error_msg}

            # Build the event object using private helper
            event = self._build_event(
                subject=subject,
                start_time=start_time,
                end_time=end_time,
                timezone=timezone,
                is_all_day=is_all_day,
                description=description,
                locations=locations,
                required_attendees=required_attendees,
                optional_attendees=optional_attendees,
                resource_attendees=resource_attendees,
                is_online_meeting=is_online_meeting,
                importance=importance,
                show_as=show_as,
            )

            # Send request to create event
            if calendar_id:
                result = await self.client.me.calendars.by_calendar_id(
                    calendar_id
                ).events.post(event)
            else:
                result = await self.client.me.events.post(event)

            return {
                "status": "success",
                "message": "Calendar event created successfully.",
                "event_subject": result.subject,
                "event_id": result.id,
                "event_start": result.start.date_time,
                "event_end": result.end.date_time,
            }

        except Exception as e:
            error_msg = f"Failed to create calendar event: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def update_calendar_event(
        self,
        event_id: str,
        subject: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        timezone: Optional[str] = None,
        description: Optional[str] = None,
        locations: Optional[List[str]] = None,
        required_attendees: Optional[List[str]] = None,
        optional_attendees: Optional[List[str]] = None,
        resource_attendees: Optional[List[str]] = None,
        is_online_meeting: Optional[bool] = None,
        is_all_day: Optional[bool] = None,
        importance: Optional[str] = None,
        show_as: Optional[str] = None,
    ) -> dict[str, Any]:
        """Updates an existing calendar event in the user's Outlook calendar.

        Important:
        Any parameter provided will completely replace the original
        value. For example, if you want to add a new attendee while keeping
        existing ones, you must pass all attendees (both original and new).

        Args:
            event_id (str): The unique identifier of the event to update.
            subject (Optional[str]): The new subject/title of the event.
                (default: :obj:`None`)
            start_time (Optional[str]): New start time in ISO format
                (YYYY-MM-DDTHH:MM:SS). (default: :obj:`None`)
            end_time (Optional[str]): New end time in ISO format
                (YYYY-MM-DDTHH:MM:SS). (default: :obj:`None`)
            timezone (Optional[str]): Timezone for the event (e.g., 'UTC',
                'Pacific Standard Time'). (default: :obj:`None`)
            description (Optional[str]): HTML content for the body of the
                event. (default: :obj:`None`)
            locations (Optional[List[str]]): List of display names for
                locations of the event. (default: :obj:`None`)
            required_attendees (Optional[List[str]]): Email addresses of
                attendees marked as required. Supports formats: "email" or
                "Name <email>". (default: :obj:`None`)
            optional_attendees (Optional[List[str]]): Email addresses of
                attendees marked as optional. Supports formats: "email" or
                "Name <email>". (default: :obj:`None`)
            resource_attendees (Optional[List[str]]): Email addresses of room
                or equipment mailboxes to be booked as resources.
                (default: :obj:`None`)
            is_online_meeting (Optional[bool]): Whether to enable online
                meeting (e.g., Teams). (default: :obj:`None`)
            is_all_day (Optional[bool]): Whether the event is an all-day
                event. (default: :obj:`None`)
            importance (Optional[str]): The importance of the event. Possible
                values: 'low', 'normal', 'high'. (default: :obj:`None`)
            show_as (Optional[str]): The status to show during the event.
                Possible values: 'free', 'tentative', 'busy', 'oof',
                'workingElsewhere', 'unknown'. (default: :obj:`None`)

        Returns:
            dict[str, Any]: A dictionary containing the status and details
                of the updated event, or an error message.
        """
        try:
            # Validate all email addresses if provided
            invalid_emails = _get_invalid_emails(
                required_attendees, optional_attendees, resource_attendees
            )
            if invalid_emails:
                error_msg = (
                    f"Invalid email address(es) provided: "
                    f"{', '.join(invalid_emails)}"
                )
                logger.error(error_msg)
                return {"error": error_msg}

            # Build the event object with only provided fields
            event = self._build_event(
                subject=subject,
                start_time=start_time,
                end_time=end_time,
                timezone=timezone,
                is_all_day=is_all_day,
                description=description,
                locations=locations,
                required_attendees=required_attendees,
                optional_attendees=optional_attendees,
                resource_attendees=resource_attendees,
                is_online_meeting=is_online_meeting,
                importance=importance,
                show_as=show_as,
            )

            # Send request to update event
            result = await self.client.me.events.by_event_id(event_id).patch(
                event
            )

            return {
                "status": "success",
                "message": "Calendar event updated successfully.",
                "event_subject": result.subject,
                "event_id": result.id,
                "event_start": result.start.date_time,
                "event_end": result.end.date_time,
            }

        except Exception as e:
            error_msg = f"Failed to update calendar event: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    def _extract_attendees(self, attendees_list) -> List[dict]:
        """Extracts attendee details from a list of Attendee objects.

        Args:
            attendees_list: List of Attendee objects from the event.

        Returns:
            List[dict]: A list of dictionaries containing attendee details.
        """
        attendees = []
        if not attendees_list:
            return attendees

        for attendee in attendees_list:
            attendee_info = {
                "email": attendee.email_address.address,
                "name": attendee.email_address.name,
                "type": attendee.type.value if attendee.type else None,
            }
            if attendee.status:
                attendee_info["response"] = (
                    attendee.status.response.value
                    if attendee.status.response
                    else None
                )
            attendees.append(attendee_info)
        return attendees

    def _extract_locations(self, locations_list) -> List[dict]:
        """Extracts location details from a list of Location objects.

        Args:
            locations_list: List of Location objects from the event.

        Returns:
            List[dict]: A list of dictionaries containing location details.
        """
        locations = []
        if not locations_list:
            return locations

        for loc in locations_list:
            location_info = {
                "display_name": loc.display_name,
                "location_type": (
                    loc.location_type.value if loc.location_type else None
                ),
                "address": None,
                "coordinates": None,
            }
            # Extract address if available
            if loc.address:
                location_info["address"] = {
                    "street": loc.address.street,
                    "city": loc.address.city,
                    "state": loc.address.state,
                    "country_or_region": loc.address.country_or_region,
                    "postal_code": loc.address.postal_code,
                }
            # Extract coordinates if available
            if loc.coordinates:
                location_info["coordinates"] = {
                    "latitude": loc.coordinates.latitude,
                    "longitude": loc.coordinates.longitude,
                }
            locations.append(location_info)
        return locations

    def _extract_organizer(self, organizer) -> dict:
        """Extracts organizer details from an Organizer object.

        Args:
            organizer: The Organizer object from the event.

        Returns:
            dict: A dictionary containing organizer email and name.
        """
        if not organizer or not organizer.email_address:
            return {"email": None, "name": None}

        return {
            "email": organizer.email_address.address,
            "name": organizer.email_address.name,
        }

    def _extract_event_details(self, event) -> dict:
        """Extracts relevant details from an Event object.

        Args:
            event (Event): The Event object to extract details from.

        Returns:
            dict: A dictionary containing the extracted event details.
        """
        organizer = self._extract_organizer(event.organizer)

        return {
            "id": event.id,
            "subject": event.subject,
            "start": event.start.date_time if event.start else None,
            "end": event.end.date_time if event.end else None,
            "timezone": event.start.time_zone if event.start else None,
            "is_all_day": event.is_all_day,
            "body_preview": event.body_preview,
            "locations": self._extract_locations(event.locations),
            "attendees": self._extract_attendees(event.attendees),
            "organizer_email": organizer["email"],
            "organizer_name": organizer["name"],
            "is_online_meeting": event.is_online_meeting,
            "online_meeting_url": event.online_meeting_url,
            "importance": event.importance.value if event.importance else None,
            "show_as": event.show_as.value if event.show_as else None,
            "is_cancelled": event.is_cancelled,
        }

    async def get_calendar_event(
        self,
        event_id: str,
    ) -> dict[str, Any]:
        """Retrieves a calendar event by its ID.

        Args:
            event_id (str): The unique identifier of the event to retrieve.

        Returns:
            dict[str, Any]: A dictionary containing the status and event
                details or an error message.
        """
        try:
            result = await self.client.me.events.by_event_id(event_id).get()

            return {
                "status": "success",
                "event_details": self._extract_event_details(result),
            }

        except Exception as e:
            error_msg = f"Failed to get calendar event: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def list_calendar_events(
        self,
        filter_query: Optional[str] = None,
        order_by: Optional[List[str]] = None,
        top: int = 10,
        skip: int = 0,
    ) -> dict[str, Any]:
        """Retrieves a list of calendar events with optional filtering,
        sorting, and pagination.

        Warning: When using $filter and $orderby in the same query,
        properties that appear in $orderby must also appear in $filter.
        Failing to do this may result in an error.

        Args:
            filter_query (Optional[str]): OData filter for events.
                Examples:
                - Subject: "subject eq 'Team Meeting'"
                - Contains: "contains(subject, 'meeting')"
                - Start time: "start/dateTime ge '2025-01-01T00:00:00+05:30'"
                - End time: "end/dateTime le '2025-12-31T23:59:59+05:30'"
                - Combine: "subject eq 'Team Meeting' and isCancelled eq false"
            order_by (Optional[List[str]]): OData orderBy for sorting.
                Examples:
                - Start time ascending: ["start/dateTime asc"]
                - Start time descending: ["start/dateTime desc"]
                - Subject ascending: ["subject asc"]
                - Multi-field: ["start/dateTime desc", "subject asc"]
            top (int): Maximum number of events to return.
                (default: :obj:`10`)
            skip (int): Number of events to skip for pagination.
                (default: :obj:`0`)

        Returns:
            A dictionary containing the result of the operation.
        """
        try:
            from msgraph.generated.users.item.events.events_request_builder import (  # noqa: E501
                EventsRequestBuilder,
            )

            # Build query parameters
            query_params = (
                EventsRequestBuilder.EventsRequestBuilderGetQueryParameters(
                    top=top,
                    skip=skip,
                )
            )

            if order_by:
                query_params.orderby = order_by

            if filter_query:
                query_params.filter = filter_query

            request_config = EventsRequestBuilder.EventsRequestBuilderGetRequestConfiguration(  # noqa: E501
                query_parameters=query_params
            )

            # Send request to list events
            result = await self.client.me.events.get(
                request_configuration=request_config
            )

            all_events = []
            if result and result.value:
                for event in result.value:
                    details = self._extract_event_details(event)
                    all_events.append(details)

            return {
                "status": "success",
                "events": all_events,
                "total_count": len(all_events),
                "skip": skip,
                "top": top,
            }

        except Exception as e:
            error_msg = f"Failed to list calendar events: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def delete_calendar_event(
        self,
        event_id: str,
    ) -> dict[str, str]:
        """Deletes a calendar event by its ID.

        Args:
            event_id (str): The unique identifier of the event to delete.

        Returns:
            dict[str, str]: A dictionary containing the status and details
                of the deletion operation or an error message.
        """
        try:
            await self.client.me.events.by_event_id(event_id).delete()
            return {
                "status": "success",
                "message": "Calendar event deleted successfully.",
                "event_id": event_id,
            }

        except Exception as e:
            error_msg = f"Failed to delete calendar event: {e!s}"
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
            FunctionTool(run_async(self.create_calendar_event)),
            FunctionTool(run_async(self.update_calendar_event)),
            FunctionTool(run_async(self.get_calendar_event)),
            FunctionTool(run_async(self.list_calendar_events)),
            FunctionTool(run_async(self.delete_calendar_event)),
        ]
