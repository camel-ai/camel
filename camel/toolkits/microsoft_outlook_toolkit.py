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

import os
from http.server import BaseHTTPRequestHandler
from typing import List, Optional

from dotenv import load_dotenv

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, api_keys_required

load_dotenv()
logger = get_logger(__name__)


class RedirectHandler(BaseHTTPRequestHandler):
    """Handler for OAuth redirect requests."""

    def do_GET(self):
        """Handles GET request and extracts authorization code."""
        from urllib.parse import parse_qs, urlparse

        try:
            query = parse_qs(urlparse(self.path).query)
            code = query.get("code", [None])[0]
            self.server.code = code
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"Authentication complete. You can close this window."
            )
        except Exception as e:
            self.server.code = None
            self.send_response(500)
            self.end_headers()
            self.wfile.write(
                f"Error during authentication: {e}".encode("utf-8")
            )

    def log_message(self, format, *args):
        pass


@MCPServer()
class OutlookToolkit(BaseToolkit):
    """A class representing a toolkit for Microsoft Outlook operations.

    This class provides methods for interacting with Microsoft Outlook via
    the Microsoft Graph API, including sending emails and managing calendar
    events.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
    ):
        """Initializes a new instance of the OutlookToolkit.

        Args:
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

        self.scopes = ["offline_access", "Mail.Send"]
        self.redirect_uri = 'http://localhost:1000'
        self.credentials = self._authenticate()
        self.client = self._get_graph_client(
            credentials=self.credentials, scopes=self.scopes
        )

    @api_keys_required(
        [
            (None, "MICROSOFT_TENANT_ID"),
            (None, "MICROSOFT_CLIENT_ID"),
            (None, "MICROSOFT_CLIENT_SECRET"),
        ]
    )
    def _get_auth_url(self, client_id, tenant_id, redirect_uri, scopes):
        """Constructs the Microsoft authorization URL.

        Args:
            client_id (str): The OAuth client ID.
            tenant_id (str): The Microsoft tenant ID.
            redirect_uri (str): The redirect URI for OAuth callback.
            scopes (List[str]): List of permission scopes.

        Returns:
            str: The complete authorization URL.
        """
        from urllib.parse import urlencode

        params = {
            'client_id': client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'scope': " ".join(scopes),
        }
        auth_url = (
            f'https://login.microsoftonline.com/{tenant_id}'
            f'/oauth2/v2.0/authorize?{urlencode(params)}'
        )
        return auth_url

    @api_keys_required(
        [
            (None, "MICROSOFT_CLIENT_ID"),
            (None, "MICROSOFT_CLIENT_SECRET"),
        ]
    )
    def _authenticate(self):
        """Authenticates and creates a Microsoft Graph credential.

        Environment variables needed:
        - MICROSOFT_TENANT_ID: The Microsoft tenant ID (optional,
            defaults to "common")
        - MICROSOFT_CLIENT_ID: The OAuth client ID
        - MICROSOFT_CLIENT_SECRET: The OAuth client secret

        Returns:
            AuthorizationCodeCredential: A Microsoft Graph credential object.

        Raises:
            ValueError: If authentication fails or authorization code is not
                received.
        """
        import webbrowser
        from http.server import HTTPServer
        from urllib.parse import urlparse

        from azure.identity import TokenCachePersistenceOptions
        from azure.identity.aio import AuthorizationCodeCredential

        try:
            self.tenant_id = os.getenv("MICROSOFT_TENANT_ID", "common")
            self.client_id = os.getenv("MICROSOFT_CLIENT_ID")
            self.client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")

            auth_url = self._get_auth_url(
                client_id=self.client_id,
                tenant_id=self.tenant_id,
                redirect_uri=self.redirect_uri,
                scopes=self.scopes,
            )

            # Convert redirect URI string to tuple for HTTPServer
            parsed_uri = urlparse(self.redirect_uri)
            server_address = (parsed_uri.hostname, parsed_uri.port)
            server = HTTPServer(server_address, RedirectHandler)

            # Open authorization URL
            logger.info("Opening browser for authentication...")
            webbrowser.open(auth_url)

            # Capture authorization code via local server
            server.handle_request()

            if not server.code:
                raise ValueError("Failed to get authorization code")

            # Create credentials
            cache_opts = TokenCachePersistenceOptions(name="my_app_cache")

            credentials = AuthorizationCodeCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                authorization_code=server.code,
                redirect_uri=self.redirect_uri,
                client_secret=self.client_secret,
                token_cache_persistence_options=cache_opts,
            )

            return credentials
        except Exception as e:
            error_msg = f"Failed to authenticate: {e!s}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _get_graph_client(self, credentials, scopes):
        """Creates a client for Microsoft Graph API.

        Args:
            credentials (AuthorizationCodeCredential): The authentication
                credentials.
            scopes (List[str]): List of permission scopes.

        Returns:
            GraphServiceClient: A Microsoft Graph API service client.

        Raises:
            ValueError: If the client creation fails.
        """
        from msgraph import GraphServiceClient

        try:
            client = GraphServiceClient(credentials=credentials, scopes=scopes)
            return client
        except Exception as e:
            error_msg = f"Failed to create Graph client: {e!s}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def get_tools(self) -> List[FunctionTool]:
        """Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return []
