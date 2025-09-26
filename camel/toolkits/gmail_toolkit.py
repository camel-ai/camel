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

import base64
import os
import re
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from googleapiclient.discovery import Resource
else:
    Resource = Any

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, api_keys_required

logger = get_logger(__name__)

SCOPES = [
    'https://mail.google.com/',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/contacts.readonly',
    'https://www.googleapis.com/auth/userinfo.profile',
]


@MCPServer()
class GmailToolkit(BaseToolkit):
    r"""A comprehensive toolkit for Gmail operations.

    This class provides methods for Gmail operations including sending emails,
    managing drafts, fetching messages, managing labels, and handling contacts.
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
    ):
        r"""Initializes a new instance of the GmailToolkit class.

        Args:
            timeout (Optional[float]): The timeout value for API requests
                in seconds. If None, no timeout is applied.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)
        self.gmail_service: Any = self._get_gmail_service()
        self.people_service: Any = self._get_people_service()

    def send_email(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[str]] = None,
        is_html: bool = False,
    ) -> Dict[str, Any]:
        r"""Send an email through Gmail.

        Args:
            to (Union[str, List[str]]): Recipient email address(es).
            subject (str): Email subject.
            body (str): Email body content.
            cc (Optional[Union[str, List[str]]]): CC recipient email
                address(es).
            bcc (Optional[Union[str, List[str]]]): BCC recipient email
                address(es).
            attachments (Optional[List[str]]): List of file paths to attach.
            is_html (bool): Whether the body is HTML format.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the
                operation.
        """
        try:
            # Normalize recipients to lists
            to_list = [to] if isinstance(to, str) else to
            cc_list = [cc] if isinstance(cc, str) else (cc or [])
            bcc_list = [bcc] if isinstance(bcc, str) else (bcc or [])

            # Validate email addresses
            all_recipients = to_list + cc_list + bcc_list
            for email in all_recipients:
                if not self._is_valid_email(email):
                    return {"error": f"Invalid email address: {email}"}

            # Create message
            message = self._create_message(
                to_list, subject, body, cc_list, bcc_list, attachments, is_html
            )

            # Send message
            sent_message = (
                self.gmail_service.users()
                .messages()
                .send(userId='me', body=message)
                .execute()
            )

            return {
                "success": True,
                "message_id": sent_message.get('id'),
                "thread_id": sent_message.get('threadId'),
                "message": "Email sent successfully",
            }

        except Exception as e:
            logger.error("Failed to send email: %s", e)
            return {"error": f"Failed to send email: {e!s}"}

    def reply_to_email(
        self,
        message_id: str,
        reply_body: str,
        reply_all: bool = False,
        is_html: bool = False,
    ) -> Dict[str, Any]:
        r"""Reply to an email message.

        Args:
            message_id (str): The ID of the message to reply to.
            reply_body (str): The reply message body.
            reply_all (bool): Whether to reply to all recipients.
            is_html (bool): Whether the reply body is HTML format.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the
                operation.
        """
        try:
            # Get the original message
            original_message = (
                self.gmail_service.users()
                .messages()
                .get(userId='me', id=message_id)
                .execute()
            )

            # Extract headers
            headers = original_message['payload'].get('headers', [])
            subject = self._get_header_value(headers, 'Subject')
            from_email = self._get_header_value(headers, 'From')
            to_emails = self._get_header_value(headers, 'To')
            cc_emails = self._get_header_value(headers, 'Cc')

            # Prepare reply subject
            if not subject.startswith('Re: '):
                subject = f"Re: {subject}"

            # Prepare recipients
            if reply_all:
                recipients = [from_email]
                if to_emails:
                    recipients.extend(
                        [email.strip() for email in to_emails.split(',')]
                    )
                if cc_emails:
                    recipients.extend(
                        [email.strip() for email in cc_emails.split(',')]
                    )
                # Remove duplicates
                recipients = list(set(recipients))

                # Get current user's email and remove it from recipients
                try:
                    profile_result = self.get_profile()
                    if profile_result.get('success'):
                        current_user_email = profile_result['profile'][
                            'email_address'
                        ]
                        # Remove current user from recipients (handle both
                        # plain email and "Name <email>" format)
                        recipients = [
                            email
                            for email in recipients
                            if email != current_user_email
                            and not email.endswith(f'<{current_user_email}>')
                        ]
                except Exception as e:
                    logger.warning(
                        "Could not get current user email to filter from "
                        "recipients: %s",
                        e,
                    )
            else:
                recipients = [from_email]

            # Create reply message
            message = self._create_message(
                recipients, subject, reply_body, is_html=is_html
            )

            # Send reply
            sent_message = (
                self.gmail_service.users()
                .messages()
                .send(userId='me', body=message)
                .execute()
            )

            return {
                "success": True,
                "message_id": sent_message.get('id'),
                "thread_id": sent_message.get('threadId'),
                "message": "Reply sent successfully",
            }

        except Exception as e:
            logger.error("Failed to reply to email: %s", e)
            return {"error": f"Failed to reply to email: {e!s}"}

    def forward_email(
        self,
        message_id: str,
        to: Union[str, List[str]],
        forward_body: Optional[str] = None,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
    ) -> Dict[str, Any]:
        r"""Forward an email message.

        Args:
            message_id (str): The ID of the message to forward.
            to (Union[str, List[str]]): Recipient email address(es).
            forward_body (Optional[str]): Additional message to include.
            cc (Optional[Union[str, List[str]]]): CC recipient email
                address(es).
            bcc (Optional[Union[str, List[str]]]): BCC recipient email
                address(es).

        Returns:
            Dict[str, Any]: A dictionary containing the result of the
                operation.
        """
        try:
            # Get the original message
            original_message = (
                self.gmail_service.users()
                .messages()
                .get(userId='me', id=message_id)
                .execute()
            )

            # Extract headers
            headers = original_message['payload'].get('headers', [])
            subject = self._get_header_value(headers, 'Subject')
            from_email = self._get_header_value(headers, 'From')
            date = self._get_header_value(headers, 'Date')

            # Prepare forward subject
            if not subject.startswith('Fwd: '):
                subject = f"Fwd: {subject}"

            # Prepare forward body
            if forward_body:
                body = f"{forward_body}\n\n--- Forwarded message ---\n"
            else:
                body = "--- Forwarded message ---\n"

            body += f"From: {from_email}\n"
            body += f"Date: {date}\n"
            body += f"Subject: {subject.replace('Fwd: ', '')}\n\n"

            # Add original message body
            body += self._extract_message_body(original_message)

            # Normalize recipients
            to_list = [to] if isinstance(to, str) else to
            cc_list = [cc] if isinstance(cc, str) else (cc or [])
            bcc_list = [bcc] if isinstance(bcc, str) else (bcc or [])

            # Create forward message
            message = self._create_message(
                to_list, subject, body, cc_list, bcc_list
            )

            # Send forward
            sent_message = (
                self.gmail_service.users()
                .messages()
                .send(userId='me', body=message)
                .execute()
            )

            return {
                "success": True,
                "message_id": sent_message.get('id'),
                "thread_id": sent_message.get('threadId'),
                "message": "Email forwarded successfully",
            }

        except Exception as e:
            logger.error("Failed to forward email: %s", e)
            return {"error": f"Failed to forward email: {e!s}"}

    def create_email_draft(
        self,
        to: Union[str, List[str]],
        subject: str,
        body: str,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        attachments: Optional[List[str]] = None,
        is_html: bool = False,
    ) -> Dict[str, Any]:
        r"""Create an email draft.

        Args:
            to (Union[str, List[str]]): Recipient email address(es).
            subject (str): Email subject.
            body (str): Email body content.
            cc (Optional[Union[str, List[str]]]): CC recipient email
                address(es).
            bcc (Optional[Union[str, List[str]]]): BCC recipient email
                address(es).
            attachments (Optional[List[str]]): List of file paths to attach.
            is_html (bool): Whether the body is HTML format.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the
                operation.
        """
        try:
            # Normalize recipients to lists
            to_list = [to] if isinstance(to, str) else to
            cc_list = [cc] if isinstance(cc, str) else (cc or [])
            bcc_list = [bcc] if isinstance(bcc, str) else (bcc or [])

            # Validate email addresses
            all_recipients = to_list + cc_list + bcc_list
            for email in all_recipients:
                if not self._is_valid_email(email):
                    return {"error": f"Invalid email address: {email}"}

            # Create message
            message = self._create_message(
                to_list, subject, body, cc_list, bcc_list, attachments, is_html
            )

            # Create draft
            draft = (
                self.gmail_service.users()
                .drafts()
                .create(userId='me', body={'message': message})
                .execute()
            )

            return {
                "success": True,
                "draft_id": draft.get('id'),
                "message_id": draft.get('message', {}).get('id'),
                "message": "Draft created successfully",
            }

        except Exception as e:
            logger.error("Failed to create draft: %s", e)
            return {"error": f"Failed to create draft: {e!s}"}

    def send_draft(self, draft_id: str) -> Dict[str, Any]:
        r"""Send a draft email.

        Args:
            draft_id (str): The ID of the draft to send.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the
                operation.
        """
        try:
            # Send draft
            sent_message = (
                self.gmail_service.users()
                .drafts()
                .send(userId='me', body={'id': draft_id})
                .execute()
            )

            return {
                "success": True,
                "message_id": sent_message.get('id'),
                "thread_id": sent_message.get('threadId'),
                "message": "Draft sent successfully",
            }

        except Exception as e:
            logger.error("Failed to send draft: %s", e)
            return {"error": f"Failed to send draft: {e!s}"}

    def fetch_emails(
        self,
        query: str = "",
        max_results: int = 10,
        include_spam_trash: bool = False,
        label_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        r"""Fetch emails with filters and pagination.

        Args:
            query (str): Gmail search query string.
            max_results (int): Maximum number of emails to fetch.
            include_spam_trash (bool): Whether to include spam and trash.
            label_ids (Optional[List[str]]): List of label IDs to filter by.

        Returns:
            Dict[str, Any]: A dictionary containing the fetched emails.
        """
        try:
            # Build request parameters
            request_params = {
                'userId': 'me',
                'maxResults': max_results,
                'includeSpamTrash': include_spam_trash,
            }

            if query:
                request_params['q'] = query
            if label_ids:
                request_params['labelIds'] = label_ids

            # List messages
            messages_result = (
                self.gmail_service.users()
                .messages()
                .list(**request_params)
                .execute()
            )

            messages = messages_result.get('messages', [])
            emails = []

            # Fetch detailed information for each message
            for msg in messages:
                email_detail = self._get_message_details(msg['id'])
                if email_detail:
                    emails.append(email_detail)

            return {
                "success": True,
                "emails": emails,
                "total_count": len(emails),
                "next_page_token": messages_result.get('nextPageToken'),
            }

        except Exception as e:
            logger.error("Failed to fetch emails: %s", e)
            return {"error": f"Failed to fetch emails: {e!s}"}

    def fetch_message_by_id(self, message_id: str) -> Dict[str, Any]:
        r"""Fetch a specific message by ID.

        Args:
            message_id (str): The ID of the message to fetch.

        Returns:
            Dict[str, Any]: A dictionary containing the message details.
        """
        try:
            message_detail = self._get_message_details(message_id)
            if message_detail:
                return {"success": True, "message": message_detail}
            else:
                return {"error": "Message not found"}

        except Exception as e:
            logger.error("Failed to fetch message: %s", e)
            return {"error": f"Failed to fetch message: {e!s}"}

    def fetch_thread_by_id(self, thread_id: str) -> Dict[str, Any]:
        r"""Fetch a thread by ID.

        Args:
            thread_id (str): The ID of the thread to fetch.

        Returns:
            Dict[str, Any]: A dictionary containing the thread details.
        """
        try:
            thread = (
                self.gmail_service.users()
                .threads()
                .get(userId='me', id=thread_id)
                .execute()
            )

            messages = []
            for message in thread.get('messages', []):
                message_detail = self._get_message_details(message['id'])
                if message_detail:
                    messages.append(message_detail)

            return {
                "success": True,
                "thread_id": thread_id,
                "messages": messages,
                "message_count": len(messages),
            }

        except Exception as e:
            logger.error("Failed to fetch thread: %s", e)
            return {"error": f"Failed to fetch thread: {e!s}"}

    def modify_email_labels(
        self,
        message_id: str,
        add_labels: Optional[List[str]] = None,
        remove_labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        r"""Modify labels on an email message.

        Args:
            message_id (str): The ID of the message to modify.
            add_labels (Optional[List[str]]): Labels to add.
            remove_labels (Optional[List[str]]): Labels to remove.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the
                operation.
        """
        try:
            body = {}
            if add_labels:
                body['addLabelIds'] = add_labels
            if remove_labels:
                body['removeLabelIds'] = remove_labels

            if not body:
                return {"error": "No labels to add or remove"}

            modified_message = (
                self.gmail_service.users()
                .messages()
                .modify(userId='me', id=message_id, body=body)
                .execute()
            )

            return {
                "success": True,
                "message_id": message_id,
                "label_ids": modified_message.get('labelIds', []),
                "message": "Labels modified successfully",
            }

        except Exception as e:
            logger.error("Failed to modify labels: %s", e)
            return {"error": f"Failed to modify labels: {e!s}"}

    def move_to_trash(self, message_id: str) -> Dict[str, Any]:
        r"""Move a message to trash.

        Args:
            message_id (str): The ID of the message to move to trash.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the
                operation.
        """
        try:
            trashed_message = (
                self.gmail_service.users()
                .messages()
                .trash(userId='me', id=message_id)
                .execute()
            )

            return {
                "success": True,
                "message_id": message_id,
                "label_ids": trashed_message.get('labelIds', []),
                "message": "Message moved to trash successfully",
            }

        except Exception as e:
            logger.error("Failed to move message to trash: %s", e)
            return {"error": f"Failed to move message to trash: {e!s}"}

    def get_attachment(
        self,
        message_id: str,
        attachment_id: str,
        save_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Get an attachment from a message.

        Args:
            message_id (str): The ID of the message containing the attachment.
            attachment_id (str): The ID of the attachment.
            save_path (Optional[str]): Path to save the attachment file.

        Returns:
            Dict[str, Any]: A dictionary containing the attachment data or
                save result.
        """
        try:
            attachment = (
                self.gmail_service.users()
                .messages()
                .attachments()
                .get(userId='me', messageId=message_id, id=attachment_id)
                .execute()
            )

            # Decode the attachment data
            file_data = base64.urlsafe_b64decode(attachment['data'])

            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(file_data)
                return {
                    "success": True,
                    "message": f"Attachment saved to {save_path}",
                    "file_size": len(file_data),
                }
            else:
                return {
                    "success": True,
                    "data": base64.b64encode(file_data).decode('utf-8'),
                    "file_size": len(file_data),
                }

        except Exception as e:
            logger.error("Failed to get attachment: %s", e)
            return {"error": f"Failed to get attachment: {e!s}"}

    def list_threads(
        self,
        query: str = "",
        max_results: int = 10,
        include_spam_trash: bool = False,
        label_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        r"""List email threads.

        Args:
            query (str): Gmail search query string.
            max_results (int): Maximum number of threads to fetch.
            include_spam_trash (bool): Whether to include spam and trash.
            label_ids (Optional[List[str]]): List of label IDs to filter by.

        Returns:
            Dict[str, Any]: A dictionary containing the thread list.
        """
        try:
            # Build request parameters
            request_params = {
                'userId': 'me',
                'maxResults': max_results,
                'includeSpamTrash': include_spam_trash,
            }

            if query:
                request_params['q'] = query
            if label_ids:
                request_params['labelIds'] = label_ids

            # List threads
            threads_result = (
                self.gmail_service.users()
                .threads()
                .list(**request_params)
                .execute()
            )

            threads = threads_result.get('threads', [])
            thread_list = []

            for thread in threads:
                thread_list.append(
                    {
                        "thread_id": thread['id'],
                        "snippet": thread.get('snippet', ''),
                        "history_id": thread.get('historyId', ''),
                    }
                )

            return {
                "success": True,
                "threads": thread_list,
                "total_count": len(thread_list),
                "next_page_token": threads_result.get('nextPageToken'),
            }

        except Exception as e:
            logger.error("Failed to list threads: %s", e)
            return {"error": f"Failed to list threads: {e!s}"}

    def list_drafts(self, max_results: int = 10) -> Dict[str, Any]:
        r"""List email drafts.

        Args:
            max_results (int): Maximum number of drafts to fetch.

        Returns:
            Dict[str, Any]: A dictionary containing the draft list.
        """
        try:
            drafts_result = (
                self.gmail_service.users()
                .drafts()
                .list(userId='me', maxResults=max_results)
                .execute()
            )

            drafts = drafts_result.get('drafts', [])
            draft_list = []

            for draft in drafts:
                draft_info = {
                    "draft_id": draft['id'],
                    "message_id": draft.get('message', {}).get('id', ''),
                    "thread_id": draft.get('message', {}).get('threadId', ''),
                    "snippet": draft.get('message', {}).get('snippet', ''),
                }
                draft_list.append(draft_info)

            return {
                "success": True,
                "drafts": draft_list,
                "total_count": len(draft_list),
                "next_page_token": drafts_result.get('nextPageToken'),
            }

        except Exception as e:
            logger.error("Failed to list drafts: %s", e)
            return {"error": f"Failed to list drafts: {e!s}"}

    def list_gmail_labels(self) -> Dict[str, Any]:
        r"""List all Gmail labels.

        Returns:
            Dict[str, Any]: A dictionary containing the label list.
        """
        try:
            labels_result = (
                self.gmail_service.users().labels().list(userId='me').execute()
            )

            labels = labels_result.get('labels', [])
            label_list = []

            for label in labels:
                label_info = {
                    "id": label['id'],
                    "name": label['name'],
                    "type": label.get('type', 'user'),
                    "messages_total": label.get('messagesTotal', 0),
                    "messages_unread": label.get('messagesUnread', 0),
                    "threads_total": label.get('threadsTotal', 0),
                    "threads_unread": label.get('threadsUnread', 0),
                }
                label_list.append(label_info)

            return {
                "success": True,
                "labels": label_list,
                "total_count": len(label_list),
            }

        except Exception as e:
            logger.error("Failed to list labels: %s", e)
            return {"error": f"Failed to list labels: {e!s}"}

    def create_label(
        self,
        name: str,
        label_list_visibility: str = "labelShow",
        message_list_visibility: str = "show",
    ) -> Dict[str, Any]:
        r"""Create a new Gmail label.

        Args:
            name (str): The name of the label to create.
            label_list_visibility (str): Label visibility in label list.
            message_list_visibility (str): Label visibility in message list.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the
                operation.
        """
        try:
            label_object = {
                'name': name,
                'labelListVisibility': label_list_visibility,
                'messageListVisibility': message_list_visibility,
            }

            created_label = (
                self.gmail_service.users()
                .labels()
                .create(userId='me', body=label_object)
                .execute()
            )

            return {
                "success": True,
                "label_id": created_label['id'],
                "label_name": created_label['name'],
                "message": "Label created successfully",
            }

        except Exception as e:
            logger.error("Failed to create label: %s", e)
            return {"error": f"Failed to create label: {e!s}"}

    def delete_label(self, label_id: str) -> Dict[str, Any]:
        r"""Delete a Gmail label.

        Args:
            label_id (str): The ID of the label to delete.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the
                operation.
        """
        try:
            self.gmail_service.users().labels().delete(
                userId='me', id=label_id
            ).execute()

            return {
                "success": True,
                "label_id": label_id,
                "message": "Label deleted successfully",
            }

        except Exception as e:
            logger.error("Failed to delete label: %s", e)
            return {"error": f"Failed to delete label: {e!s}"}

    def modify_thread_labels(
        self,
        thread_id: str,
        add_labels: Optional[List[str]] = None,
        remove_labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        r"""Modify labels on a thread.

        Args:
            thread_id (str): The ID of the thread to modify.
            add_labels (Optional[List[str]]): Labels to add.
            remove_labels (Optional[List[str]]): Labels to remove.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the
                operation.
        """
        try:
            body = {}
            if add_labels:
                body['addLabelIds'] = add_labels
            if remove_labels:
                body['removeLabelIds'] = remove_labels

            if not body:
                return {"error": "No labels to add or remove"}

            modified_thread = (
                self.gmail_service.users()
                .threads()
                .modify(userId='me', id=thread_id, body=body)
                .execute()
            )

            return {
                "success": True,
                "thread_id": thread_id,
                "label_ids": modified_thread.get('labelIds', []),
                "message": "Thread labels modified successfully",
            }

        except Exception as e:
            logger.error("Failed to modify thread labels: %s", e)
            return {"error": f"Failed to modify thread labels: {e!s}"}

    def get_profile(self) -> Dict[str, Any]:
        r"""Get Gmail profile information.

        Returns:
            Dict[str, Any]: A dictionary containing the profile information.
        """
        try:
            profile = (
                self.gmail_service.users().getProfile(userId='me').execute()
            )

            return {
                "success": True,
                "profile": {
                    "email_address": profile.get('emailAddress', ''),
                    "messages_total": profile.get('messagesTotal', 0),
                    "threads_total": profile.get('threadsTotal', 0),
                    "history_id": profile.get('historyId', ''),
                },
            }

        except Exception as e:
            logger.error("Failed to get profile: %s", e)
            return {"error": f"Failed to get profile: {e!s}"}

    def get_contacts(
        self,
        query: str = "",
        max_results: int = 100,
    ) -> Dict[str, Any]:
        r"""Get contacts from Google People API.

        Args:
            query (str): Search query for contacts.
            max_results (int): Maximum number of contacts to fetch.

        Returns:
            Dict[str, Any]: A dictionary containing the contacts.
        """
        try:
            # Build request parameters
            request_params = {
                'resourceName': 'people/me',
                'personFields': (
                    'names,emailAddresses,phoneNumbers,organizations'
                ),
                'pageSize': max_results,
            }

            if query:
                request_params['query'] = query

            # Search contacts
            contacts_result = (
                self.people_service.people()
                .connections()
                .list(**request_params)
                .execute()
            )

            connections = contacts_result.get('connections', [])
            contact_list = []

            for person in connections:
                contact_info = {
                    "resource_name": person.get('resourceName', ''),
                    "names": person.get('names', []),
                    "email_addresses": person.get('emailAddresses', []),
                    "phone_numbers": person.get('phoneNumbers', []),
                    "organizations": person.get('organizations', []),
                }
                contact_list.append(contact_info)

            return {
                "success": True,
                "contacts": contact_list,
                "total_count": len(contact_list),
                "next_page_token": contacts_result.get('nextPageToken'),
            }

        except Exception as e:
            logger.error("Failed to get contacts: %s", e)
            return {"error": f"Failed to get contacts: {e!s}"}

    def search_people(
        self,
        query: str,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        r"""Search for people in contacts.

        Args:
            query (str): Search query for people.
            max_results (int): Maximum number of results to fetch.

        Returns:
            Dict[str, Any]: A dictionary containing the search results.
        """
        try:
            # Search people
            search_result = (
                self.people_service.people()
                .searchContacts(
                    query=query,
                    readMask='names,emailAddresses,phoneNumbers,organizations',
                    pageSize=max_results,
                )
                .execute()
            )

            results = search_result.get('results', [])
            people_list = []

            for result in results:
                person = result.get('person', {})
                person_info = {
                    "resource_name": person.get('resourceName', ''),
                    "names": person.get('names', []),
                    "email_addresses": person.get('emailAddresses', []),
                    "phone_numbers": person.get('phoneNumbers', []),
                    "organizations": person.get('organizations', []),
                }
                people_list.append(person_info)

            return {
                "success": True,
                "people": people_list,
                "total_count": len(people_list),
            }

        except Exception as e:
            logger.error("Failed to search people: %s", e)
            return {"error": f"Failed to search people: {e!s}"}

    # Helper methods
    def _get_gmail_service(self):
        r"""Get Gmail service object."""
        from googleapiclient.discovery import build

        try:
            creds = self._authenticate()
            service = build('gmail', 'v1', credentials=creds)
            return service
        except Exception as e:
            raise ValueError(f"Failed to build Gmail service: {e}") from e

    def _get_people_service(self):
        r"""Get People service object."""
        from googleapiclient.discovery import build

        try:
            creds = self._authenticate()
            service = build('people', 'v1', credentials=creds)
            return service
        except Exception as e:
            raise ValueError(f"Failed to build People service: {e}") from e

    @api_keys_required(
        [
            (None, "GOOGLE_CLIENT_ID"),
            (None, "GOOGLE_CLIENT_SECRET"),
        ]
    )
    def _authenticate(self):
        r"""Authenticate with Google APIs."""
        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
        refresh_token = os.environ.get('GOOGLE_REFRESH_TOKEN')
        token_uri = os.environ.get(
            'GOOGLE_TOKEN_URI', 'https://oauth2.googleapis.com/token'
        )

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        # For first-time authentication
        if not refresh_token:
            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": token_uri,
                    "redirect_uris": ["http://localhost"],
                }
            }

            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)
            return creds
        else:
            # If we have a refresh token, use it to get credentials
            creds = Credentials(
                None,
                refresh_token=refresh_token,
                token_uri=token_uri,
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES,
            )

            # Refresh token if expired
            if creds.expired:
                creds.refresh(Request())

            return creds

    def _create_message(
        self,
        to_list: List[str],
        subject: str,
        body: str,
        cc_list: Optional[List[str]] = None,
        bcc_list: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        is_html: bool = False,
    ) -> Dict[str, str]:
        r"""Create a message object for sending."""
        message = MIMEMultipart()
        message['to'] = ', '.join(to_list)
        message['subject'] = subject

        if cc_list:
            message['cc'] = ', '.join(cc_list)
        if bcc_list:
            message['bcc'] = ', '.join(bcc_list)

        # Add body
        if is_html:
            message.attach(MIMEText(body, 'html'))
        else:
            message.attach(MIMEText(body, 'plain'))

        # Add attachments
        if attachments:
            for file_path in attachments:
                if os.path.isfile(file_path):
                    with open(file_path, "rb") as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= '
                            f'{os.path.basename(file_path)}',
                        )
                        message.attach(part)

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode(
            'utf-8'
        )
        return {'raw': raw_message}

    def _get_message_details(
        self, message_id: str
    ) -> Optional[Dict[str, Any]]:
        r"""Get detailed information about a message."""
        try:
            message = (
                self.gmail_service.users()
                .messages()
                .get(userId='me', id=message_id)
                .execute()
            )

            headers = message['payload'].get('headers', [])

            return {
                "message_id": message['id'],
                "thread_id": message['threadId'],
                "snippet": message.get('snippet', ''),
                "subject": self._get_header_value(headers, 'Subject'),
                "from": self._get_header_value(headers, 'From'),
                "to": self._get_header_value(headers, 'To'),
                "cc": self._get_header_value(headers, 'Cc'),
                "bcc": self._get_header_value(headers, 'Bcc'),
                "date": self._get_header_value(headers, 'Date'),
                "body": self._extract_message_body(message),
                "label_ids": message.get('labelIds', []),
                "size_estimate": message.get('sizeEstimate', 0),
            }
        except Exception as e:
            logger.error("Failed to get message details: %s", e)
            return None

    def _get_header_value(
        self, headers: List[Dict[str, str]], name: str
    ) -> str:
        r"""Get header value by name."""
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return ""

    def _extract_message_body(self, message: Dict[str, Any]) -> str:
        r"""Extract message body from message payload."""
        payload = message.get('payload', {})

        # Handle multipart messages
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8')
                elif part['mimeType'] == 'text/html':
                    data = part['body'].get('data', '')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8')
        else:
            # Handle single part messages
            if payload.get('mimeType') == 'text/plain':
                data = payload['body'].get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8')
            elif payload.get('mimeType') == 'text/html':
                data = payload['body'].get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data).decode('utf-8')

        return ""

    def _is_valid_email(self, email: str) -> bool:
        r"""Validate email address format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.send_email),
            FunctionTool(self.reply_to_email),
            FunctionTool(self.forward_email),
            FunctionTool(self.create_email_draft),
            FunctionTool(self.send_draft),
            FunctionTool(self.fetch_emails),
            FunctionTool(self.fetch_message_by_id),
            FunctionTool(self.fetch_thread_by_id),
            FunctionTool(self.modify_email_labels),
            FunctionTool(self.move_to_trash),
            FunctionTool(self.get_attachment),
            FunctionTool(self.list_threads),
            FunctionTool(self.list_drafts),
            FunctionTool(self.list_gmail_labels),
            FunctionTool(self.create_label),
            FunctionTool(self.delete_label),
            FunctionTool(self.modify_thread_labels),
            FunctionTool(self.get_profile),
            FunctionTool(self.get_contacts),
            FunctionTool(self.search_people),
        ]
