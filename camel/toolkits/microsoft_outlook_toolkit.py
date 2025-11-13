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

            # Initialize code attribute to None
            server.code = None

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

    def _validate_emails(self, emails: Optional[List[str]]) -> List[str]:
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
        to_email: Optional[List[str]],
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        reply_to: Optional[List[str]] = None,
    ):
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
            FunctionTool(self.create_draft_email),
            FunctionTool(self.send_draft_email),
            FunctionTool(self.delete_email),
            FunctionTool(self.move_message_to_folder),
            FunctionTool(self.get_attachments),
            FunctionTool(self.get_message),
            FunctionTool(self.list_messages),
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

    async def delete_email(self, message_id: str) -> Dict[str, Any]:
        """Deletes an email from Microsoft Outlook.

        Args:
            message_id (str): The ID of the email to delete.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the email
                deletion operation.

        Raises:
            ValueError: If deleting the email fails.
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

    async def move_message_to_folder(
        self, message_id: str, destination_folder_id: str
    ) -> Dict[str, Any]:
        """Moves an email to a specified folder in Microsoft Outlook.

        Args:
            message_id (str): The ID of the email to move.
                destination_folder_id (str): The destination folder ID, or
                a well-known folder name. For a list of supported
                well-known folder names, see
                https://learn.microsoft.com/en-us/graph/api/resources/mailfolder?view=graph-rest-1.0.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the email
                move operation.

        Raises:
            ValueError: If moving the email fails.
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

    async def get_attachments(
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
                which to retrieve attachments.
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
        """Constructs the query configuration for fetching attachments.

        Args:
            metadata_only (bool): Whether to fetch only metadata or include
                content bytes.

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

        info = {
            'id': attachment.id,
            'name': attachment.name,
            'content_type': attachment.content_type,
            'size': attachment.size,
            'is_inline': getattr(attachment, 'is_inline', False),
            'last_modified_date_time': (
                attachment.last_modified_date_time.isoformat()
            ),
        }

        if not metadata_only:
            content_bytes = getattr(attachment, 'content_bytes', None)
            if content_bytes:
                # Decode once because bytes contain Base64 text '
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
            from bs4 import BeautifulSoup

            # Parse HTML content (already sanitized by Microsoft Graph)
            soup = BeautifulSoup(body_content, 'html.parser')

            # Remove script and style elements (defense in depth)
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text and clean up whitespace
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (
                phrase.strip() for line in lines for phrase in line.split("  ")
            )
            text = '\n'.join(chunk for chunk in chunks if chunk)
            return text

        except Exception as e:
            logger.error(f"Failed to parse HTML body: {e!s}")
            return body_content

    def _get_recipients(self, recipient_list: Optional[List[Any]]):
        """Gets a list of recipients from a recipient list object."""
        recipients = []
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
                converted to plain text. Only applies when include_body=True.
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
                - Basic info (id, subject, from, received_date_time,body etc.)
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
                'id': message.id,
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

            attachments_info = await self.get_attachments(
                message_id=details['id'],
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

    async def get_message(
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
                retrieve.
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
                including id, subject, from, to_recipients, cc_recipients,
                bcc_recipients, received_date_time, sent_date_time, body,
                body_type, has_attachments, importance, is_read, is_draft,
                body_preview, and optionally attachments.

        Raises:
            ValueError: If retrieving the message fails or message_id is
                invalid.
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

    async def list_messages(
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
                (default: "receivedDateTime desc")
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
            if order_by:
                query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(  # noqa: E501
                    top=top,
                    skip=skip,
                    orderby=order_by,
                )
            else:
                query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(  # noqa: E501
                    top=top,
                    skip=skip,
                )

            if filter_query:
                query_params.filter = filter_query

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
                            include_inline_attachments=True,
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
