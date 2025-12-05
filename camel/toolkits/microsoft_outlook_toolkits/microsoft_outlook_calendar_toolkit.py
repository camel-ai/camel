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

from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer

from ._auth_utils import (
    MicrosoftAuthenticator,
)


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

    def get_tools(self) -> List[FunctionTool]:
        """Returns a list of FunctionTool objects representing the
        functions in the toolkit.
        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return []
