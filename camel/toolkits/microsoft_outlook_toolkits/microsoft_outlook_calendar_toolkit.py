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
from typing import List, Optional

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
        ]
