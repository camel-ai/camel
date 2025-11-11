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
import re
from typing import Any, Dict, List, Literal, Optional, Union

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer

logger = get_logger(__name__)

SCOPES = [
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
    API keys can be accessed in google cloud console (https://console.cloud.google.com/)
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

        self._credentials = self._authenticate()

        self.gmail_service: Any = self._get_gmail_service()
        self._people_service: Any = None

    @property
    def people_service(self) -> Any:
        r"""Lazily initialize and return the Google People service."""
        if self._people_service is None:
            self._people_service = self._get_people_service()
        return self._people_service

    @people_service.setter
    def people_service(self, service: Any) -> None:
        r"""Allow overriding/injecting the People service (e.g., in tests)."""
        self._people_service = service

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
            is_html (bool): Whether the body is HTML format. Set to True when
                sending formatted emails with HTML tags (e.g., bold,
                links, images). Use False (default) for plain text emails.

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
            message_id (str): The unique identifier of the message to reply to.
                To get a message ID, first use fetch_emails() to list messages,
                or use the 'message_id' returned from send_email() or
                create_email_draft().
            reply_body (str): The reply message body.
            reply_all (bool): Whether to reply to all recipients.
            is_html (bool): Whether the body is HTML format. Set to True when
                sending formatted emails with HTML tags (e.g., bold,
                links, images). Use False (default) for plain text emails.

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

            # Extract headers (single pass, case-insensitive)
            headers = original_message['payload'].get('headers', [])
            subject = from_email = to_emails = cc_emails = None
            missing = {'subject', 'from', 'to', 'cc'}

            for header in headers:
                name = (header.get('name') or '').lower()
                if name not in missing:
                    continue
                value = header.get('value')
                if name == 'subject':
                    subject = value
                elif name == 'from':
                    from_email = value
                elif name == 'to':
                    to_emails = value
                elif name == 'cc':
                    cc_emails = value
                missing.discard(name)
                if not missing:
                    break

            # Extract identifiers for reply context
            message_id_header = self._get_header_value(
                headers, 'Message-Id'
            ) or self._get_header_value(headers, 'Message-ID')
            thread_id = original_message.get('threadId')

            # Prepare reply subject
            if subject and not subject.startswith('Re: '):
                subject = f"Re: {subject}"
            elif not subject:
                subject = "Re: (No Subject)"

            # Validate from_email
            if not from_email:
                return {"error": "Original message has no sender address"}

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
                # Remove duplicates and None values
                recipients = [r for r in list(set(recipients)) if r]

                # Get current user's email and remove it from recipients
                try:
                    profile_result = self.get_profile()
                    if profile_result.get('success'):
                        current_user_email = profile_result['profile'][
                            'email_address'
                        ]
                        # Remove current user from recipients (handle both
                        # plain email and "Name <email>" format)
                        filtered_recipients = []
                        for email in recipients:
                            # Extract email from "Name <email>" format
                            match = re.search(r'<([^>]+)>$', email.strip())
                            email_addr = (
                                match.group(1) if match else email.strip()
                            )
                            if email_addr != current_user_email:
                                filtered_recipients.append(email)
                        recipients = filtered_recipients
                except Exception as e:
                    logger.warning(
                        "Could not get current user email to filter from "
                        "recipients: %s",
                        e,
                    )
            else:
                recipients = [from_email]

            # Create reply message with reply headers
            message = self._create_message(
                recipients,
                subject,
                reply_body,
                is_html=is_html,
                in_reply_to=message_id_header or original_message.get('id'),
                references=[message_id_header] if message_id_header else None,
            )

            # Send reply in the same thread
            sent_message = (
                self.gmail_service.users()
                .messages()
                .send(userId='me', body={**message, 'threadId': thread_id})
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
        include_attachments: bool = True,
    ) -> Dict[str, Any]:
        r"""Forward an email message.

        Args:
            message_id (str): The unique identifier of the message to forward.
                To get a message ID, first use fetch_emails() to list messages,
                or use the 'message_id' returned from send_email() or
                create_email_draft().
            to (Union[str, List[str]]): Recipient email address(es).
                forward_body (Optional[str]): Additional message to include at
                the top of the forwarded email, before the original message
                content. If not provided, only the original message will be
                forwarded.
            cc (Optional[Union[str, List[str]]]): CC recipient email
                address(es).
            bcc (Optional[Union[str, List[str]]]): BCC recipient email
                address(es).
            include_attachments (bool): Whether to include original
                attachments. Defaults to True. Only includes real
                attachments, not inline images.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the
                operation, including the number of attachments forwarded.
        """
        try:
            import tempfile

            # Get the original message
            original_message = (
                self.gmail_service.users()
                .messages()
                .get(userId='me', id=message_id)
                .execute()
            )

            # Extract headers (single pass, case-insensitive)
            headers = original_message['payload'].get('headers', [])
            subject = from_email = date = None
            missing = {'subject', 'from', 'date'}

            for header in headers:
                name = (header.get('name') or '').lower()
                if name not in missing:
                    continue
                value = header.get('value')
                if name == 'subject':
                    subject = value
                elif name == 'from':
                    from_email = value
                elif name == 'date':
                    date = value
                missing.discard(name)
                if not missing:
                    break

            # Prepare forward subject
            if subject and not subject.startswith('Fwd: '):
                subject = f"Fwd: {subject}"
            elif not subject:
                subject = "Fwd: (No Subject)"

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

            # Handle attachments
            attachment_paths = []
            temp_files: List[str] = []

            try:
                if include_attachments:
                    # Extract attachment metadata
                    attachments = self._extract_attachments(original_message)
                    for att in attachments:
                        try:
                            # Create temp file
                            temp_file = tempfile.NamedTemporaryFile(
                                delete=False, suffix=f"_{att['filename']}"
                            )
                            temp_files.append(temp_file.name)

                            # Download attachment
                            result = self.get_attachment(
                                message_id=message_id,
                                attachment_id=att['attachment_id'],
                                save_path=temp_file.name,
                            )

                            if result.get('success'):
                                attachment_paths.append(temp_file.name)

                        except Exception as e:
                            logger.warning(
                                f"Failed to download attachment "
                                f"{att['filename']}: {e}"
                            )

                # Create forward message (now with attachments!)
                message = self._create_message(
                    to_list,
                    subject,
                    body,
                    cc_list,
                    bcc_list,
                    attachments=attachment_paths if attachment_paths else None,
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
                    "attachments_forwarded": len(attachment_paths),
                }

            finally:
                # Clean up temp files
                for temp_file_path in temp_files:
                    try:
                        os.unlink(temp_file_path)
                    except Exception as e:
                        logger.warning(
                            f"Failed to delete temp file {temp_file_path}: {e}"
                        )

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
            is_html (bool): Whether the body is HTML format. Set to True when
                sending formatted emails with HTML tags (e.g., bold,
                links, images). Use False (default) for plain text emails.

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
            draft_id (str): The unique identifier of the draft to send.
                To get a draft ID, first use list_drafts() to list drafts,
                or use the 'draft_id' returned from create_email_draft().

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
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Fetch emails with filters and pagination.

        Args:
            query (str): Gmail search query string. Use Gmail's search syntax:
                - 'from:example@domain.com' - emails from specific sender
                - 'subject:meeting' - emails with specific subject text
                - 'has:attachment' - emails with attachments
                - 'is:unread' - unread emails
                - 'in:sent' - emails in sent folder
                - 'after:2024/01/01 before:2024/12/31' - date range
                Examples: 'from:john@example.com subject:project', 'is:unread
                has:attachment'
            max_results (int): Maximum number of emails to fetch.
            include_spam_trash (bool): Whether to include spam and trash.
            label_ids (Optional[List[str]]): List of label IDs to filter
                emails by. Only emails with ALL of the specified
                labels will be returned.
                Label IDs can be:
                - System labels: 'INBOX', 'SENT', 'DRAFT', 'SPAM', 'TRASH',
                  'UNREAD', 'STARRED', 'IMPORTANT', 'CATEGORY_PERSONAL', etc.
                - Custom label IDs: Retrieved from list_gmail_labels() method.
            page_token (Optional[str]): Pagination token from a previous
                response. If provided, fetches the next page of results.

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
            if page_token:
                request_params['pageToken'] = page_token

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

    def fetch_thread_by_id(self, thread_id: str) -> Dict[str, Any]:
        r"""Fetch a thread by ID.

        Args:
            thread_id (str): The unique identifier of the thread to fetch.
                To get a thread ID, first use list_threads() to list threads,
                or use the 'thread_id' returned from send_email() or
                reply_to_email().

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
            message_id (str): The unique identifier of the message to modify.
                To get a message ID, first use fetch_emails() to list messages,
                or use the 'message_id' returned from send_email() or
                create_email_draft().
            add_labels (Optional[List[str]]): List of label IDs to add to
                the message.
                Label IDs can be:
                - System labels: 'INBOX', 'STARRED', 'IMPORTANT',
                    'UNREAD', etc.
                - Custom label IDs: Retrieved from list_gmail_labels() method.
                    Example: ['STARRED', 'IMPORTANT'] marks email as starred
                    and important.
            remove_labels (Optional[List[str]]): List of label IDs to
                remove from the message. Uses the same format as add_labels.
                Example: ['UNREAD'] marks the email as read.

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
            message_id (str): The unique identifier of the message to move to
                trash. To get a message ID, first use fetch_emails() to list
                messages, or use the 'message_id' returned from send_email()
                or create_email_draft().

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
            message_id (str): The unique identifier of the message containing
                the attachment. To get a message ID, first use fetch_emails()
                to list messages, or use the 'message_id' returned from
                send_email() or create_email_draft().
            attachment_id (str): The unique identifier of the attachment to
                download. To get an attachment ID, first use fetch_emails() to
                get message details, then look for 'attachment_id' in the
                'attachments' list of each message.
            save_path (Optional[str]): Local file path where the attachment
                should be saved. If provided, the attachment will be saved to
                this location and the response will include a success message.
                If not provided, the attachment data will be returned as
                base64-encoded content in the response.

        Returns:
            Dict[str, Any]: A dictionary containing the attachment data or
                save result.
        """
        try:
            import base64

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
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""List email threads.

        Args:
            query (str): Gmail search query string. Use Gmail's search syntax:
                - 'from:example@domain.com' - threads from specific sender
                - 'subject:meeting' - threads with specific subject text
                - 'has:attachment' - threads with attachments
                - 'is:unread' - unread threads
                - 'in:sent' - threads in sent folder
                - 'after:2024/01/01 before:2024/12/31' - date range
                Examples: 'from:john@example.com subject:project', 'is:unread
                has:attachment'
            max_results (int): Maximum number of threads to fetch.
            include_spam_trash (bool): Whether to include spam and trash.
            label_ids (Optional[List[str]]): List of label IDs to filter
                threads by. Only threads with ALL of the specified labels
                will be returned.
                Label IDs can be:
                - System labels: 'INBOX', 'SENT', 'DRAFT', 'SPAM', 'TRASH',
                  'UNREAD', 'STARRED', 'IMPORTANT', 'CATEGORY_PERSONAL', etc.
                - Custom label IDs: Retrieved from list_gmail_labels() method.
            page_token (Optional[str]): Pagination token from a previous
                response. If provided, fetches the next page of results.

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
            if page_token:
                request_params['pageToken'] = page_token

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

    def list_drafts(
        self, max_results: int = 10, page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        r"""List email drafts.

        Args:
            max_results (int): Maximum number of drafts to fetch.
            page_token (Optional[str]): Pagination token from a previous
                response. If provided, fetches the next page of results.

        Returns:
            Dict[str, Any]: A dictionary containing the draft list.
        """
        try:
            drafts_result = (
                self.gmail_service.users()
                .drafts()
                .list(
                    userId='me',
                    maxResults=max_results,
                    **({"pageToken": page_token} if page_token else {}),
                )
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
        label_list_visibility: Literal["labelShow", "labelHide"] = "labelShow",
        message_list_visibility: Literal["show", "hide"] = "show",
    ) -> Dict[str, Any]:
        r"""Create a new Gmail label.

        Args:
            name (str): The name of the label to create.
            label_list_visibility (str): How the label appears in Gmail's
                label list. - 'labelShow': Label is visible in the label list
                sidebar (default) - 'labelHide': Label is hidden from the
                label list sidebar
            message_list_visibility (str): How the label appears in message
                lists. - 'show': Label is visible on messages in inbox/lists
                (default) - 'hide': Label is hidden from message displays

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
            label_id (str): The unique identifier of the user-created label to
                delete. To get a label ID, first use list_gmail_labels() to
                list all labels. Note: System labels (e.g., 'INBOX', 'SENT',
                'DRAFT', 'SPAM', 'TRASH', 'UNREAD', 'STARRED', 'IMPORTANT',
                'CATEGORY_PERSONAL', etc.) cannot be deleted.

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
            thread_id (str): The unique identifier of the thread to modify.
                To get a thread ID, first use list_threads() to list threads,
                or use the 'thread_id' returned from send_email() or
                reply_to_email().
            add_labels (Optional[List[str]]): List of label IDs to add to all
                messages in the thread.
                Label IDs can be:
                - System labels: 'INBOX', 'STARRED', 'IMPORTANT',
                  'UNREAD', etc.
                - Custom label IDs: Retrieved from list_gmail_labels().
                Example: ['STARRED', 'IMPORTANT'] marks thread as
                starred and important.
            remove_labels (Optional[List[str]]): List of label IDs to
                remove from all messages in the thread. Uses the same
                format as add_labels.
                Example: ['UNREAD'] marks the entire thread as read.

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
        max_results: int = 100,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""List connections from Google People API.

        Args:
            max_results (int): Maximum number of contacts to fetch.
            page_token (Optional[str]): Pagination token from a previous
                response. If provided, fetches the next page of results.

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

            # Search contacts
            if page_token:
                request_params['pageToken'] = page_token

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
            query (str): Search query for people in contacts. Can search by:
                - Name: 'John Smith' or partial names like 'John'
                - Email: 'john@example.com'
                - Organization: 'Google' or 'Acme Corp'
                - Phone number: '+1234567890'
                Examples: 'John Smith', 'john@example.com', 'Google'
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
            # Build service with optional timeout
            if self.timeout is not None:
                import httplib2

                http = httplib2.Http(timeout=self.timeout)
                http = self._credentials.authorize(http)
                service = build('gmail', 'v1', http=http)
            else:
                service = build('gmail', 'v1', credentials=self._credentials)
            return service
        except Exception as e:
            raise ValueError(f"Failed to build Gmail service: {e}") from e

    def _get_people_service(self):
        r"""Get People service object."""
        from googleapiclient.discovery import build

        try:
            # Build service with optional timeout
            if self.timeout is not None:
                import httplib2

                http = httplib2.Http(timeout=self.timeout)
                http = self._credentials.authorize(http)
                service = build('people', 'v1', http=http)
            else:
                service = build('people', 'v1', credentials=self._credentials)
            return service
        except Exception as e:
            raise ValueError(f"Failed to build People service: {e}") from e

    def _authenticate(self):
        r"""Authenticate with Google APIs using OAuth2.

        Automatically saves and loads credentials from
        ~/.camel/gmail_token.json to avoid repeated
        browser logins.
        """
        import json
        from pathlib import Path

        from dotenv import load_dotenv
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        # Look for .env file in the project root (camel/)
        env_file = Path(__file__).parent.parent.parent / '.env'
        load_dotenv(env_file)

        client_id = os.environ.get('GOOGLE_CLIENT_ID')
        client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')

        if not client_id or not client_secret:
            missing_vars = []
            if not client_id:
                missing_vars.append('GOOGLE_CLIENT_ID')
            if not client_secret:
                missing_vars.append('GOOGLE_CLIENT_SECRET')
            raise ValueError(
                f"Missing required environment variables: "
                f"{', '.join(missing_vars)}. "
                "Please set these in your .env file or environment variables."
            )

        token_file = Path.home() / '.camel' / 'gmail_token.json'
        creds = None

        # COMPONENT 1: Load saved credentials
        if token_file.exists():
            try:
                with open(token_file, 'r') as f:
                    data = json.load(f)
                creds = Credentials(
                    token=data.get('token'),
                    refresh_token=data.get('refresh_token'),
                    token_uri=data.get(
                        'token_uri', 'https://oauth2.googleapis.com/token'
                    ),
                    client_id=client_id,
                    client_secret=client_secret,
                    scopes=SCOPES,
                )
            except Exception as e:
                logger.warning(f"Failed to load saved token: {e}")
                creds = None

        # COMPONENT 2: Refresh if expired
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Access token refreshed")

                # Save refreshed credentials to disk
                token_file.parent.mkdir(parents=True, exist_ok=True)
                try:
                    with open(token_file, 'w') as f:
                        json.dump(
                            {
                                'token': creds.token,
                                'refresh_token': creds.refresh_token,
                                'token_uri': creds.token_uri,
                                'scopes': creds.scopes,
                            },
                            f,
                        )
                    os.chmod(token_file, 0o600)
                    logger.info(f"Refreshed credentials saved to {token_file}")
                except Exception as e:
                    logger.warning(
                        f"Failed to save refreshed credentials to "
                        f"{token_file}: {e}. "
                        "Token refreshed but not persisted."
                    )

                return creds
            except Exception as e:
                logger.warning(f"Token refresh failed: {e}")
                creds = None

        # COMPONENT 3: Return if valid
        if creds and creds.valid:
            return creds

        # COMPONENT 4: Browser OAuth (first-time or invalid credentials)
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"],
            }
        }

        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        creds = flow.run_local_server(port=0)

        # Save new credentials
        token_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(token_file, 'w') as f:
                json.dump(
                    {
                        'token': creds.token,
                        'refresh_token': creds.refresh_token,
                        'token_uri': creds.token_uri,
                        'scopes': creds.scopes,
                    },
                    f,
                )
            os.chmod(token_file, 0o600)
            logger.info(f"Credentials saved to {token_file}")
        except Exception as e:
            logger.warning(
                f"Failed to save credentials to {token_file}: {e}. "
                "You may need to re-authenticate next time."
            )

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
        in_reply_to: Optional[str] = None,
        references: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        r"""Create a message object for sending."""

        import base64
        from email import encoders
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        message = MIMEMultipart()
        message['to'] = ', '.join(to_list)
        message['subject'] = subject

        if cc_list:
            message['cc'] = ', '.join(cc_list)
        if bcc_list:
            message['bcc'] = ', '.join(bcc_list)

        # Set reply headers when provided
        if in_reply_to:
            message['In-Reply-To'] = in_reply_to
        if references:
            message['References'] = ' '.join(references)

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
            # Build a name->value map in one pass (case-insensitive)
            header_map = {}
            for header in headers:
                name = header.get('name')
                if name:
                    header_map[name.lower()] = header.get('value', '')

            return {
                "message_id": message['id'],
                "thread_id": message['threadId'],
                "snippet": message.get('snippet', ''),
                "subject": header_map.get('subject', ''),
                "from": header_map.get('from', ''),
                "to": header_map.get('to', ''),
                "cc": header_map.get('cc', ''),
                "bcc": header_map.get('bcc', ''),
                "date": header_map.get('date', ''),
                "body": self._extract_message_body(message),
                "attachments": self._extract_attachments(
                    message, include_inline=True
                ),
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
        r"""Extract message body from message payload.

        Recursively traverses the entire message tree and collects all text
        content from text/plain and text/html parts. Special handling for
        multipart/alternative containers: recursively searches for one format
        (preferring plain text) to avoid duplication when both formats contain
        the same content. All other text parts are collected to ensure no
        information is lost.

        Args:
            message (Dict[str, Any]): The Gmail message dictionary containing
                the payload to extract text from.

        Returns:
            str: The extracted message body text with multiple parts separated
                by double newlines, or an empty string if no text content is
                found.
        """
        import base64
        import re

        text_parts = []

        def decode_text_data(data: str, mime_type: str) -> Optional[str]:
            """Helper to decode base64 text data.

            Args:
                data: Base64 encoded text data.
                mime_type: MIME type for logging purposes.

            Returns:
                Decoded text string, or None if decoding fails or text
                is empty.
            """
            if not data:
                return None
            try:
                text = base64.urlsafe_b64decode(data).decode('utf-8')
                return text if text.strip() else None
            except Exception as e:
                logger.warning(f"Failed to decode {mime_type}: {e}")
                return None

        def strip_html_tags(html_content: str) -> str:
            """Strip HTML tags and convert to readable plain text.

            Uses regex to remove tags and clean up formatting while preserving
            basic document structure.

            Args:
                html_content: HTML content to strip.

            Returns:
                Plain text version of HTML content.
            """
            if not html_content or not html_content.strip():
                return ""

            text = html_content

            # Remove script and style elements completely
            text = re.sub(
                r'<script[^>]*>.*?</script>',
                '',
                text,
                flags=re.DOTALL | re.IGNORECASE,
            )
            text = re.sub(
                r'<style[^>]*>.*?</style>',
                '',
                text,
                flags=re.DOTALL | re.IGNORECASE,
            )

            # Convert common HTML entities
            text = text.replace('&nbsp;', ' ')
            text = text.replace('&amp;', '&')
            text = text.replace('&lt;', '<')
            text = text.replace('&gt;', '>')
            text = text.replace('&quot;', '"')
            text = text.replace('&#39;', "'")
            text = text.replace('&rsquo;', "'")
            text = text.replace('&lsquo;', "'")
            text = text.replace('&rdquo;', '"')
            text = text.replace('&ldquo;', '"')
            text = text.replace('&mdash;', '—')
            text = text.replace('&ndash;', '-')

            # Convert <br> and <br/> to newlines
            text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)

            # Convert block-level closing tags to newlines
            text = re.sub(
                r'</(p|div|h[1-6]|tr|li)>', '\n', text, flags=re.IGNORECASE
            )

            # Convert <hr> to separator
            text = re.sub(r'<hr\s*/?>', '\n---\n', text, flags=re.IGNORECASE)

            # Remove all remaining HTML tags
            text = re.sub(r'<[^>]+>', '', text)

            # Clean up whitespace
            text = re.sub(
                r'\n\s*\n\s*\n+', '\n\n', text
            )  # Multiple blank lines to double newline
            text = re.sub(r' +', ' ', text)  # Multiple spaces to single space
            text = re.sub(r'\n ', '\n', text)  # Remove leading spaces on lines
            text = re.sub(
                r' \n', '\n', text
            )  # Remove trailing spaces on lines

            return text.strip()

        def find_text_recursive(
            part: Dict[str, Any], target_mime: str
        ) -> Optional[str]:
            """Recursively search for text content of a specific MIME type.

            Args:
                part: Message part to search in.
                target_mime: Target MIME type ('text/plain' or 'text/html').

            Returns:
                Decoded text string if found, None otherwise.
            """
            mime = part.get('mimeType', '')

            # Found the target type at this level
            if mime == target_mime:
                data = part.get('body', {}).get('data', '')
                decoded = decode_text_data(data, target_mime)
                # Strip HTML tags if this is HTML content
                if decoded and target_mime == 'text/html':
                    return strip_html_tags(decoded)
                return decoded

            # Not found, but has nested parts? Search recursively
            if 'parts' in part:
                for nested_part in part['parts']:
                    result = find_text_recursive(nested_part, target_mime)
                    if result:
                        return result

            return None

        def extract_from_part(part: Dict[str, Any]):
            """Recursively collect all text from message parts."""
            mime_type = part.get('mimeType', '')

            # Special handling for multipart/alternative
            if mime_type == 'multipart/alternative' and 'parts' in part:
                # Recursively search for one format (prefer plain text)
                plain_text = None
                html_text = None

                # Search each alternative branch recursively
                for nested_part in part['parts']:
                    if not plain_text:
                        plain_text = find_text_recursive(
                            nested_part, 'text/plain'
                        )
                    if not html_text:
                        html_text = find_text_recursive(
                            nested_part, 'text/html'
                        )

                # Prefer plain text, fall back to HTML
                chosen_text = plain_text if plain_text else html_text
                if chosen_text:
                    text_parts.append(chosen_text)

            # If this part has nested parts (but not multipart/alternative)
            elif 'parts' in part:
                for nested_part in part['parts']:
                    extract_from_part(nested_part)

            # If this is a text leaf, extract and collect it
            elif mime_type == 'text/plain':
                data = part.get('body', {}).get('data', '')
                text = decode_text_data(data, 'plain text body')
                if text:
                    text_parts.append(text)

            elif mime_type == 'text/html':
                data = part.get('body', {}).get('data', '')
                html_text = decode_text_data(data, 'HTML body')
                if html_text:
                    text = strip_html_tags(html_text)
                    if text:
                        text_parts.append(text)

        # Traverse the entire tree and collect all text parts
        payload = message.get('payload', {})
        extract_from_part(payload)

        if not text_parts:
            return ""

        # Return all text parts combined
        return '\n\n'.join(text_parts)

    def _extract_attachments(
        self, message: Dict[str, Any], include_inline: bool = False
    ) -> List[Dict[str, Any]]:
        r"""Extract attachment information from message payload.

        Recursively traverses the message tree to find all attachments
        and extracts their metadata. Distinguishes between regular attachments
        and inline images embedded in HTML content.

        Args:
            message (Dict[str, Any]): The Gmail message dictionary containing
                the payload to extract attachments from.

        Returns:
            List[Dict[str, Any]]: List of attachment dictionaries, each
                containing:
                - attachment_id: Gmail's unique identifier for the attachment
                - filename: Name of the attached file
                - mime_type: MIME type of the attachment
                - size: Size of the attachment in bytes
                - is_inline: Whether this is an inline image (embedded in HTML)
        """
        attachments = []

        def is_inline_image(part: Dict[str, Any]) -> bool:
            """Check if this part is an inline image."""
            headers = part.get('headers', [])
            for header in headers:
                name = header.get('name', '').lower()
                value = header.get('value', '').lower()
                # Check for Content-Disposition: inline
                if name == 'content-disposition' and 'inline' in value:
                    return True
                # Check for Content-ID (usually indicates inline)
                if name == 'content-id':
                    return True
            return False

        def find_attachments(part: Dict[str, Any]):
            """Recursively find attachments in message parts."""
            # Check if this part has an attachmentId (indicates it's an
            # attachment)
            if 'body' in part and 'attachmentId' in part['body']:
                attachment_info = {
                    'attachment_id': part['body']['attachmentId'],
                    'filename': part.get('filename', 'unnamed'),
                    'mime_type': part.get(
                        'mimeType', 'application/octet-stream'
                    ),
                    'size': part['body'].get('size', 0),
                    'is_inline': is_inline_image(part),
                }
                attachments.append(attachment_info)

            # Recurse into nested parts
            if 'parts' in part:
                for nested_part in part['parts']:
                    find_attachments(nested_part)

        # Start traversal from the message payload
        payload = message.get('payload', {})
        if payload:
            find_attachments(payload)

        # Return based on include_inline toggle
        if include_inline:
            return attachments
        return [att for att in attachments if not att['is_inline']]

    def _is_valid_email(self, email: str) -> bool:
        r"""Validate email address format.

        Supports both formats:
        - Plain email: john@example.com
        - Named email: John Doe <john@example.com>
        """
        # Extract email from "Name <email>" format if present
        match = re.search(r'<([^>]+)>$', email.strip())
        email_to_check = match.group(1) if match else email.strip()

        # Validate the email address
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email_to_check) is not None

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
