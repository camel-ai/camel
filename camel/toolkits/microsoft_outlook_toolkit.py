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
from typing import Any, Dict, List, Optional

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

        self.scopes = ["offline_access", "Mail.Send", "Mail.ReadWrite"]
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

    def _validate_email(self, email: str) -> bool:
        """Validates a single email address.

        Args:
            email (str): Email address to validate.

        Returns:
            bool: True if the email is valid, False otherwise.
        """
        import re

        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        return bool(email_pattern.match(email))

    def _validate_emails(self, emails: List[str]) -> List[str]:
        """Validates a list of email addresses.

        Args:
            emails (List[str]): List of email addresses to validate.

        Returns:
            List[str]: List of valid email addresses.

        Raises:
            ValueError: If no valid email addresses are found or if any
                email is invalid.
        """
        if not emails:
            error_msg = "No email addresses provided"
            logger.error(error_msg)
            raise ValueError(error_msg)

        valid_emails = []

        for email in emails:
            if self._validate_email(email):
                valid_emails.append(email)
            else:
                error_msg = f"Invalid email address: {email}"
                logger.error(error_msg)
                raise ValueError(error_msg)

        return valid_emails

    def _validate_all_email_addresses(
        self,
        to_email: List[str],
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        reply_to: Optional[List[str]] = None,
    ) -> Dict[str, Optional[List[str]]]:
        """Validates all email addresses for to, cc, bcc, and reply_to fields.

        Args:
            to_email (List[str]): List of recipient email addresses.
            cc_recipients (Optional[List[str]]): List of CC recipient email
                addresses. (default: :obj:`None`)
            bcc_recipients (Optional[List[str]]): List of BCC recipient email
                addresses. (default: :obj:`None`)
            reply_to (Optional[List[str]]): List of email addresses that will
                receive replies. (default: :obj:`None`)

        Returns:
            Dict[str, Optional[List[str]]]: A dictionary containing validated
                email addresses for each field:
                - 'to': validated to_email addresses
                - 'cc': validated cc_recipients addresses or None
                - 'bcc': validated bcc_recipients addresses or None
                - 'reply_to': validated reply_to addresses or None

        Raises:
            ValueError: If any email address is invalid in any field.
        """
        validated_emails = {
            'to': self._validate_emails(to_email),
            'cc': None,
            'bcc': None,
            'reply_to': None,
        }

        if cc_recipients:
            validated_emails['cc'] = self._validate_emails(cc_recipients)

        if bcc_recipients:
            validated_emails['bcc'] = self._validate_emails(bcc_recipients)

        if reply_to:
            validated_emails['reply_to'] = self._validate_emails(reply_to)

        return validated_emails

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

                # Create attachment with proper properties
                attachment_obj = FileAttachment()
                attachment_obj.odata_type = "#microsoft.graph.fileAttachment"
                attachment_obj.name = file_name
                attachment_obj.content_bytes = file_content

                attachment_list.append(attachment_obj)

            except Exception as e:
                raise ValueError(f"Failed to attach file {file_path}: {e!s}")

        return attachment_list

    def _create_message(
        self,
        to_email: List[str],
        subject: str,
        content: str,
        attachments: Optional[List[str]] = None,
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        reply_to: Optional[List[str]] = None,
    ):
        """Creates a message object.

        Args:
            to_email (List[str]): List of recipient email addresses.
            subject (str): The subject of the email.
            content (str): The body content of the email.
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
            message.Message: A Microsoft Graph message object.
        """
        from msgraph.generated.models import (
            body_type,
            email_address,
            item_body,
            message,
            recipient,
        )

        message_body = item_body.ItemBody(
            content_type=body_type.BodyType.Text, content=content
        )

        to_recipients = [
            recipient.Recipient(
                email_address=email_address.EmailAddress(address=email)
            )
            for email in to_email
        ]

        mail_message = message.Message(
            subject=subject,
            body=message_body,
            to_recipients=to_recipients,
        )

        # Add CC recipients if provided
        if cc_recipients:
            mail_message.cc_recipients = [
                recipient.Recipient(
                    email_address=email_address.EmailAddress(address=email)
                )
                for email in cc_recipients
            ]

        # Add BCC recipients if provided
        if bcc_recipients:
            mail_message.bcc_recipients = [
                recipient.Recipient(
                    email_address=email_address.EmailAddress(address=email)
                )
                for email in bcc_recipients
            ]

        # Add reply-to addresses if provided
        if reply_to:
            mail_message.reply_to = [
                recipient.Recipient(
                    email_address=email_address.EmailAddress(address=email)
                )
                for email in reply_to
            ]

        # Add attachments if provided
        if attachments:
            mail_message.attachments = self._create_attachments(attachments)

        return mail_message

    async def send_email(
        self,
        to_email: List[str],
        subject: str,
        content: str,
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

        Raises:
            ValueError: If sending the email fails or if email addresses are
                invalid.
        """
        from msgraph.generated.users.item.send_mail.send_mail_post_request_body import (  # noqa: E501
            SendMailPostRequestBody,
        )

        # Validate all email addresses
        try:
            validated = self._validate_all_email_addresses(
                to_email=to_email,
                cc_recipients=cc_recipients,
                bcc_recipients=bcc_recipients,
                reply_to=reply_to,
            )
        except ValueError as e:
            error_msg = str(e)
            return {"error": error_msg}

        try:
            mail_message = self._create_message(
                to_email=validated['to'],
                subject=subject,
                content=content,
                attachments=attachments,
                cc_recipients=validated['cc'],
                bcc_recipients=validated['bcc'],
                reply_to=validated['reply_to'],
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
                'recipients': validated['to'],
                'subject': subject,
            }
        except Exception as e:
            error_msg = f"Failed to send email: {e!s}"
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
            FunctionTool(self.send_email),
        ]

    async def create_draft_email(
        self,
        to_email: List[str],
        subject: str,
        content: str,
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

        Raises:
            ValueError: If creating the draft email fails or if email
                addresses are invalid.
        """
        # Validate all email addresses
        try:
            validated = self._validate_all_email_addresses(
                to_email=to_email,
                cc_recipients=cc_recipients,
                bcc_recipients=bcc_recipients,
                reply_to=reply_to,
            )
        except ValueError as e:
            error_msg = str(e)
            return {"error": error_msg}

        try:
            request_body = self._create_message(
                to_email=validated['to'],
                subject=subject,
                content=content,
                attachments=attachments,
                cc_recipients=validated['cc'],
                bcc_recipients=validated['bcc'],
                reply_to=validated['reply_to'],
            )

            result = await self.client.me.messages.post(request_body)

            logger.info("Draft email created successfully.")
            return {
                'status': 'success',
                'message': 'Draft email created successfully',
                'draft_id': result.id,
                'recipients': validated['to'],
                'subject': subject,
            }
        except Exception as e:
            error_msg = f"Failed to create draft email: {e!s}"
            logger.error(error_msg)
            return {"error": error_msg}

    async def send_draft_email(self, draft_id: str) -> Dict[str, Any]:
        """Sends a draft email via Microsoft Outlook.

        Args:
            draft_id (str): The ID of the draft email to send.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the draft
                email sending operation.

        Raises:
            ValueError: If sending the draft email fails.
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
