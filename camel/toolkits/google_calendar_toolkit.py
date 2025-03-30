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
import pickle
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit

SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarToolkit(BaseToolkit):
    r"""A class representing a toolkit for Google Calendar operations.

    This class provides methods for creating events, retrieving events,
    updating events, and deleting events from a Google Calendar.
    """

    def __init__(
        self,
        credentials_path: str = "credentials.json",
        token_path: str = "token.pickle",
        timeout: Optional[float] = None,
    ):
        super().__init__(timeout=timeout)
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = self._get_calendar_service()

    def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        attendees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        r"""Creates an event in the user's primary Google Calendar.

        Args:
            summary (str): Title of the event.
            start_time (str): Start time in ISO format (YYYY-MM-DDTHH:MM:SS).
            end_time (str): End time in ISO format (YYYY-MM-DDTHH:MM:SS).
            description (str, optional): Description of the event.
            location (str, optional): Location of the event.
            attendees (List[str], optional): List of email addresses.

        Returns:
            dict: A dictionary containing details of the created event.

        Raises:
            Exception: If the event creation fails.
        """
        if attendees is None:
            attendees = []

        event: Dict[str, Any] = {
            'summary': summary,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'UTC',
            },
        }

        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]

        try:
            created_event = (
                self.service.events()
                .insert(calendarId='primary', body=event)
                .execute()
            )
            return {
                'Event ID': created_event.get('id'),
                'Summary': created_event.get('summary'),
                'Start Time': created_event.get('start', {}).get('dateTime'),
                'End Time': created_event.get('end', {}).get('dateTime'),
                'Link': created_event.get('htmlLink'),
            }
        except Exception as e:
            raise Exception(f"Failed to create event: {e!s}")

    def get_events(
        self, max_results: int = 10, time_min: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        r"""Retrieves upcoming events from the user's primary Google Calendar.

        Args:
            max_results (int, optional): Maximum number of events to retrieve.
            time_min (str, optional): The minimum time to fetch events from.
                If not provided, defaults to the current time.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries,
            each containing details of an event.

        Raises:
            Exception: If the event retrieval fails.
        """
        if time_min is None:
            time_min = datetime.datetime.utcnow().isoformat() + 'Z'
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
            raise Exception(f"Failed to retrieve events: {e!s}")

    def update_event(
        self,
        event_id: str,
        summary: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Updates an existing event in the user's primary Google Calendar.

        Args:
            event_id (str): The ID of the event to update.
            summary (str, optional): New title of the event.
            start_time (str, optional): New start time in ISO format
            (YYYY-MM-DDTHH:MM:SSZ).
            end_time (str, optional): New end time in ISO format
            (YYYY-MM-DDTHH:MM:SSZ).
            description (str, optional): New description of the event.
            location (str, optional): New location of the event.

        Returns:
            dict: A dictionary containing details of the updated event.

        Raises:
            Exception: If the event update fails.
        """
        try:
            event = (
                self.service.events()
                .get(calendarId='primary', eventId=event_id)
                .execute()
            )

            # Update fields that are provided
            if summary:
                event['summary'] = summary
            if description:
                event['description'] = description
            if location:
                event['location'] = location
            if start_time:
                event['start']['dateTime'] = start_time
            if end_time:
                event['end']['dateTime'] = end_time

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
            }
        except Exception as e:
            raise Exception(f"Failed to update event: {e!s}")

    def delete_event(self, event_id: str) -> str:
        r"""Deletes an event from the user's primary Google Calendar.

        Args:
            event_id (str): The ID of the event to delete.

        Returns:
            str: A message indicating the result of the deletion.

        Raises:
            Exception: If the event deletion fails.
        """
        try:
            self.service.events().delete(
                calendarId='primary', eventId=event_id
            ).execute()
            return f"Event deleted successfully. Event ID: {event_id}"
        except Exception as e:
            raise Exception(f"Failed to delete event: {e!s}")

    def get_calendar_details(self) -> Dict[str, Any]:
        r"""Retrieves details about the user's primary Google Calendar.

        Returns:
            dict: A dictionary containing details about the calendar.

        Raises:
            Exception: If the calendar details retrieval fails.
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
        except Exception as e:
            raise Exception(f"Failed to retrieve calendar details: {e!s}")

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

    def _get_calendar_service(self):
        r"""Authenticates and creates a Google Calendar service object.

        Returns:
            Resource: A Google Calendar API service object.

        Raises:
            Exception: If authentication fails.
        """
        creds = None

        # The file token.pickle stores the user's access and refresh tokens
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)

        try:
            service = build('calendar', 'v3', credentials=creds)
            return service
        except Exception as e:
            raise Exception(f"Failed to build service: {e!s}")
