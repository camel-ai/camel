# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

import json
import os
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits import BaseToolkit, FunctionTool

from .mcp_toolkit import MCPToolkit

logger = get_logger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


class GoogleSheetMCPToolkit(BaseToolkit):
    r"""GoogleSheetMCPToolkit provides Google Sheets operations via
    MCP server.

    This toolkit enables creating, reading, updating, and managing
    Google Sheets spreadsheets.

    Uses the ``mcp-google-sheets`` Python package.

    **Setup & Authentication Flow:**

    This toolkit requires OAuth2 authentication with Google. The full
    setup process is:

    Step 1 - Create OAuth2 credentials:
        Go to Google Cloud Console -> APIs & Services -> Credentials,
        create an OAuth2 Client ID (type: Desktop App). Download the
        credentials JSON, or note the Client ID and Client Secret.

    Step 2 - Enable APIs:
        In the same Google Cloud project, enable both:
        - Google Sheets API
        - Google Drive API

    Step 3 - Add test users (if app is in "Testing" mode):
        Go to OAuth consent screen -> Test users, add the Google
        account email that will authorize the Sheets access.

    Step 4 - First-time token authorization (one-time, requires browser):
        Run the following command to trigger the OAuth browser flow
        and generate a ``token.json`` file::

            CREDENTIALS_PATH=/path/to/credentials.json \
            TOKEN_PATH=~/.camel/google_sheets_token.json \
            uvx mcp-google-sheets

        A browser window will open asking you to authorize. After
        authorizing, the ``token.json`` will be saved. You can then
        stop the server with Ctrl+C. This is a one-time step.

    Step 5 - Use the toolkit:
        Now you can use the toolkit with both credential and token
        files::

            async with GoogleSheetMCPToolkit(
                credentials_path="/path/to/credentials.json",
                token_path="~/.camel/google_sheets_token.json",
            ) as toolkit:
                tools = toolkit.get_tools()

        Or, set environment variables and let the toolkit auto-generate
        the credentials file::

            export GOOGLE_CLIENT_ID="your-client-id"
            export GOOGLE_CLIENT_SECRET="your-client-secret"
            export GOOGLE_SHEETS_TOKEN_PATH="~/.camel/google_sheets_token.json"

            async with GoogleSheetMCPToolkit() as toolkit:
                tools = toolkit.get_tools()

    **Authentication Modes:**

    1. **Pre-existing credentials**: Provide ``credentials_path`` and
       ``token_path`` directly.
    2. **Auto-generate from CAMEL OAuth env vars**: Set
       ``GOOGLE_CLIENT_ID`` and ``GOOGLE_CLIENT_SECRET``, and the
       toolkit auto-generates a ``credentials.json`` at
       ``~/.camel/google_sheets_credentials.json``. You still need
       ``token_path`` pointing to a valid token file obtained from
       Step 4 above.

    Environment Variables:
        GOOGLE_SHEETS_CREDENTIALS_PATH: Path to OAuth2 credentials JSON.
        GOOGLE_SHEETS_TOKEN_PATH: Path to OAuth2 token JSON.
        GOOGLE_SHEETS_DRIVE_FOLDER_ID: Google Drive folder ID for
            new spreadsheets (optional).
        GOOGLE_CLIENT_ID: OAuth2 client ID (for auto-generation).
        GOOGLE_CLIENT_SECRET: OAuth2 client secret (for auto-generation).

    Attributes:
        timeout (Optional[float]): Connection timeout in seconds.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        drive_folder_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes the GoogleSheetMCPToolkit.

        Args:
            credentials_path (Optional[str]): Path to OAuth2 credentials
                JSON file. If None, attempts to read from
                GOOGLE_SHEETS_CREDENTIALS_PATH env var, or auto-generates
                from GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET.
                (default: :obj:`None`)
            token_path (Optional[str]): Path to OAuth2 token JSON file.
                If None, reads from GOOGLE_SHEETS_TOKEN_PATH env var.
                (default: :obj:`None`)
            drive_folder_id (Optional[str]): Google Drive folder ID for
                new spreadsheets. If None, reads from
                GOOGLE_SHEETS_DRIVE_FOLDER_ID env var.
                (default: :obj:`None`)
            timeout (Optional[float]): Connection timeout in seconds.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

        # --- Resolve credentials_path ---
        # Priority: parameter > env var > auto-generate from
        # GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET
        if credentials_path is None:
            credentials_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")

        # --- Resolve token_path ---
        # The token file contains the OAuth2 access & refresh tokens
        # obtained from the browser authorization flow (see Step 4 in
        # the class docstring). Without this file, the MCP server will
        # attempt to open a browser for authorization, which will hang
        # in non-interactive environments and cause a connection timeout.
        if token_path is None:
            token_path = os.getenv("GOOGLE_SHEETS_TOKEN_PATH")

        if drive_folder_id is None:
            drive_folder_id = os.getenv("GOOGLE_SHEETS_DRIVE_FOLDER_ID", "")

        # If no explicit credentials file, try to auto-generate one
        # from GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET env vars.
        # This creates ~/.camel/google_sheets_credentials.json with
        # the standard Google OAuth2 "installed" app format.
        if credentials_path is None:
            credentials_path = self._generate_credentials_file()

        if not credentials_path:
            raise ValueError(
                "credentials_path must be provided either as a parameter, "
                "through GOOGLE_SHEETS_CREDENTIALS_PATH, or by setting "
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars"
            )

        # Build env vars for the mcp-google-sheets server process.
        # CREDENTIALS_PATH: OAuth2 client credentials (client_id/secret)
        # TOKEN_PATH: authorized token (access_token/refresh_token)
        # DRIVE_FOLDER_ID: optional, restricts new spreadsheets to a
        #   specific Google Drive folder
        env: Dict[str, str] = {
            "CREDENTIALS_PATH": credentials_path,
        }
        if token_path:
            env["TOKEN_PATH"] = token_path
        if drive_folder_id:
            env["DRIVE_FOLDER_ID"] = drive_folder_id

        self._mcp_toolkit = MCPToolkit(
            config_dict={
                "mcpServers": {
                    "google-sheets": {
                        "command": "uvx",
                        "args": ["mcp-google-sheets"],
                        "env": env,
                    }
                }
            },
            timeout=timeout,
        )

    def _generate_credentials_file(self) -> Optional[str]:
        r"""Generate an OAuth2 credentials JSON file from CAMEL-style
        environment variables.

        This reuses the same env var pattern as GoogleCalendarToolkit
        (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET) and produces a file
        in the standard Google "installed" app format that
        mcp-google-sheets expects.

        The generated file looks like::

            {
              "installed": {
                "client_id": "...",
                "client_secret": "...",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"]
              }
            }

        This is the same format as downloading the JSON from Google
        Cloud Console -> Credentials -> OAuth 2.0 Client IDs.

        Note:
            This only generates the *credentials* file (client identity).
            You still need a separate *token* file containing the
            authorized access/refresh tokens. See Step 4 in the class
            docstring for how to obtain it.

        Returns:
            Optional[str]: Path to the generated credentials file,
                or None if env vars are not set.
        """
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

        if not client_id or not client_secret:
            return None

        # Build the standard Google OAuth2 "installed" app credentials
        credentials = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }

        # Store under ~/.camel/ alongside other CAMEL credential files
        # (e.g., gmail_token.json used by GmailToolkit)
        creds_dir = os.path.join(os.path.expanduser("~"), ".camel")
        os.makedirs(creds_dir, exist_ok=True)
        creds_path = os.path.join(creds_dir, "google_sheets_credentials.json")

        with open(creds_path, "w") as f:
            json.dump(credentials, f)
        # Restrict permissions: only owner can read/write
        os.chmod(creds_path, 0o600)

        logger.info(
            f"Generated Google Sheets credentials file at {creds_path}"
        )
        return creds_path

    async def connect(self):
        r"""Explicitly connect to the Google Sheets MCP server."""
        await self._mcp_toolkit.connect()

    async def disconnect(self):
        r"""Explicitly disconnect from the Google Sheets MCP server."""
        await self._mcp_toolkit.disconnect()

    @property
    def is_connected(self) -> bool:
        r"""Check if the toolkit is connected to the MCP server."""
        return self._mcp_toolkit.is_connected

    async def __aenter__(self) -> "GoogleSheetMCPToolkit":
        r"""Async context manager entry point."""
        await self.connect()
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        r"""Async context manager exit point."""
        await self.disconnect()

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of tools provided by the Google Sheets
        MCP server.

        Returns:
            List[FunctionTool]: List of available Google Sheets tools.
        """
        return self._mcp_toolkit.get_tools()

    async def call_tool(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Any:
        r"""Call a Google Sheets tool by name.

        Args:
            tool_name (str): Name of the tool to call.
            tool_args (Dict[str, Any]): Arguments to pass to the tool.

        Returns:
            Any: The result of the tool call.
        """
        return await self._mcp_toolkit.call_tool(tool_name, tool_args)
