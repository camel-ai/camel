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
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import requests
from dotenv import load_dotenv

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, api_keys_required

load_dotenv()
logger = get_logger(__name__)


class OAuthHTTPServer(HTTPServer):
    code: Optional[str] = None


class RedirectHandler(BaseHTTPRequestHandler):
    """Handler for OAuth redirect requests."""

    def do_GET(self):
        """Handles GET request and extracts authorization code."""
        from urllib.parse import parse_qs, urlparse

        try:
            query = parse_qs(urlparse(self.path).query)
            code = query.get("code", [None])[0]
            cast(OAuthHTTPServer, self.server).code = code
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                b"Authentication complete. You can close this window."
            )
        except Exception as e:
            cast(OAuthHTTPServer, self.server).code = None
            self.send_response(500)
            self.end_headers()
            self.wfile.write(
                f"Error during authentication: {e}".encode("utf-8")
            )

    def log_message(self, format, *args):
        pass


class CustomAzureCredential:
    """Creates a sync Azure credential to pass into MSGraph client.

    Implements Azure credential interface with automatic token refresh using
    a refresh token. Updates the refresh token file whenever Microsoft issues
    a new refresh token during the refresh flow.

    Args:
        client_id (str): The OAuth client ID.
        client_secret (str): The OAuth client secret.
        tenant_id (str): The Microsoft tenant ID.
        refresh_token (str): The refresh token from OAuth flow.
        scopes (List[str]): List of OAuth permission scopes.
        refresh_token_file_path (Optional[Path]): File path of json file
        with refresh token.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str,
        refresh_token: str,
        scopes: List[str],
        refresh_token_file_path: Optional[Path],
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
        self._debug_claims_logged = False

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

        response = requests.post(token_url, data=data, timeout=30)
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
        if not self.refresh_token_file_path:
            logger.info("Token file path not set, skipping token save")
            return

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
        """Gets a valid AccessToken object for msgraph (sync).

        Called by Microsoft Graph SDK when making API requests.
        Automatically refreshes the token if expired.

        Args:
            *args: Positional arguments that msgraph might pass .
            **kwargs: Keyword arguments that msgraph might pass .

        Returns:
            AccessToken: Azure AccessToken with token and expiration.

        Raises:
            Exception: If requested scopes exceed allowed scopes.
        """
        from azure.core.credentials import AccessToken

        def _maybe_log_token_claims(token: str) -> None:
            if self._debug_claims_logged:
                return
            if os.getenv("CAMEL_OUTLOOK_DEBUG_TOKEN_CLAIMS") != "1":
                return

            try:
                import base64

                _header_b64, payload_b64, _sig_b64 = token.split(".", 2)
                payload_b64 += "=" * (-len(payload_b64) % 4)
                payload = json.loads(
                    base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
                )
                logger.info(
                    "Outlook token claims: aud=%s scp=%s roles=%s",
                    payload.get("aud"),
                    payload.get("scp"),
                    payload.get("roles"),
                )
            except Exception as e:
                logger.warning("Failed to decode token claims: %s", e)
            finally:
                self._debug_claims_logged = True

        # Check if token needs refresh
        now = int(time.time())
        if now >= self._expires_at:
            with self._lock:
                # Double-check after lock (another thread may have refreshed)
                if now >= self._expires_at:
                    self._refresh_access_token()

        _maybe_log_token_claims(self._access_token)
        return AccessToken(self._access_token, self._expires_at)


@MCPServer()
class OutlookMailToolkit(BaseToolkit):
    """A comprehensive toolkit for Microsoft Outlook Mail operations.

    This class provides methods for Outlook Mail operations including sending
    emails, managing drafts, replying to mails, deleting mails, fetching
    mails and attachments and changing folder of mails.
    API keys can be accessed in the Azure portal (https://portal.azure.com/)
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        refresh_token_file_path: Optional[str] = None,
    ):
        """Initializes a new instance of the OutlookMailToolkit.

        Args:
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
            refresh_token_file_path (Optional[str]): The path of json file
                where refresh token is stored. If None, authentication using
                web browser will be required on each initialization. If
                provided, the refresh token is read from the file, used, and
                automatically updated when it nears expiry.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)

        self.scopes = self._normalize_scopes(["Mail.Send", "Mail.ReadWrite"])
        self.redirect_uri = self._get_dynamic_redirect_uri()
        self.refresh_token_file_path = (
            Path(refresh_token_file_path) if refresh_token_file_path else None
        )
        self.credentials = self._authenticate()
        self.client = self._get_graph_client(
            credentials=self.credentials, scopes=self.scopes
        )

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

    def _normalize_scopes(self, scopes: List[str]) -> List[str]:
        """Normalizes OAuth scopes to what Azure Identity expects.

        Azure Identity credentials (used by Kiota/MSGraph) expect fully
        qualified scopes like `https://graph.microsoft.com/Mail.Send`.
        For backwards compatibility, this method also accepts short scopes
        like `Mail.Send` and prefixes them with Microsoft Graph resource.
        """
        graph_resource = "https://graph.microsoft.com"
        passthrough = {"offline_access", "openid", "profile"}

        normalized: List[str] = []
        for scope in scopes:
            scope = scope.strip()
            if not scope:
                continue
            if scope in passthrough or "://" in scope:
                normalized.append(scope)
                continue
            normalized.append(f"{graph_resource}/{scope.lstrip('/')}")
        return normalized

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
                f"Refresh token saved to {self.refresh_token_file_path}"
            )
        except Exception as e:
            logger.warning(f"Failed to save token to file: {e!s}")

    def _authenticate_using_refresh_token(
        self,
    ) -> CustomAzureCredential:
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

    def _authenticate_using_browser(self):
        """Authenticates using browser-based OAuth flow.

        Opens browser for user authentication, exchanges authorization
        code for tokens, and saves refresh token for future use.

        Returns:
            CustomAzureCredential or AuthorizationCodeCredential :
                Credential for Microsoft Graph API.

        Raises:
            ValueError: If authentication fails or no authorization code.
        """
        from azure.identity import AuthorizationCodeCredential

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

        authorization_code = self._get_authorization_code_via_browser(auth_url)

        token_result = self._exchange_authorization_code_for_tokens(
            authorization_code=authorization_code,
            scope=scope,
        )

        refresh_token = token_result.get("refresh_token")
        if refresh_token:
            self._save_token_to_file(refresh_token)
            credentials = CustomAzureCredential(
                client_id=self.client_id,
                client_secret=self.client_secret,
                tenant_id=self.tenant_id,
                refresh_token=refresh_token,
                scopes=self.scopes,
                refresh_token_file_path=self.refresh_token_file_path,
            )

            access_token = token_result.get("access_token")
            expires_in = token_result.get("expires_in")
            if access_token and expires_in:
                # Prime the credential to avoid an immediate refresh request.
                credentials._access_token = access_token
                credentials._expires_at = (
                    int(time.time()) + int(expires_in) - 60
                )
            return credentials

        logger.warning(
            "No refresh_token returned from browser auth; falling back to "
            "AuthorizationCodeCredential (token won't be persisted to the "
            "provided refresh_token_file_path)."
        )
        return AuthorizationCodeCredential(
            tenant_id=self.tenant_id,
            client_id=self.client_id,
            authorization_code=authorization_code,
            redirect_uri=self.redirect_uri,
            client_secret=self.client_secret,
        )

    def _get_authorization_code_via_browser(self, auth_url: str) -> str:
        """Opens a browser and captures the authorization code via localhost.

        Args:
            auth_url (str): The authorization URL to open in the browser.

        Returns:
            str: The captured authorization code.

        Raises:
            ValueError: If the authorization code cannot be captured.
        """
        import webbrowser
        from urllib.parse import urlparse

        parsed_uri = urlparse(self.redirect_uri)
        hostname = parsed_uri.hostname
        port = parsed_uri.port
        if not hostname or not port:
            raise ValueError(
                f"Invalid redirect_uri, expected host and port: "
                f"{self.redirect_uri}"
            )

        server_address = (hostname, port)
        server = OAuthHTTPServer(server_address, RedirectHandler)
        server.code = None

        logger.info(f"Opening browser for authentication: {auth_url}")
        webbrowser.open(auth_url)

        server.handle_request()
        server.server_close()

        authorization_code = server.code
        if not authorization_code:
            raise ValueError("Failed to get authorization code")
        return authorization_code

    def _exchange_authorization_code_for_tokens(
        self, authorization_code: str, scope: List[str]
    ) -> Dict[str, Any]:
        """Exchanges an authorization code for tokens via OAuth token endpoint.

        Args:
            authorization_code (str): Authorization code captured from browser.
            scope (List[str]): Scopes requested in the authorization flow.

        Returns:
            Dict[str, Any]: Token response JSON.

        Raises:
            ValueError: If token exchange fails or returns an error payload.
        """
        token_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}"
            f"/oauth2/v2.0/token"
        )
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scope),
        }

        response = requests.post(token_url, data=data, timeout=self.timeout)
        result = response.json()

        if "error" in result:
            error_desc = result.get("error_description", result["error"])
            raise ValueError(f"Token exchange failed: {error_desc}")

        return result

    @api_keys_required(
        [
            (None, "MICROSOFT_CLIENT_ID"),
            (None, "MICROSOFT_CLIENT_SECRET"),
        ]
    )
    def _authenticate(self):
        """Authenticates and creates credential for Microsoft Graph.

        Implements two-stage authentication:
        1. Attempts to use saved refresh token if refresh_token_file_path is
            provided
        2. Falls back to browser OAuth if no token or token invalid

        Returns:
            AuthorizationCodeCredential or CustomAzureCredential

        Raises:
            ValueError: If authentication fails through both methods.
        """
        from azure.identity import AuthorizationCodeCredential

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
                    credentials: CustomAzureCredential = (
                        self._authenticate_using_refresh_token()
                    )
                    return credentials
                except Exception as e:
                    logger.warning(
                        f"Authentication using refresh token failed: {e!s}. "
                        f"Falling back to browser authentication"
                    )

            # Fall back to browser authentication
            credentials: AuthorizationCodeCredential = (
                self._authenticate_using_browser()
            )
            return credentials

        except Exception as e:
            error_msg = f"Failed to authenticate: {e!s}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _get_graph_client(self, credentials, scopes):
        """Creates Microsoft Graph API client.

        Args:
            credentials : AuthorizationCodeCredential or
                AsyncCustomAzureCredential.
            scopes (List[str]): List of permission scopes.

        Returns:
            GraphServiceClient: Microsoft Graph API client.

        Raises:
            ValueError: If client creation fails.
        """
        from msgraph import GraphServiceClient

        try:
            return GraphServiceClient(credentials=credentials, scopes=scopes)
        except Exception as e:
            error_msg = f"Failed to create Graph client: {e!s}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def is_email_valid(self, email: str) -> bool:
        """Validates a single email address.

        Args:
            email (str): Email address to validate.

        Returns:
            bool: True if the email is valid, False otherwise.
        """
        import re
        from email.utils import parseaddr

        # Extract email address from both formats : "Email" , "Name <Email>"
        _, addr = parseaddr(email)

        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        return bool(addr and email_pattern.match(addr))

    def _get_invalid_emails(self, *lists: Optional[List[str]]) -> List[str]:
        """Finds invalid email addresses from multiple email lists.

        Args:
            *lists: Variable number of optional email address lists.

        Returns:
            List[str]: List of invalid email addresses. Empty list if all
                emails are valid.
        """
        invalid_emails = []
        for email_list in lists:
            if email_list is None:
                continue
            for email in email_list:
                if not self.is_email_valid(email):
                    invalid_emails.append(email)
        return invalid_emails

    def _create_attachments(self, file_paths: List[str]) -> List[Any]:
        """Creates Microsoft Graph FileAttachment objects from file paths.

        Args:
            file_paths (List[str]): List of local file paths to attach.

        Returns:
            List[Any]: List of FileAttachment objects ready for Graph API use.

        Raises:
            ValueError: If any file cannot be read or attached.
        """
        from msgraph.generated.models.file_attachment import FileAttachment

        attachment_list = []

        for file_path in file_paths:
            try:
                if not os.path.isfile(file_path):
                    raise ValueError(
                        f"Path does not exist or is not a file: {file_path}"
                    )

                with open(file_path, "rb") as file:
                    file_content = file.read()

                file_name = os.path.basename(file_path)

                attachment_obj = FileAttachment(
                    name=file_name,
                    content_bytes=file_content,
                )

                attachment_list.append(attachment_obj)

            except Exception as e:
                raise ValueError(f"Failed to attach file {file_path}: {e!s}")

        return attachment_list

    def _create_recipients(self, email_list: List[str]) -> List[Any]:
        """Creates Microsoft Graph Recipient objects from email addresses.

        Supports both simple email format ("email@example.com") and
        name-email format ("John Doe <email@example.com>").

        Args:
            email_list (List[str]): List of email addresses,
                which can include display names.

        Returns:
            List[Any]: List of Recipient objects ready for Graph API use.
        """
        from email.utils import parseaddr

        from msgraph.generated.models import email_address, recipient

        recipients: List[Any] = []
        for email in email_list:
            # Extract email address from both formats: "Email", "Name <Email>"
            name, addr = parseaddr(email)
            address = email_address.EmailAddress(address=addr)
            if name:
                address.name = name
            recp = recipient.Recipient(email_address=address)
            recipients.append(recp)
        return recipients

    def _create_message(
        self,
        to_email: Optional[List[str]] = None,
        subject: Optional[str] = None,
        content: Optional[str] = None,
        is_content_html: bool = False,
        attachments: Optional[List[str]] = None,
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        reply_to: Optional[List[str]] = None,
    ):
        """Creates a message object for sending or updating emails.

        This helper method is used internally to construct Microsoft Graph
        message objects. It's used by methods like send_email,
        create_draft_email, and update_draft_message. All parameters are
        optional to allow partial updates when modifying existing messages.

        Args:
            to_email (Optional[List[str]]): List of recipient email addresses.
                (default: :obj:`None`)
            subject (Optional[str]): The subject of the email.
                (default: :obj:`None`)
            content (Optional[str]): The body content of the email.
                (default: :obj:`None`)
            is_content_html (bool): If True, the content type will be set to
                HTML; otherwise, it will be Text. (default: :obj:`False`)
            attachments (Optional[List[str]]): List of file paths to attach
                to the email. (default: :obj:`None`)
            cc_recipients (Optional[List[str]]): List of CC recipient email
                addresses. (default: :obj:`None`)
            bcc_recipients (Optional[List[str]]): List of BCC recipient email
                addresses. (default: :obj:`None`)
            reply_to (Optional[List[str]]): List of email addresses that will
                receive replies when recipients use the "Reply" button. This
                allows replies to be directed to different addresses than the
                sender's address. (default: :obj:`None`)

        Returns:
            message.Message: A Microsoft Graph message object with only the
                provided fields set.
        """
        from msgraph.generated.models import body_type, item_body, message

        content_type = (
            body_type.BodyType.Html
            if is_content_html
            else body_type.BodyType.Text
        )

        mail_message = message.Message()

        # Set body content if provided
        if content:
            message_body = item_body.ItemBody(
                content_type=content_type, content=content
            )
            mail_message.body = message_body

        # Set to recipients if provided
        if to_email:
            mail_message.to_recipients = self._create_recipients(to_email)

        # Set subject if provided
        if subject:
            mail_message.subject = subject

        # Add CC recipients if provided
        if cc_recipients:
            mail_message.cc_recipients = self._create_recipients(cc_recipients)

        # Add BCC recipients if provided
        if bcc_recipients:
            mail_message.bcc_recipients = self._create_recipients(
                bcc_recipients
            )

        # Add reply-to addresses if provided
        if reply_to:
            mail_message.reply_to = self._create_recipients(reply_to)

        # Add attachments if provided
        if attachments:
            mail_message.attachments = self._create_attachments(attachments)

        return mail_message

    async def outlook_send_email(
        self,
        to_email: List[str],
        subject: str,
        content: str,
        is_content_html: bool = False,
        attachments: Optional[List[str]] = None,
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        reply_to: Optional[List[str]] = None,
        save_to_sent_items: bool = True,
    ) -> Dict[str, Any]:
        """Sends an email via Microsoft Outlook.

        Args:
            to_email (List[str]): List of recipient email addresses.
            subject (str): The subject of the email.
            content (str): The body content of the email.
            is_content_html (bool): If True, the content type will be set to
                HTML; otherwise, it will be Text. (default: :obj:`False`)
            attachments (Optional[List[str]]): List of file paths to attach
                to the email. (default: :obj:`None`)
            cc_recipients (Optional[List[str]]): List of CC recipient email
                addresses. (default: :obj:`None`)
            bcc_recipients (Optional[List[str]]): List of BCC recipient email
                addresses. (default: :obj:`None`)
            reply_to (Optional[List[str]]): List of email addresses that will
                receive replies when recipients use the "Reply" button. This
                allows replies to be directed to different addresses than the
                sender's address. (default: :obj:`None`)
            save_to_sent_items (bool): Whether to save the email to sent
                items. (default: :obj:`True`)

        Returns:
            Dict[str, Any]: A dictionary containing the result of the email
                sending operation.
        """
        from msgraph.generated.users.item.send_mail.send_mail_post_request_body import (  # noqa: E501
            SendMailPostRequestBody,
        )

        try:
            # Validate all email addresses
            invalid_emails = self._get_invalid_emails(
                to_email, cc_recipients, bcc_recipients, reply_to
            )
            if invalid_emails:
                error_msg = (
                    f"Invalid email address(es) provided: "
                    f"{', '.join(invalid_emails)}"
                )
                logger.error(error_msg)
                return {"error": error_msg}

            mail_message = self._create_message(
                to_email=to_email,
                subject=subject,
                content=content,
                is_content_html=is_content_html,
                attachments=attachments,
                cc_recipients=cc_recipients,
                bcc_recipients=bcc_recipients,
                reply_to=reply_to,
            )

            request = SendMailPostRequestBody(
                message=mail_message,
                save_to_sent_items=save_to_sent_items,
            )

            await self.client.me.send_mail.post(request)

            logger.info("Email sent successfully.")
            return {
                'status': 'success',
                'message': 'Email sent successfully',
                'recipients': to_email,
                'subject': subject,
            }
        except Exception as e:
            logger.exception("Failed to send email")
            return {"error": f"Failed to send email: {e!s}"}

    async def outlook_create_draft_email(
        self,
        to_email: List[str],
        subject: str,
        content: str,
        is_content_html: bool = False,
        attachments: Optional[List[str]] = None,
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        reply_to: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Creates a draft email in Microsoft Outlook.

        Args:
            to_email (List[str]): List of recipient email addresses.
            subject (str): The subject of the email.
            content (str): The body content of the email.
            is_content_html (bool): If True, the content type will be set to
                HTML; otherwise, it will be Text. (default: :obj:`False`)
            attachments (Optional[List[str]]): List of file paths to attach
                to the email. (default: :obj:`None`)
            cc_recipients (Optional[List[str]]): List of CC recipient email
                addresses. (default: :obj:`None`)
            bcc_recipients (Optional[List[str]]): List of BCC recipient email
                addresses. (default: :obj:`None`)
            reply_to (Optional[List[str]]): List of email addresses that will
                receive replies when recipients use the "Reply" button. This
                allows replies to be directed to different addresses than the
                sender's address. (default: :obj:`None`)

        Returns:
            Dict[str, Any]: A dictionary containing the result of the draft
                email creation operation, including the draft ID.

        """
        # Validate all email addresses
        invalid_emails = self._get_invalid_emails(
            to_email, cc_recipients, bcc_recipients, reply_to
        )
        if invalid_emails:
            error_msg = (
                f"Invalid email address(es) provided: "
                f"{', '.join(invalid_emails)}"
            )
            logger.error(error_msg)
            return {"error": error_msg}

        try:
            request_body = self._create_message(
                to_email=to_email,
                subject=subject,
                content=content,
                is_content_html=is_content_html,
                attachments=attachments,
                cc_recipients=cc_recipients,
                bcc_recipients=bcc_recipients,
                reply_to=reply_to,
            )

            result = await self.client.me.messages.post(request_body)

            logger.info("Draft email created successfully.")
            return {
                'status': 'success',
                'message': 'Draft email created successfully',
                'draft_id': result.id,
                'recipients': to_email,
                'subject': subject,
            }
        except Exception as e:
            error_msg = f"Failed to create draft email: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def outlook_send_draft_email(self, draft_id: str) -> Dict[str, Any]:
        """Sends a draft email via Microsoft Outlook.

        Args:
            draft_id (str): The ID of the draft email to send. Can be
                obtained either by creating a draft via
                `create_draft_email()` or from the 'message_id' field in
                messages returned by `list_messages()`.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the draft
                email sending operation.
        """
        try:
            await self.client.me.messages.by_message_id(draft_id).send.post()

            logger.info(f"Draft email with ID {draft_id} sent successfully.")
            return {
                'status': 'success',
                'message': 'Draft email sent successfully',
                'draft_id': draft_id,
            }
        except Exception as e:
            error_msg = f"Failed to send draft email: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def outlook_delete_email(self, message_id: str) -> Dict[str, Any]:
        """Deletes an email from Microsoft Outlook.

        Args:
            message_id (str): The ID of the email to delete. Can be obtained
                from the 'message_id' field in messages returned by
                `list_messages()`.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the email
                deletion operation.
        """
        try:
            await self.client.me.messages.by_message_id(message_id).delete()
            logger.info(f"Email with ID {message_id} deleted successfully.")
            return {
                'status': 'success',
                'message': 'Email deleted successfully',
                'message_id': message_id,
            }
        except Exception as e:
            error_msg = f"Failed to delete email: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def outlook_move_message_to_folder(
        self, message_id: str, destination_folder_id: str
    ) -> Dict[str, Any]:
        """Moves an email to a specified folder in Microsoft Outlook.

        Args:
            message_id (str): The ID of the email to move. Can be obtained
                from the 'message_id' field in messages returned by
                `list_messages()`.
            destination_folder_id (str): The destination folder ID, or
                a well-known folder name. Supported well-known folder names are
                ("inbox", "drafts", "sentitems", "deleteditems", "junkemail",
                "archive", "outbox").

        Returns:
            Dict[str, Any]: A dictionary containing the result of the email
                move operation.
        """
        from msgraph.generated.users.item.messages.item.move.move_post_request_body import (  # noqa: E501
            MovePostRequestBody,
        )

        try:
            request_body = MovePostRequestBody(
                destination_id=destination_folder_id,
            )
            message = self.client.me.messages.by_message_id(message_id)
            await message.move.post(request_body)

            logger.info(
                f"Email with ID {message_id} moved to folder "
                f"{destination_folder_id} successfully."
            )
            return {
                'status': 'success',
                'message': 'Email moved successfully',
                'message_id': message_id,
                'destination_folder_id': destination_folder_id,
            }
        except Exception as e:
            error_msg = f"Failed to move email: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def outlook_get_attachments(
        self,
        message_id: str,
        metadata_only: bool = True,
        include_inline_attachments: bool = False,
        save_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves attachments from a Microsoft Outlook email message.

        This method fetches attachments from a specified email message and can
        either return metadata only or download the full attachment content.
        Inline attachments (like embedded images) can optionally be included
        or excluded from the results.
        Also, if a save_path is provided, attachments will be saved to disk.

        Args:
            message_id (str): The unique identifier of the email message from
                which to retrieve attachments. Can be obtained from the
                'message_id' field in messages returned by `list_messages()`.
            metadata_only (bool): If True, returns only attachment metadata
                (name, size, content type, etc.) without downloading the actual
                file content. If False, downloads the full attachment content.
                (default: :obj:`True`)
            include_inline_attachments (bool): If True, includes inline
                attachments (such as embedded images) in the results. If False,
                filters them out. (default: :obj:`False`)
            save_path (Optional[str]): The local directory path where
                attachments should be saved. If provided, attachments are saved
                to disk and the file paths are returned. If None, attachment
                content is returned as base64-encoded strings (only when
                metadata_only=False). (default: :obj:`None`)

        Returns:
            Dict[str, Any]: A dictionary containing the attachment retrieval
            results
        """
        try:
            request_config = None
            if metadata_only:
                request_config = self._build_attachment_query()

            attachments_response = await self._fetch_attachments(
                message_id, request_config
            )
            if not attachments_response:
                return {
                    'status': 'success',
                    'message_id': message_id,
                    'attachments': [],
                    'total_count': 0,
                }

            attachments_list = []
            for attachment in attachments_response.value:
                if not include_inline_attachments and attachment.is_inline:
                    continue
                info = self._process_attachment(
                    attachment,
                    metadata_only,
                    save_path,
                )
                attachments_list.append(info)

            return {
                'status': 'success',
                'message_id': message_id,
                'attachments': attachments_list,
                'total_count': len(attachments_list),
            }

        except Exception as e:
            error_msg = f"Failed to get attachments: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    def _build_attachment_query(self):
        """Constructs the query configuration for fetching attachment metadata.

        Returns:
            AttachmentsRequestBuilderGetRequestConfiguration: Query config
                for the Graph API request.
        """
        from msgraph.generated.users.item.messages.item.attachments.attachments_request_builder import (  # noqa: E501
            AttachmentsRequestBuilder,
        )

        query_params = AttachmentsRequestBuilder.AttachmentsRequestBuilderGetQueryParameters(  # noqa: E501
            select=[
                "id",
                "lastModifiedDateTime",
                "name",
                "contentType",
                "size",
                "isInline",
            ]
        )

        return AttachmentsRequestBuilder.AttachmentsRequestBuilderGetRequestConfiguration(  # noqa: E501
            query_parameters=query_params
        )

    async def _fetch_attachments(
        self, message_id: str, request_config: Optional[Any] = None
    ):
        """Fetches attachments from the Microsoft Graph API.

        Args:
            message_id (str): The email message ID.
            request_config (Optional[Any]): The request configuration with
            query parameters. (default: :obj:`None`)


        Returns:
            Attachments response from the Graph API.
        """
        if not request_config:
            return await self.client.me.messages.by_message_id(
                message_id
            ).attachments.get()
        return await self.client.me.messages.by_message_id(
            message_id
        ).attachments.get(request_configuration=request_config)

    def _process_attachment(
        self,
        attachment,
        metadata_only: bool,
        save_path: Optional[str],
    ):
        """Processes a single attachment and extracts its information.

        Args:
            attachment: The attachment object from Graph API.
            metadata_only (bool): Whether to include content bytes.
            save_path (Optional[str]): Path to save attachment file.

        Returns:
            Dict: Dictionary containing attachment information.
        """
        import base64

        last_modified = getattr(attachment, 'last_modified_date_time', None)
        info = {
            'id': attachment.id,
            'name': attachment.name,
            'content_type': attachment.content_type,
            'size': attachment.size,
            'is_inline': getattr(attachment, 'is_inline', False),
            'last_modified_date_time': (
                last_modified.isoformat() if last_modified else None
            ),
        }

        if not metadata_only:
            content_bytes = getattr(attachment, 'content_bytes', None)
            if content_bytes:
                # Decode once because bytes contain Base64 text
                decoded_bytes = base64.b64decode(content_bytes)

                if save_path:
                    file_path = self._save_attachment_file(
                        save_path, attachment.name, decoded_bytes
                    )
                    info['saved_path'] = file_path
                    logger.info(
                        f"Attachment {attachment.name} saved to {file_path}"
                    )
                else:
                    info['content_bytes'] = content_bytes

        return info

    def _save_attachment_file(
        self,
        save_path: str,
        attachment_name: str,
        content_bytes: bytes,
        cannot_overwrite: bool = True,
    ) -> str:
        """Saves attachment content to a file on disk.

        Args:
            save_path (str): Directory path where file should be saved.
            attachment_name (str): Name of the attachment file.
            content_bytes (bytes): The file content as bytes.
            cannot_overwrite (bool): If True, appends counter to filename
                if file exists. (default: :obj:`True`)

        Returns:
            str: The full file path where the attachment was saved.
        """
        import os

        os.makedirs(save_path, exist_ok=True)
        file_path = os.path.join(save_path, attachment_name)
        file_path_already_exists = os.path.exists(file_path)
        if cannot_overwrite and file_path_already_exists:
            count = 1
            name, ext = os.path.splitext(attachment_name)
            while os.path.exists(file_path):
                file_path = os.path.join(save_path, f"{name}_{count}{ext}")
                count += 1
        with open(file_path, 'wb') as f:
            f.write(content_bytes)
        return file_path

    def _handle_html_body(self, body_content: str) -> str:
        """Converts HTML email body to plain text.

        Note: This method performs client-side HTML-to-text conversion.

        Args:
            body_content (str): The HTML content of the email body. This
                content is already sanitized by Microsoft Graph API.

        Returns:
            str: Plain text version of the email body with cleaned whitespace
                and removed HTML tags.
        """
        try:
            import html2text

            parser = html2text.HTML2Text()

            parser.ignore_links = False
            parser.inline_links = True
            parser.protect_links = True
            parser.skip_internal_links = True

            parser.ignore_images = False
            parser.images_as_html = False
            parser.images_to_alt = False
            parser.images_with_size = False

            parser.ignore_emphasis = False
            parser.body_width = 0
            parser.single_line_break = True

            return parser.handle(body_content).strip()

        except Exception as e:
            logger.error(f"Failed to parse HTML body: {e!s}")
            return body_content

    def _get_recipients(self, recipient_list: Optional[List[Any]]):
        """Gets a list of recipients from a recipient list object."""
        recipients: List[Dict[str, str]] = []
        if not recipient_list:
            return recipients
        for recipient_info in recipient_list:
            email = recipient_info.email_address.address
            name = recipient_info.email_address.name
            recipients.append({'address': email, 'name': name})
        return recipients

    async def _extract_message_details(
        self,
        message: Any,
        return_html_content: bool = False,
        include_attachments: bool = False,
        attachment_metadata_only: bool = True,
        include_inline_attachments: bool = False,
        attachment_save_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extracts detailed information from a message object.

        This function processes a message object (either from a list response
        or a direct fetch) and extracts all relevant details. It can
        optionally fetch attachments but does not make additional API calls
        for basic message information.

        Args:
            message (Any): The Microsoft Graph message object to extract
                details from.
            return_html_content (bool): If True and body content type is HTML,
                returns the raw HTML content without converting it to plain
                text. If False and body_type is 'text', HTML content will be
                converted to plain text.
                (default: :obj:`False`)
            include_attachments (bool): Whether to include attachment
                information. If True, will make an API call to fetch
                attachments. (default: :obj:`False`)
            attachment_metadata_only (bool): If True, returns only attachment
                metadata without downloading content. If False, downloads full
                attachment content. Only used when include_attachments=True.
                (default: :obj:`True`)
            include_inline_attachments (bool): If True, includes inline
                attachments in the results. Only used when
                include_attachments=True. (default: :obj:`False`)
            attachment_save_path (Optional[str]): Directory path where
                attachments should be saved. Only used when
                include_attachments=True and attachment_metadata_only=False.
                (default: :obj:`None`)

        Returns:
            Dict[str, Any]: A dictionary containing the message details
                including:
                - Basic info (message_id, subject, from, received_date_time,
                  body etc.)
                - Recipients (to_recipients, cc_recipients, bcc_recipients)
                - Attachment information (if requested)
        """
        try:
            # Validate message object
            from msgraph.generated.models.message import Message

            if not isinstance(message, Message):
                return {'error': 'Invalid message object provided'}
            # Extract basic details
            details = {
                'message_id': message.id,
                'subject': message.subject,
                # Draft messages have from_ as None
                'from': (
                    self._get_recipients([message.from_])
                    if message.from_
                    else None
                ),
                'to_recipients': self._get_recipients(message.to_recipients),
                'cc_recipients': self._get_recipients(message.cc_recipients),
                'bcc_recipients': self._get_recipients(message.bcc_recipients),
                'received_date_time': (
                    message.received_date_time.isoformat()
                    if message.received_date_time
                    else None
                ),
                'sent_date_time': (
                    message.sent_date_time.isoformat()
                    if message.sent_date_time
                    else None
                ),
                'has_non_inline_attachments': message.has_attachments,
                'importance': (str(message.importance)),
                'is_read': message.is_read,
                'is_draft': message.is_draft,
                'body_preview': message.body_preview,
            }

            body_content = message.body.content if message.body else ''
            content_type = message.body.content_type if (message.body) else ''

            # Convert HTML to text if requested and content is HTML
            is_content_html = content_type and "html" in str(content_type)
            if is_content_html and not return_html_content and body_content:
                body_content = self._handle_html_body(body_content)

            details['body'] = body_content
            details['body_type'] = content_type

            # Include attachments if requested
            if not include_attachments:
                return details

            attachments_info = await self.outlook_get_attachments(
                message_id=details['message_id'],
                metadata_only=attachment_metadata_only,
                include_inline_attachments=include_inline_attachments,
                save_path=attachment_save_path,
            )
            details['attachments'] = attachments_info.get('attachments', [])
            return details

        except Exception as e:
            error_msg = f"Failed to extract message details: {e!s}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    async def outlook_get_message(
        self,
        message_id: str,
        return_html_content: bool = False,
        include_attachments: bool = False,
        attachment_metadata_only: bool = True,
        include_inline_attachments: bool = False,
        attachment_save_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves a single email message by ID from Microsoft Outlook.

        This method fetches a specific email message using its unique
        identifier and returns detailed information including subject, sender,
        recipients, body content, and optionally attachments.

        Args:
            message_id (str): The unique identifier of the email message to
                retrieve. Can be obtained from the 'message_id' field in
                messages returned by `list_messages()`.
            return_html_content (bool): If True and body content type is HTML,
                returns the raw HTML content without converting it to plain
                text. If False and body_type is HTML, content will be converted
                to plain text. (default: :obj:`False`)
            include_attachments (bool): Whether to include attachment
                information in the response. (default: :obj:`False`)
            attachment_metadata_only (bool): If True, returns only attachment
                metadata without downloading content. If False, downloads full
                attachment content. Only used when include_attachments=True.
                (default: :obj:`True`)
            include_inline_attachments (bool): If True, includes inline
                attachments in the results. Only used when
                include_attachments=True. (default: :obj:`False`)
            attachment_save_path (Optional[str]): Directory path where
                attachments should be saved. Only used when
                include_attachments=True and attachment_metadata_only=False.
                (default: :obj:`None`)

        Returns:
            Dict[str, Any]: A dictionary containing the message details
                including message_id, subject, from, to_recipients,
                cc_recipients, bcc_recipients, received_date_time,
                sent_date_time, body, body_type, has_attachments, importance,
                is_read, is_draft, body_preview, and optionally attachments.
        """
        try:
            message = await self.client.me.messages.by_message_id(
                message_id
            ).get()

            if not message:
                error_msg = f"Message with ID {message_id} not found"
                logger.error(error_msg)
                return {"error": error_msg}

            details = await self._extract_message_details(
                message=message,
                return_html_content=return_html_content,
                include_attachments=include_attachments,
                attachment_metadata_only=attachment_metadata_only,
                include_inline_attachments=include_inline_attachments,
                attachment_save_path=attachment_save_path,
            )

            logger.info(f"Message with ID {message_id} retrieved successfully")
            return {
                'status': 'success',
                'message': details,
            }

        except Exception as e:
            error_msg = f"Failed to get message: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def _get_messages_from_folder(
        self,
        folder_id: str,
        request_config,
    ):
        """Fetches messages from a specific folder.

        Args:
            folder_id (str): The folder ID or well-known folder name.
            request_config: The request configuration with query parameters.

        Returns:
            Messages response from the Graph API, or None if folder not found.
        """
        try:
            messages = await self.client.me.mail_folders.by_mail_folder_id(
                folder_id
            ).messages.get(request_configuration=request_config)
            return messages
        except Exception as e:
            logger.warning(
                f"Failed to get messages from folder {folder_id}: {e!s}"
            )
            return None

    async def outlook_list_messages(
        self,
        folder_ids: Optional[List[str]] = None,
        filter_query: Optional[str] = None,
        order_by: Optional[List[str]] = None,
        top: int = 10,
        skip: int = 0,
        return_html_content: bool = False,
        include_attachment_metadata: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieves messages from Microsoft Outlook using Microsoft Graph API.

        Note: Each folder requires a separate API call. Use folder_ids=None
        to search the entire mailbox in one call for better performance.

        When using $filter and $orderby in the same query to get messages,
        make sure to specify properties in the following ways:
        Properties that appear in $orderby must also appear in $filter.
        Properties that appear in $orderby are in the same order as in $filter.
        Properties that are present in $orderby appear in $filter before any
        properties that aren't.
        Failing to do this results in the following error:
        Error code: InefficientFilter
        Error message: The restriction or sort order is too complex for this
        operation.

        Args:
            folder_ids (Optional[List[str]]): Folder IDs or well-known names
                ("inbox", "drafts", "sentitems", "deleteditems", "junkemail",
                "archive", "outbox"). None searches the entire mailbox.
            filter_query (Optional[str]): OData filter for messages.
                Examples:
                - Sender: "from/emailAddress/address eq 'john@example.com'"
                - Subject: "subject eq 'Meeting Notes'",
                           "contains(subject, 'urgent')"
                - Read status: "isRead eq false", "isRead eq true"
                - Attachments: "hasAttachments eq true/false"
                - Importance: "importance eq 'high'/'normal'/'low'"
                - Date: "receivedDateTime ge 2024-01-01T00:00:00Z"
                - Combine: "isRead eq false and hasAttachments eq true"
                - Negation: "not(isRead eq true)"
                Reference: https://learn.microsoft.com/en-us/graph/filter-query-parameter
            order_by (Optional[List[str]]): OData orderBy for sorting messages.
                Examples:
                - Date: "receivedDateTime desc/asc", "sentDateTime desc"
                - Sender: "from/emailAddress/address asc/desc",
                - Subject: "subject asc/desc"
                - Importance: "importance desc/asc"
                - Size: "size desc/asc"
                - Multi-field: "importance desc, receivedDateTime desc"
                Reference: https://learn.microsoft.com/en-us/graph/query-parameters
            top (int): Max messages per folder (default: 10)
            skip (int): Messages to skip for pagination (default: 0)
            return_html_content (bool): Return raw HTML if True;
            else convert to text (default: False)
            include_attachment_metadata (bool): Include attachment metadata
            (name, size, type); content not included (default: False)

        Returns:
            Dict[str, Any]: Dictionary containing messages and
            attachment metadata if requested.
        """

        try:
            from msgraph.generated.users.item.mail_folders.item.messages.messages_request_builder import (  # noqa: E501
                MessagesRequestBuilder,
            )

            # Build query parameters
            query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(  # noqa: E501
                top=top,
                skip=skip,
                orderby=order_by,
                filter=filter_query,
            )

            request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(  # noqa: E501
                query_parameters=query_params
            )
            if not folder_ids:
                # Search entire mailbox in a single API call
                messages_response = await self.client.me.messages.get(
                    request_configuration=request_config
                )
                all_messages = []
                if messages_response and messages_response.value:
                    for message in messages_response.value:
                        details = await self._extract_message_details(
                            message=message,
                            return_html_content=return_html_content,
                            include_attachments=include_attachment_metadata,
                            attachment_metadata_only=True,
                            include_inline_attachments=False,
                            attachment_save_path=None,
                        )
                        all_messages.append(details)

                logger.info(
                    f"Retrieved {len(all_messages)} messages from mailbox"
                )

                return {
                    'status': 'success',
                    'messages': all_messages,
                    'total_count': len(all_messages),
                    'skip': skip,
                    'top': top,
                    'folders_searched': ['all'],
                }
            # Search specific folders (requires multiple API calls)
            all_messages = []
            for folder_id in folder_ids:
                messages_response = await self._get_messages_from_folder(
                    folder_id=folder_id,
                    request_config=request_config,
                )

                if not messages_response or not messages_response.value:
                    continue

                # Extract details from each message
                for message in messages_response.value:
                    details = await self._extract_message_details(
                        message=message,
                        return_html_content=return_html_content,
                        include_attachments=include_attachment_metadata,
                        attachment_metadata_only=True,
                        include_inline_attachments=False,
                        attachment_save_path=None,
                    )
                    all_messages.append(details)

            logger.info(
                f"Retrieved {len(all_messages)} messages from "
                f"{len(folder_ids)} folder(s)"
            )

            return {
                'status': 'success',
                'messages': all_messages,
                'total_count': len(all_messages),
                'skip': skip,
                'top': top,
                'folders_searched': folder_ids,
            }

        except Exception as e:
            error_msg = f"Failed to list messages: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def outlook_reply_to_email(
        self,
        message_id: str,
        content: str,
        reply_all: bool = False,
    ) -> Dict[str, Any]:
        """Replies to an email in Microsoft Outlook.

        Args:
            message_id (str): The ID of the email to reply to.
            content (str): The body content of the reply email.
            reply_all (bool): If True, replies to all recipients of the
                original email. If False, replies only to the sender.
                (default: :obj:`False`)

        Returns:
            Dict[str, Any]: A dictionary containing the result of the email
                reply operation.

        Raises:
            ValueError: If replying to the email fails.
        """
        from msgraph.generated.users.item.messages.item.reply.reply_post_request_body import (  # noqa: E501
            ReplyPostRequestBody,
        )
        from msgraph.generated.users.item.messages.item.reply_all.reply_all_post_request_body import (  # noqa: E501
            ReplyAllPostRequestBody,
        )

        try:
            message_request = self.client.me.messages.by_message_id(message_id)
            if reply_all:
                request_body_reply_all = ReplyAllPostRequestBody(
                    comment=content
                )
                await message_request.reply_all.post(request_body_reply_all)
            else:
                request_body = ReplyPostRequestBody(comment=content)
                await message_request.reply.post(request_body)

            reply_type = "Reply All" if reply_all else "Reply"
            logger.info(
                f"{reply_type} to email with ID {message_id} sent "
                "successfully."
            )

            return {
                'status': 'success',
                'message': f'{reply_type} sent successfully',
                'message_id': message_id,
                'reply_type': reply_type.lower(),
            }

        except Exception as e:
            error_msg = f"Failed to reply to email: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def outlook_update_draft_message(
        self,
        message_id: str,
        subject: Optional[str] = None,
        content: Optional[str] = None,
        is_content_html: bool = False,
        to_email: Optional[List[str]] = None,
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        reply_to: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Updates an existing draft email message in Microsoft Outlook.

        Important: Any parameter provided will completely replace the original
        value. For example, if you want to add a new recipient while keeping
        existing ones, you must pass all recipients (both original and new) in
        the to_email parameter.

        Note: This method is intended for draft messages only and not for
        sent messages.

        Args:
            message_id (str): The ID of the draft message to update.
            subject (Optional[str]): Change the subject of the email.
                Replaces the original subject completely.
                (default: :obj:`None`)
            content (Optional[str]): Change the body content of the email.
                Replaces the original content completely.
                (default: :obj:`None`)
            is_content_html (bool): Change the content type. If True, sets
                content type to HTML; if False, sets to plain text.
                (default: :obj:`False`)
            to_email (Optional[List[str]]): Change the recipient email
                addresses. Replaces all original recipients completely.
                (default: :obj:`None`)
            cc_recipients (Optional[List[str]]): Change the CC recipient
                email addresses. Replaces all original CC recipients
                completely. (default: :obj:`None`)
            bcc_recipients (Optional[List[str]]): Change the BCC recipient
                email addresses. Replaces all original BCC recipients
                completely. (default: :obj:`None`)
            reply_to (Optional[List[str]]): Change the email addresses that
                will receive replies. Replaces all original reply-to addresses
                completely. (default: :obj:`None`)

        Returns:
            Dict[str, Any]: A dictionary containing the result of the update
                operation.
        """
        try:
            # Validate all email addresses if provided
            invalid_emails = self._get_invalid_emails(
                to_email, cc_recipients, bcc_recipients, reply_to
            )
            if invalid_emails:
                error_msg = (
                    f"Invalid email address(es) provided: "
                    f"{', '.join(invalid_emails)}"
                )
                logger.error(error_msg)
                return {"error": error_msg}

            # Create message with only the fields to update
            mail_message = self._create_message(
                to_email=to_email,
                subject=subject,
                content=content,
                is_content_html=is_content_html,
                cc_recipients=cc_recipients,
                bcc_recipients=bcc_recipients,
                reply_to=reply_to,
            )

            # Update the message using PATCH
            await self.client.me.messages.by_message_id(message_id).patch(
                mail_message
            )

            logger.info(
                f"Draft message with ID {message_id} updated successfully."
            )

            # Build dict of updated parameters (only include non-None values)
            updated_params = {
                k: v
                for k, v in {
                    'subject': subject,
                    'content': content,
                    'to_email': to_email,
                    'cc_recipients': cc_recipients,
                    'bcc_recipients': bcc_recipients,
                    'reply_to': reply_to,
                }.items()
                if v
            }

            return {
                'status': 'success',
                'message': 'Draft message updated successfully',
                'message_id': message_id,
                'updated_params': updated_params,
            }

        except Exception as e:
            error_msg = f"Failed to update draft message: {e!s}"
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
            FunctionTool(self.outlook_send_email),
            FunctionTool(self.outlook_create_draft_email),
            FunctionTool(self.outlook_send_draft_email),
            FunctionTool(self.outlook_delete_email),
            FunctionTool(self.outlook_move_message_to_folder),
            FunctionTool(self.outlook_get_attachments),
            FunctionTool(self.outlook_get_message),
            FunctionTool(self.outlook_list_messages),
            FunctionTool(self.outlook_reply_to_email),
            FunctionTool(self.outlook_update_draft_message),
        ]
