# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========

"""Shared authentication utilities for Microsoft Outlook toolkits.

This module provides common authentication components that can be reused
across different Microsoft Outlook toolkits (Calendar, Mail, etc.).
"""

import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union

import requests
from dotenv import load_dotenv

from camel.logger import get_logger
from camel.utils import api_keys_required

if TYPE_CHECKING:
    from azure.identity.aio import AuthorizationCodeCredential

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


class CustomAzureCredential:
    """Creates a custom Azure credential to pass into MSGraph client.

    Implements Azure credential interface with automatic access token refresh
    using a refresh token. Updates the refresh token file whenever Microsoft
    issues a new refresh token during the refresh flow.

    Args:
        client_id (str): The OAuth client ID.
        client_secret (str): The OAuth client secret.
        tenant_id (str): The Microsoft tenant ID.
        refresh_token (str): The refresh token from OAuth flow.
        scopes (List[str]): List of OAuth permission scopes.
        refresh_token_file_path (Path): File path of json file to persist
            the refresh token.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        refresh_token: str,
        scopes: List[str],
        refresh_token_file_path: Path,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.refresh_token = refresh_token
        self.scopes = scopes
        self.refresh_token_file_path = refresh_token_file_path

        self._access_token = None
        self._expires_at = 0
        self._lock = threading.Lock()

    def _refresh_access_token(self):
        """Refreshes the access token using the refresh token.

        Requests a new access token from Microsoft's token endpoint.
        If Microsoft returns a new refresh token, updates both in-memory
        and refresh token file.

        Raises:
            Exception: If token refresh fails or returns an error.
        """
        token_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}"
            f"/oauth2/v2.0/token"
        )
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "scope": " ".join(self.scopes),
        }

        response = requests.post(token_url, data=data)
        result = response.json()

        # Raise exception if error in response
        if "error" in result:
            error_desc = result.get('error_description', result['error'])
            error_msg = f"Token refresh failed: {error_desc}"
            logger.error(error_msg)
            raise Exception(error_msg)

        # Update access token and expiration (60 second buffer)
        self._access_token = result["access_token"]
        self._expires_at = int(time.time()) + int(result["expires_in"]) - 60

        # Save new refresh token if Microsoft provides one
        if "refresh_token" in result:
            self.refresh_token = result["refresh_token"]
            self._save_refresh_token(self.refresh_token)

    def _save_refresh_token(self, refresh_token: str):
        """Saves the refresh token to file.

        Args:
            refresh_token (str): The refresh token to save.
        """
        token_data = {"refresh_token": refresh_token}

        try:
            # Create parent directories if they don't exist
            self.refresh_token_file_path.parent.mkdir(
                parents=True, exist_ok=True
            )

            # Write new refresh token to file
            with open(self.refresh_token_file_path, 'w') as f:
                json.dump(token_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save refresh token: {e!s}")

    def get_token(self, *args, **kwargs):
        """Gets a valid AccessToken object for msgraph.

        Called by Microsoft Graph SDK when making API requests.
        Automatically refreshes the token if expired.

        Args:
            *args: Positional arguments that msgraph might pass.
            **kwargs: Keyword arguments that msgraph might pass.

        Returns:
            AccessToken: Azure AccessToken with token and expiration.

        Raises:
            Exception: If requested scopes exceed allowed scopes.
        """
        from azure.core.credentials import AccessToken

        # Check if token needs refresh
        now = int(time.time())
        if now >= self._expires_at:
            with self._lock:
                # Double-check after lock (another thread may have refreshed)
                if now >= self._expires_at:
                    self._refresh_access_token()

        return AccessToken(self._access_token, self._expires_at)


class MicrosoftAuthenticator:
    """Handles Microsoft OAuth authentication for Outlook toolkits.

    This class provides authentication methods that can be used by
    different Microsoft Outlook toolkits. It handles both browser-based
    OAuth flow and refresh token-based authentication.

    Args:
        scopes (List[str]): OAuth permission scopes required by the toolkit.
        refresh_token_file_path (Optional[Path]): Path to store/load refresh
            tokens. If None, browser auth will be required each time.
    """

    def __init__(
        self,
        scopes: List[str],
        refresh_token_file_path: Optional[Path] = None,
    ):
        self.scopes = scopes
        self.refresh_token_file_path = refresh_token_file_path
        self.redirect_uri = self._get_dynamic_redirect_uri()

    def _get_dynamic_redirect_uri(self) -> str:
        """Finds an available port and returns a dynamic redirect URI.

        Returns:
            str: A redirect URI with format 'http://localhost:<port>' where
                port is an available port on the system.
        """
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
        return f'http://localhost:{port}'

    def _get_auth_url(
        self,
        client_id: str,
        tenant_id: str,
        redirect_uri: str,
        scopes: List[str],
    ) -> str:
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

    def _load_token_from_file(self) -> Optional[str]:
        """Loads refresh token from disk.

        Returns:
            Optional[str]: Refresh token if file exists and valid, else None.
        """
        if not self.refresh_token_file_path:
            return None

        if not self.refresh_token_file_path.exists():
            return None

        try:
            with open(self.refresh_token_file_path, 'r') as f:
                token_data = json.load(f)

            refresh_token = token_data.get('refresh_token')
            if refresh_token:
                logger.info(
                    f"Refresh token loaded from {self.refresh_token_file_path}"
                )
                return refresh_token

            logger.warning("Token file missing 'refresh_token' field")
            return None

        except Exception as e:
            logger.warning(f"Failed to load token file: {e!s}")
            return None

    def _save_token_to_file(self, refresh_token: str):
        """Saves refresh token to disk.

        Args:
            refresh_token (str): The refresh token to save.
        """
        if not self.refresh_token_file_path:
            logger.info("Token file path not set, skipping token save")
            return

        try:
            # Create parent directories if they don't exist
            self.refresh_token_file_path.parent.mkdir(
                parents=True, exist_ok=True
            )

            with open(self.refresh_token_file_path, 'w') as f:
                json.dump({"refresh_token": refresh_token}, f, indent=2)
            logger.info(
                f"Refresh token saved to " f"{self.refresh_token_file_path}"
            )
        except Exception as e:
            logger.warning(f"Failed to save token to file: {e!s}")

    def _authenticate_using_refresh_token(self) -> CustomAzureCredential:
        """Authenticates using a saved refresh token.

        Loads the refresh token from disk and creates a credential object
        that will automatically refresh access tokens as needed.

        Returns:
            CustomAzureCredential: Credential with auto-refresh capability.

        Raises:
            ValueError: If refresh token cannot be loaded or is invalid.
        """
        refresh_token = self._load_token_from_file()

        if not refresh_token:
            raise ValueError("No valid refresh token found in file")

        if not self.client_id or not self.client_secret:
            raise ValueError("Client ID and secret must be set")

        if not self.refresh_token_file_path:
            raise ValueError("Refresh token file path must be set")

        # Create credential with automatic refresh capability
        credentials = CustomAzureCredential(
            client_id=self.client_id,
            client_secret=self.client_secret,
            tenant_id=self.tenant_id,
            refresh_token=refresh_token,
            scopes=self.scopes,
            refresh_token_file_path=self.refresh_token_file_path,
        )

        logger.info("Authentication with saved token successful")
        return credentials

    def _authenticate_using_browser(self) -> "AuthorizationCodeCredential":
        """Authenticates using browser-based OAuth flow.

        Opens browser for user authentication, exchanges authorization
        code for tokens, and saves refresh token for future use.

        Returns:
            AuthorizationCodeCredential: Credential for Microsoft Graph API.

        Raises:
            ValueError: If authentication fails or no authorization code.
        """
        import webbrowser
        from http.server import HTTPServer
        from urllib.parse import urlparse

        from azure.identity import TokenCachePersistenceOptions
        from azure.identity.aio import AuthorizationCodeCredential

        if not self.client_id or not self.client_secret:
            raise ValueError("Client ID and secret must be set")

        # offline_access scope is needed so the azure credential can refresh
        # internally after access token expires as azure handles it internally
        # Do not add offline_access to self.scopes as MSAL does not allow it
        scope = [*self.scopes, "offline_access"]

        auth_url = self._get_auth_url(
            client_id=self.client_id,
            tenant_id=self.tenant_id,
            redirect_uri=self.redirect_uri,
            scopes=scope,
        )

        # Convert redirect URI string to tuple for HTTPServer
        parsed_uri = urlparse(self.redirect_uri)

        hostname = parsed_uri.hostname if parsed_uri.hostname else 'localhost'
        port = parsed_uri.port if parsed_uri.port else 8080
        server_address = (hostname, port)
        server = HTTPServer(server_address, RedirectHandler)

        # Open authorization URL
        logger.info(f"Opening browser for authentication: {auth_url}")
        webbrowser.open(auth_url)

        # Capture authorization code via local server
        server.handle_request()

        # Close the server after getting the code
        server.server_close()

        auth_code = getattr(server, 'code', None)
        if not auth_code:
            raise ValueError("Failed to get authorization code")

        authorization_code = auth_code

        # Set up token cache to store tokens
        cache_opts = TokenCachePersistenceOptions()

        # Create credentials
        credentials = AuthorizationCodeCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            authorization_code=authorization_code,
            redirect_uri=self.redirect_uri,
            client_secret=self.client_secret,
            token_cache_persistence_options=cache_opts,
        )

        return credentials

    @api_keys_required(
        [
            (None, "MICROSOFT_CLIENT_ID"),
            (None, "MICROSOFT_CLIENT_SECRET"),
        ]
    )
    def authenticate(
        self,
    ) -> Union[CustomAzureCredential, "AuthorizationCodeCredential"]:
        """Authenticates and creates credential for Microsoft Graph.

        Implements two-stage authentication:
        1. Attempts to use saved refresh token if refresh_token_file_path is
        provided
        2. Falls back to browser OAuth if no token or token invalid

        Returns:
            Union[CustomAzureCredential, AuthorizationCodeCredential]:
                Credential for Microsoft Graph API.

        Raises:
            ValueError: If authentication fails through both methods.
        """
        from azure.identity.aio import AuthorizationCodeCredential

        try:
            self.tenant_id = os.getenv("MICROSOFT_TENANT_ID", "common")
            self.client_id = os.getenv("MICROSOFT_CLIENT_ID")
            self.client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")

            # Try saved refresh token first if token file path is provided
            if (
                self.refresh_token_file_path
                and self.refresh_token_file_path.exists()
            ):
                try:
                    custom_credentials: CustomAzureCredential = (
                        self._authenticate_using_refresh_token()
                    )
                    return custom_credentials
                except Exception as e:
                    logger.warning(
                        f"Authentication using refresh token failed: {e!s}. "
                        f"Falling back to browser authentication"
                    )

            # Fall back to browser authentication
            browser_credentials: AuthorizationCodeCredential = (
                self._authenticate_using_browser()
            )
            return browser_credentials

        except Exception as e:
            error_msg = f"Failed to authenticate: {e!s}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def get_graph_client(self, credentials, scopes: List[str]):
        """Creates Microsoft Graph API client.

        Args:
            credentials: AuthorizationCodeCredential or CustomAzureCredential.
            scopes (List[str]): List of permission scopes.

        Returns:
            GraphServiceClient: Microsoft Graph API client.

        Raises:
            ValueError: If client creation fails.
        """
        from msgraph import GraphServiceClient

        try:
            client = GraphServiceClient(credentials=credentials, scopes=scopes)
            return client
        except Exception as e:
            error_msg = f"Failed to create Graph client: {e!s}"
            logger.error(error_msg)
            raise ValueError(error_msg)
