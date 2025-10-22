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

from __future__ import annotations

import base64
import json
import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, dependencies_required

if TYPE_CHECKING:
    from googleapiclient.discovery import Resource

logger = get_logger(__name__)


@MCPServer()
class GmailToolkit(BaseToolkit):
    r"""A toolkit for Gmail operations.

    This toolkit provides methods for Gmail operations such as sending emails,
    reading emails, searching emails, managing labels, and creating drafts.

    Attributes:
        credentials_path (Optional[str]): Path to the Google OAuth2 credentials
            JSON file. Can also be set via GMAIL_CREDENTIALS_PATH environment
            variable.
        token_path (Optional[str]): Path to store the OAuth2 token.
            Defaults to 'token.json'.
    """

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        r"""Initializes the GmailToolkit.

        Args:
            credentials_path (Optional[str]): Path to the Google OAuth2
                credentials JSON file. If not provided, uses the
                GMAIL_CREDENTIALS_PATH environment variable.
                (default: :obj:`None`)
            token_path (Optional[str]): Path to store the OAuth2 token.
                (default: :obj:`'token.json'`)
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)
        self.credentials_path = credentials_path or os.environ.get(
            "GMAIL_CREDENTIALS_PATH"
        )
        self.token_path = token_path or "token.json"
        self._service: Optional[Resource] = None

    @dependencies_required("google-auth", "google-auth-oauthlib", "google-api-python-client")
    def _get_gmail_service(self) -> Resource:
        r"""Authenticate and return Gmail API service.

        Returns:
            Resource: Gmail API service object.

        Raises:
            ValueError: If credentials_path is not set.
            ImportError: If required Google packages are not installed.
        """
        if self._service is not None:
            return self._service

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        if not self.credentials_path:
            raise ValueError(
                "credentials_path must be set either via constructor or "
                "GMAIL_CREDENTIALS_PATH environment variable. "
                "See https://developers.google.com/gmail/api/quickstart/python"
            )

        SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
        creds = None

        # Load token if it exists
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(
                self.token_path, SCOPES
            )

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
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        self._service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail service authenticated successfully.")
        return self._service

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
        attachment_paths: Optional[List[str]] = None,
    ) -> str:
        r"""Send an email via Gmail.

        Args:
            to (str): Recipient email address. For multiple recipients,
                separate with commas.
            subject (str): Email subject line.
            body (str): Email body content (plain text or HTML).
            cc (Optional[str]): CC recipients, comma-separated.
                (default: :obj:`None`)
            bcc (Optional[str]): BCC recipients, comma-separated.
                (default: :obj:`None`)
            attachment_paths (Optional[List[str]]): List of file paths to
                attach to the email. (default: :obj:`None`)

        Returns:
            str: JSON string containing the sent message ID and thread ID,
                or an error message.
        """
        try:
            service = self._get_gmail_service()

            message = MIMEMultipart()
            message['To'] = to
            message['Subject'] = subject
            if cc:
                message['Cc'] = cc
            if bcc:
                message['Bcc'] = bcc

            # Add body
            message.attach(MIMEText(body, 'plain'))

            # Add attachments if provided
            if attachment_paths:
                for file_path in attachment_paths:
                    path = Path(file_path)
                    if not path.exists():
                        return f"Error: Attachment file not found: {file_path}"

                    with open(path, 'rb') as f:
                        part = MIMEApplication(f.read(), Name=path.name)
                        part[
                            'Content-Disposition'
                        ] = f'attachment; filename="{path.name}"'
                        message.attach(part)

            # Encode message
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')

            # Send message
            send_message = (
                service.users()
                .messages()
                .send(userId='me', body={'raw': raw_message})
                .execute()
            )

            result = {
                'message_id': send_message['id'],
                'thread_id': send_message['threadId'],
            }
            return json.dumps(result, ensure_ascii=False)

        except Exception as e:
            return f"Error sending email: {str(e)}"

    def search_emails(
        self,
        query: str,
        max_results: int = 10,
        include_spam_trash: bool = False,
    ) -> str:
        r"""Search for emails matching a query.

        Args:
            query (str): Gmail search query (same as in Gmail search box).
                Examples: "from:example@gmail.com", "subject:meeting",
                "is:unread", "has:attachment", "after:2024/01/01".
            max_results (int): Maximum number of emails to return.
                (default: :obj:`10`)
            include_spam_trash (bool): Whether to include emails from
                SPAM and TRASH. (default: :obj:`False`)

        Returns:
            str: JSON string containing list of matching email IDs and
                thread IDs, or an error message.
        """
        try:
            service = self._get_gmail_service()

            results = (
                service.users()
                .messages()
                .list(
                    userId='me',
                    q=query,
                    maxResults=max_results,
                    includeSpamTrash=include_spam_trash,
                )
                .execute()
            )

            messages = results.get('messages', [])

            if not messages:
                return json.dumps(
                    {'message': 'No emails found matching the query.'},
                    ensure_ascii=False,
                )

            return json.dumps(messages, ensure_ascii=False)

        except Exception as e:
            return f"Error searching emails: {str(e)}"

    def read_email(self, message_id: str) -> str:
        r"""Read an email by its message ID.

        Args:
            message_id (str): The ID of the message to read.
                You can get this from search_emails or list_emails.

        Returns:
            str: JSON string containing email details (from, to, subject,
                body, date, labels), or an error message.
        """
        try:
            service = self._get_gmail_service()

            message = (
                service.users()
                .messages()
                .get(userId='me', id=message_id, format='full')
                .execute()
            )

            headers = message['payload']['headers']
            email_data = {
                'id': message['id'],
                'thread_id': message['threadId'],
                'labels': message.get('labelIds', []),
                'snippet': message.get('snippet', ''),
            }

            # Extract common headers
            for header in headers:
                name = header['name'].lower()
                if name in ['from', 'to', 'subject', 'date', 'cc', 'bcc']:
                    email_data[name] = header['value']

            # Extract body
            parts = message['payload'].get('parts', [])
            body = ''

            if parts:
                for part in parts:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode(
                                'utf-8'
                            )
                            break
            else:
                # Single part message
                data = message['payload']['body'].get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')

            email_data['body'] = body

            return json.dumps(email_data, ensure_ascii=False, indent=2)

        except Exception as e:
            return f"Error reading email: {str(e)}"

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        bcc: Optional[str] = None,
    ) -> str:
        r"""Create a draft email.

        Args:
            to (str): Recipient email address.
            subject (str): Email subject line.
            body (str): Email body content.
            cc (Optional[str]): CC recipients, comma-separated.
                (default: :obj:`None`)
            bcc (Optional[str]): BCC recipients, comma-separated.
                (default: :obj:`None`)

        Returns:
            str: JSON string containing the draft ID, or an error message.
        """
        try:
            service = self._get_gmail_service()

            message = MIMEText(body)
            message['To'] = to
            message['Subject'] = subject
            if cc:
                message['Cc'] = cc
            if bcc:
                message['Bcc'] = bcc

            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')

            draft = (
                service.users()
                .drafts()
                .create(
                    userId='me',
                    body={'message': {'raw': raw_message}},
                )
                .execute()
            )

            result = {'draft_id': draft['id'], 'message_id': draft['message']['id']}
            return json.dumps(result, ensure_ascii=False)

        except Exception as e:
            return f"Error creating draft: {str(e)}"

    def send_draft(self, draft_id: str) -> str:
        r"""Send a draft email.

        Args:
            draft_id (str): The ID of the draft to send.
                You can get this from create_draft.

        Returns:
            str: JSON string containing the sent message ID and thread ID,
                or an error message.
        """
        try:
            service = self._get_gmail_service()

            sent_message = (
                service.users()
                .drafts()
                .send(userId='me', body={'id': draft_id})
                .execute()
            )

            result = {
                'message_id': sent_message['id'],
                'thread_id': sent_message['threadId'],
            }
            return json.dumps(result, ensure_ascii=False)

        except Exception as e:
            return f"Error sending draft: {str(e)}"

    def delete_email(self, message_id: str) -> str:
        r"""Move an email to trash.

        Args:
            message_id (str): The ID of the message to delete.

        Returns:
            str: Success message or error message.
        """
        try:
            service = self._get_gmail_service()

            service.users().messages().trash(
                userId='me', id=message_id
            ).execute()

            return f"Email {message_id} moved to trash successfully."

        except Exception as e:
            return f"Error deleting email: {str(e)}"

    def list_labels(self) -> str:
        r"""List all Gmail labels.

        Returns:
            str: JSON string containing list of labels with their IDs and
                names, or an error message.
        """
        try:
            service = self._get_gmail_service()

            results = service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])

            formatted_labels = [
                {'id': label['id'], 'name': label['name']} for label in labels
            ]

            return json.dumps(formatted_labels, ensure_ascii=False, indent=2)

        except Exception as e:
            return f"Error listing labels: {str(e)}"

    def create_label(self, name: str) -> str:
        r"""Create a new Gmail label.

        Args:
            name (str): The name of the label to create.

        Returns:
            str: JSON string containing the new label ID and name,
                or an error message.
        """
        try:
            service = self._get_gmail_service()

            label = (
                service.users()
                .labels()
                .create(
                    userId='me',
                    body={
                        'name': name,
                        'labelListVisibility': 'labelShow',
                        'messageListVisibility': 'show',
                    },
                )
                .execute()
            )

            result = {'id': label['id'], 'name': label['name']}
            return json.dumps(result, ensure_ascii=False)

        except Exception as e:
            return f"Error creating label: {str(e)}"

    def add_label_to_email(self, message_id: str, label_id: str) -> str:
        r"""Add a label to an email.

        Args:
            message_id (str): The ID of the message.
            label_id (str): The ID of the label to add.
                You can get this from list_labels.

        Returns:
            str: Success message or error message.
        """
        try:
            service = self._get_gmail_service()

            service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label_id]},
            ).execute()

            return f"Label {label_id} added to email {message_id} successfully."

        except Exception as e:
            return f"Error adding label: {str(e)}"

    def remove_label_from_email(self, message_id: str, label_id: str) -> str:
        r"""Remove a label from an email.

        Args:
            message_id (str): The ID of the message.
            label_id (str): The ID of the label to remove.
                You can get this from list_labels.

        Returns:
            str: Success message or error message.
        """
        try:
            service = self._get_gmail_service()

            service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': [label_id]},
            ).execute()

            return (
                f"Label {label_id} removed from email {message_id} successfully."
            )

        except Exception as e:
            return f"Error removing label: {str(e)}"

    def mark_as_read(self, message_id: str) -> str:
        r"""Mark an email as read.

        Args:
            message_id (str): The ID of the message to mark as read.

        Returns:
            str: Success message or error message.
        """
        try:
            service = self._get_gmail_service()

            service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']},
            ).execute()

            return f"Email {message_id} marked as read successfully."

        except Exception as e:
            return f"Error marking email as read: {str(e)}"

    def mark_as_unread(self, message_id: str) -> str:
        r"""Mark an email as unread.

        Args:
            message_id (str): The ID of the message to mark as unread.

        Returns:
            str: Success message or error message.
        """
        try:
            service = self._get_gmail_service()

            service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['UNREAD']},
            ).execute()

            return f"Email {message_id} marked as unread successfully."

        except Exception as e:
            return f"Error marking email as unread: {str(e)}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.send_email),
            FunctionTool(self.search_emails),
            FunctionTool(self.read_email),
            FunctionTool(self.create_draft),
            FunctionTool(self.send_draft),
            FunctionTool(self.delete_email),
            FunctionTool(self.list_labels),
            FunctionTool(self.create_label),
            FunctionTool(self.add_label_to_email),
            FunctionTool(self.remove_label_from_email),
            FunctionTool(self.mark_as_read),
            FunctionTool(self.mark_as_unread),
        ]
