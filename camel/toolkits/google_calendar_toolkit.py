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
# Setup guide - https://developers.google.com/calendar/api/quickstart/python

import datetime
import os
from typing import Any, Dict, List, Optional, Union

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, api_keys_required

logger = get_logger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']


@MCPServer()
class GoogleCalendarToolkit(BaseToolkit):
    r"""A class representing a toolkit for Google Calendar operations.

    This class provides methods for creating events, retrieving events,
    updating events, and deleting events from a Google Calendar.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
    ):
        r"""Initializes a new instance of the GoogleCalendarToolkit class.

        Args:
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)
        self.service = self._get_calendar_service()

    def create_event(
        self,
        event_title: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        attendees_email: Optional[List[str]] = None,
        timezone: str = "UTC",
    ) -> Dict[str, Any]:
        r"""Creates an event in the user's primary Google Calendar.

        Args:
            event_title (str): Title of the event.
            start_time (str): Start time in ISO format (YYYY-MM-DDTHH:MM:SS).
            end_time (str): End time in ISO format (YYYY-MM-DDTHH:MM:SS).
            description (str, optional): Description of the event.
            location (str, optional): Location of the event.
            attendees_email (List[str], optional): List of email addresses.
                (default: :obj:`None`)
            timezone (str, optional): Timezone for the event.
                (default: :obj:`UTC`)

        Returns:
            dict: A dictionary containing details of the created event.

        Raises:
            ValueError: If the event creation fails.
        """
        try:
            # Handle ISO format with or without timezone info
            if 'Z' in start_time or '+' in start_time:
                datetime.datetime.fromisoformat(
                    start_time.replace('Z', '+00:00')
                )
            else:
                datetime.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")

            if 'Z' in end_time or '+' in end_time:
                datetime.datetime.fromisoformat(
                    end_time.replace('Z', '+00:00')
                )
            else:
                datetime.datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S")
        except ValueError as e:
            error_msg = f"Time format error: {e!s}. Expected ISO "
            "format: YYYY-MM-DDTHH:MM:SS"
            logger.error(error_msg)
            return {"error": error_msg}

        if attendees_email is None:
            attendees_email = []

        # Verify email addresses with improved validation
        valid_emails = []
        import re

        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )

        for email in attendees_email:
            if email_pattern.match(email):
                valid_emails.append(email)
            else:
                logger.error(f"Invalid email address: {email}")
                return {"error": f"Invalid email address: {email}"}

        event: Dict[str, Any] = {
            'summary': event_title,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time,
                'timeZone': timezone,
            },
        }

        if valid_emails:
            event['attendees'] = [{'email': email} for email in valid_emails]

        try:
            created_event = (
                self.service.events()
                .insert(calendarId='primary', body=event)
                .execute()
            )
            return {
                'Event ID': created_event.get('id'),
                'EventTitle': created_event.get('summary'),
                'Start Time': created_event.get('start', {}).get('dateTime'),
                'End Time': created_event.get('end', {}).get('dateTime'),
                'Link': created_event.get('htmlLink'),
            }
        except Exception as e:
            error_msg = f"Failed to create event: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    def get_events(
        self, max_results: int = 10, time_min: Optional[str] = None
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        r"""Retrieves upcoming events from the user's primary Google Calendar.

        Args:
            max_results (int, optional): Maximum number of events to retrieve.
                (default: :obj:`10`)
            time_min (str, optional): The minimum time to fetch events from.
                If not provided, defaults to the current time.
                (default: :obj:`None`)

        Returns:
            Union[List[Dict[str, Any]], Dict[str, Any]]: A list of
                dictionaries, each containing details of an event, or a
                dictionary with an error message.

        Raises:
            ValueError: If the event retrieval fails.
        """
        if time_min is None:
            time_min = (
                datetime.datetime.now(datetime.timezone.utc).isoformat() + 'Z'
            )
        else:
            if not (time_min.endswith('Z')):
                time_min = time_min + 'Z'

        try:
            events_result = (
                self.service.events()
                .list(
                    calendarId='primary',
                    timeMin=time_min,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy='startTime',
                )
                .execute()
            )

            events = events_result.get('items', [])

            result = []
            for event in events:
                start = event['start'].get(
                    'dateTime', event['start'].get('date')
                )
                result.append(
                    {
                        'Event ID': event['id'],
                        'Summary': event.get('summary', 'No Title'),
                        'Start Time': start,
                        'Link': event.get('htmlLink'),
                    }
                )

            return result
        except Exception as e:
            logger.error(f"Failed to retrieve events: {e!s}")
            return {"error": f"Failed to retrieve events: {e!s}"}

    def update_event(
        self,
        event_id: str,
        event_title: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees_email: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        r"""Updates an existing event in the user's primary Google Calendar.

        Args:
            event_id (str): The ID of the event to update.
            event_title (Optional[str]): New title of the event.
                (default: :obj:`None`)
            start_time (Optional[str]): New start time in ISO format
                (YYYY-MM-DDTHH:MM:SSZ).
                (default: :obj:`None`)
            end_time (Optional[str]): New end time in ISO format
                (YYYY-MM-DDTHH:MM:SSZ).
                (default: :obj:`None`)
            description (Optional[str]): New description of the event.
                (default: :obj:`None`)
            location (Optional[str]): New location of the event.
                (default: :obj:`None`)
            attendees_email (Optional[List[str]]): List of email addresses.
                (default: :obj:`None`)

        Returns:
            Dict[str, Any]: A dictionary containing details of the updated
                event.

        Raises:
            ValueError: If the event update fails.
        """
        try:
            event = (
                self.service.events()
                .get(calendarId='primary', eventId=event_id)
                .execute()
            )

            # Update fields that are provided
            if event_title:
                event['summary'] = event_title
            if description:
                event['description'] = description
            if location:
                event['location'] = location
            if start_time:
                event['start']['dateTime'] = start_time
            if end_time:
                event['end']['dateTime'] = end_time
            if attendees_email:
                event['attendees'] = [
                    {'email': email} for email in attendees_email
                ]

            updated_event = (
                self.service.events()
                .update(calendarId='primary', eventId=event_id, body=event)
                .execute()
            )

            return {
                'Event ID': updated_event.get('id'),
                'Summary': updated_event.get('summary'),
                'Start Time': updated_event.get('start', {}).get('dateTime'),
                'End Time': updated_event.get('end', {}).get('dateTime'),
                'Link': updated_event.get('htmlLink'),
                'Attendees': [
                    attendee.get('email')
                    for attendee in updated_event.get('attendees', [])
                ],
            }
        except Exception:
            raise ValueError("Failed to update event")

    def delete_event(self, event_id: str) -> str:
        r"""Deletes an event from the user's primary Google Calendar.

        Args:
            event_id (str): The ID of the event to delete.

        Returns:
            str: A message indicating the result of the deletion.

        Raises:
            ValueError: If the event deletion fails.
        """
        try:
            self.service.events().delete(
                calendarId='primary', eventId=event_id
            ).execute()
            return f"Event deleted successfully. Event ID: {event_id}"
        except Exception:
            raise ValueError("Failed to delete event")

    def get_calendar_details(self) -> Dict[str, Any]:
        r"""Retrieves details about the user's primary Google Calendar.

        Returns:
            dict: A dictionary containing details about the calendar.

        Raises:
            ValueError: If the calendar details retrieval fails.
        """
        try:
            calendar = (
                self.service.calendars().get(calendarId='primary').execute()
            )
            return {
                'Calendar ID': calendar.get('id'),
                'Summary': calendar.get('summary'),
                'Description': calendar.get('description', 'No description'),
                'Time Zone': calendar.get('timeZone'),
                'Access Role': calendar.get('accessRole'),
            }
        except Exception:
            raise ValueError("Failed to retrieve calendar details")

    def _get_calendar_service(self):
        r"""Authenticates and creates a Google Calendar service object.

        Returns:
            Resource: A Google Calendar API service object.

        Raises:
            ValueError: If authentication fails.
        """
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        # Get credentials through authentication
        try:
            creds = self._authenticate()

            # Refresh token if expired
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())

            service = build('calendar', 'v3', credentials=creds)
            return service
        except Exception as e:
            raise ValueError(f"Failed to build service: {e!s}")

    @api_keys_required(
        [
            (None, "GOOGLE_CLIENT_ID"),
            (None, "GOOGLE_CLIENT_SECRET"),
        ]
    )
    def _authenticate(self):
        r"""Gets Google OAuth2 credentials from environment variables.

        Environment variables needed:
        - GOOGLE_CLIENT_ID: The OAuth client ID
        - GOOGLE_CLIENT_SECRET: The OAuth client secret
        - GOOGLE_REFRESH_TOKEN: (Optional) Refresh token for reauthorization

        Returns:
            Credentials: A Google OAuth2 credentials object.
        """
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        refresh_token = os.environ.get('GOOGLE_REFRESH_TOKEN')
        token_uri = os.environ.get(
            'GOOGLE_TOKEN_URI', 'https://oauth2.googleapis.com/token'
        )

        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        # For first-time authentication
        if not refresh_token:
            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": token_uri,
                    "redirect_uris": ["http://localhost"],
                }
            }

            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)

            return creds
        else:
            # If we have a refresh token, use it to get credentials
            return Credentials(
                None,
                refresh_token=refresh_token,
                token_uri=token_uri,
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES,
            )

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.create_event),
            FunctionTool(self.get_events),
            FunctionTool(self.update_event),
            FunctionTool(self.delete_event),
            FunctionTool(self.get_calendar_details),
        ]
