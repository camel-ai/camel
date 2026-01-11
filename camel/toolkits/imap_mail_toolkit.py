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

import email
import imaplib
import os
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, dependencies_required

logger = get_logger(__name__)


# Type aliases for mail operations
class IMAP_RETURN_STATUS(Enum):
    r"""IMAP operation return status codes."""

    OK = "OK"
    NO = "NO"  # according to imap source code


@MCPServer()
class IMAPMailToolkit(BaseToolkit):
    r"""A toolkit for IMAP email operations.

    This toolkit provides comprehensive email functionality including:
    - Fetching emails with filtering options
    - Retrieving specific emails by ID
    - Sending emails via SMTP
    - Replying to emails
    - Moving emails to folders
    - Deleting emails

    The toolkit implements connection pooling with automatic idle timeout
    to prevent resource leaks when used by LLM agents.

    Args:
        imap_server (str, optional): IMAP server hostname. If not provided,
            will be obtained from environment variables.
        imap_port (int, optional): IMAP server port. Defaults to 993.
        smtp_server (str, optional): SMTP server hostname. If not provided,
            will be obtained from environment variables.
        smtp_port (int, optional): SMTP server port. Defaults to 587.
        username (str, optional): Email username. If not provided, will be
            obtained from environment variables.
        password (str, optional): Email password. If not provided, will be
            obtained from environment variables.
        timeout (Optional[float]): The timeout for the toolkit operations.
        connection_idle_timeout (float): Maximum idle time (in seconds)
            before auto-closing connections. Defaults to 300 (5 minutes).
    """

    @dependencies_required('imaplib', 'smtplib', 'email')
    def __init__(
        self,
        imap_server: Optional[str] = None,
        imap_port: int = 993,
        smtp_server: Optional[str] = None,
        smtp_port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: Optional[float] = None,
        connection_idle_timeout: float = 300.0,
    ) -> None:
        r"""Initialize the IMAP Mail Toolkit.

        Args:
            imap_server: IMAP server hostname (default: :obj:`None`)
            imap_port: IMAP server port (default: :obj:`993`)
            smtp_server: SMTP server hostname (default: :obj:`None`)
            smtp_port: SMTP server port (default: :obj:`587`)
            username: Email username (default: :obj:`None`)
            password: Email password (default: :obj:`None`)
            timeout: Timeout for operations (default: :obj:`None`)
            connection_idle_timeout: Max idle time before auto-close (default:
            :obj:`300` seconds)
        """
        super().__init__(timeout=timeout)

        # Get credentials from environment if not provided
        self.imap_server = imap_server or os.environ.get("IMAP_SERVER")
        self.imap_port = imap_port
        self.smtp_server = smtp_server or os.environ.get("SMTP_SERVER")
        self.smtp_port = smtp_port
        self.username = username or os.environ.get("EMAIL_USERNAME")
        self.password = password or os.environ.get("EMAIL_PASSWORD")

        # Persistent connections
        self._imap_connection: Optional[imaplib.IMAP4_SSL] = None
        self._smtp_connection: Optional[smtplib.SMTP] = None

        # Connection idle timeout management
        self._connection_idle_timeout = connection_idle_timeout
        self._imap_last_used: float = 0.0
        self._smtp_last_used: float = 0.0

    def _get_imap_connection(self) -> imaplib.IMAP4_SSL:
        r"""Establish or reuse IMAP connection with idle timeout.

        Returns:
            imaplib.IMAP4_SSL: Connected IMAP client
        """
        if not self.imap_server or not self.username or not self.password:
            raise ValueError(
                "IMAP server, username, and password must be provided"
            )

        current_time = time.time()

        # Check if existing connection has exceeded idle timeout
        if self._imap_connection is not None:
            idle_time = current_time - self._imap_last_used
            if idle_time > self._connection_idle_timeout:
                logger.info(
                    "IMAP connection idle for %.1f seconds, closing",
                    idle_time,
                )
                try:
                    self._imap_connection.logout()
                except (imaplib.IMAP4.error, OSError) as e:
                    logger.debug("Error closing idle IMAP connection: %s", e)
                self._imap_connection = None

        # Check if existing connection is still alive
        if self._imap_connection is not None:
            try:
                # Test connection with NOOP command
                self._imap_connection.noop()
                logger.debug("Reusing existing IMAP connection")
                self._imap_last_used = current_time
                return self._imap_connection
            except (imaplib.IMAP4.error, OSError):
                # Connection is dead, close it and create new one
                logger.debug("IMAP connection is dead, creating new one")
                try:
                    self._imap_connection.logout()
                except (imaplib.IMAP4.error, OSError) as e:
                    logger.debug("Error closing dead IMAP connection: %s", e)
                self._imap_connection = None

        # Create new connection
        try:
            imap = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            imap.login(self.username, self.password)
            self._imap_connection = imap
            self._imap_last_used = current_time
            logger.info(
                "Successfully connected to IMAP server %s", self.imap_server
            )
            return self._imap_connection
        except Exception as e:
            logger.error("Failed to connect to IMAP server: %s", e)
            raise

    def _get_smtp_connection(self) -> smtplib.SMTP:
        r"""Establish or reuse SMTP connection with idle timeout.

        Returns:
            smtplib.SMTP: Connected SMTP client
        """
        if not self.smtp_server or not self.username or not self.password:
            raise ValueError(
                "SMTP server, username, and password must be provided"
            )

        current_time = time.time()

        # Check if existing connection has exceeded idle timeout
        if self._smtp_connection is not None:
            idle_time = current_time - self._smtp_last_used
            if idle_time > self._connection_idle_timeout:
                logger.info(
                    "SMTP connection idle for %.1f seconds, closing",
                    idle_time,
                )
                try:
                    self._smtp_connection.quit()
                except (smtplib.SMTPException, OSError) as e:
                    logger.debug("Error closing idle SMTP connection: %s", e)
                self._smtp_connection = None

        # Check if existing connection is still alive
        if self._smtp_connection is not None:
            try:
                # Test connection with NOOP command
                status = self._smtp_connection.noop()
                if status[0] == 250:
                    logger.debug("Reusing existing SMTP connection")
                    self._smtp_last_used = current_time
                    return self._smtp_connection
            except (smtplib.SMTPException, OSError):
                # Connection is dead, close it and create new one
                logger.debug("SMTP connection is dead, creating new one")
                try:
                    self._smtp_connection.quit()
                except (smtplib.SMTPException, OSError) as e:
                    logger.debug("Error closing dead SMTP connection: %s", e)
                self._smtp_connection = None

        # Create new connection
        try:
            smtp = smtplib.SMTP(self.smtp_server, self.smtp_port)
            smtp.starttls()
            smtp.login(self.username, self.password)
            self._smtp_connection = smtp
            self._smtp_last_used = current_time
            logger.info(
                "Successfully connected to SMTP server %s", self.smtp_server
            )
            return self._smtp_connection
        except Exception as e:
            logger.error("Failed to connect to SMTP server: %s", e)
            raise

    def _ensure_imap_ok(self, status: str, action: str) -> None:
        r"""Ensure IMAP status is OK, otherwise raise a ConnectionError."""
        if status != IMAP_RETURN_STATUS.OK.value:
            raise ConnectionError(f"IMAP {action} failed with status {status}")

    def fetch_emails(
        self,
        folder: Literal["INBOX"] = "INBOX",
        limit: int = 10,
        unread_only: bool = False,
        sender_filter: Optional[str] = None,
        subject_filter: Optional[str] = None,
    ) -> List[Dict]:
        r"""Fetch emails from a folder with optional filtering.

        Args:
            folder (Literal["INBOX"]): Email folder to search in
                (default: :obj:`"INBOX"`)
            limit (int): Maximum number of emails to retrieve
                (default: :obj:`10`)
            unread_only (bool): If True, only fetch unread
                emails (default: :obj:`False`)
            sender_filter (str, optional): Filter emails by
                sender email address (default: :obj:`None`)
            subject_filter (str, optional): Filter emails by subject content
                (default: :obj:`None`)

        Returns:
            List[Dict]: List of email dictionaries with metadata
        """
        try:
            imap = self._get_imap_connection()
            imap.select(folder, readonly=True)

            # Build search criteria
            search_criteria = []
            if unread_only:
                search_criteria.append("UNSEEN")
            if sender_filter:
                search_criteria.append(f'FROM "{sender_filter}"')
            if subject_filter:
                search_criteria.append(f'SUBJECT "{subject_filter}"')

            # If no specific criteria, get recent emails
            if not search_criteria:
                search_criteria.append("ALL")

            search_string = " ".join(search_criteria)
            status, messages = imap.search(None, search_string)

            if status != IMAP_RETURN_STATUS.OK.value:
                raise ConnectionError("Failed to search emails")

            email_ids = messages[0].split()

            # Limit results
            if len(email_ids) > limit:
                email_ids = email_ids[-limit:]  # Get most recent emails

            emails: List[Dict[str, Any]] = []
            for email_id in email_ids:
                try:
                    status, msg_data = imap.fetch(email_id, "(BODY.PEEK[])")
                    if (
                        status == IMAP_RETURN_STATUS.OK.value
                        and msg_data
                        and len(msg_data) > 0
                    ):
                        # msg_data is a list of tuples, get the first one
                        msg_tuple = msg_data[0]
                        if (
                            isinstance(msg_tuple, tuple)
                            and len(msg_tuple) >= 2
                        ):
                            email_body = msg_tuple[1]
                            # Handle different email body formats
                            if isinstance(email_body, bytes):
                                email_message = email.message_from_bytes(
                                    email_body
                                )
                                email_size = len(email_body)
                            elif isinstance(email_body, str):
                                email_message = email.message_from_string(
                                    email_body
                                )
                                email_size = len(email_body.encode('utf-8'))
                            else:
                                logger.warning(
                                    "Email body is incorrect %s: %s",
                                    email_id,
                                    type(email_body),
                                )
                                continue

                            email_dict = {
                                "id": (
                                    email_id.decode()
                                    if isinstance(email_id, bytes)
                                    else str(email_id)
                                ),
                                "subject": email_message.get("Subject", ""),
                                "from": email_message.get("From", ""),
                                "to": email_message.get("To", ""),
                                "date": email_message.get("Date", ""),
                                "size": email_size,
                            }
                            # Get email body content
                            body_content = self._extract_email_body(
                                email_message
                            )
                            email_dict["body"] = body_content

                            emails.append(email_dict)

                except (ValueError, UnicodeDecodeError) as e:
                    logger.warning(
                        "Failed to process email %s: %s", email_id, e
                    )
                    continue

            logger.info(
                "Successfully fetched %d emails from %s", len(emails), folder
            )
            return emails

        except (ConnectionError, imaplib.IMAP4.error) as e:
            logger.error("Error fetching emails: %s", e)
            raise

    def get_email_by_id(
        self,
        email_id: str,
        folder: Literal["INBOX"] = "INBOX",
    ) -> Dict:
        r"""Retrieve a specific email by ID with full metadata.

        Args:
            email_id (str): ID of the email to retrieve
            folder (Literal["INBOX"]): Folder containing the email
                (default: :obj:`"INBOX"`)

        Returns:
            Dict: Email dictionary with complete metadata
        """
        try:
            imap = self._get_imap_connection()
            imap.select(folder, readonly=True)

            status, msg_data = imap.fetch(email_id, "(BODY.PEEK[])")
            if status != IMAP_RETURN_STATUS.OK.value:
                raise ConnectionError(f"Failed to fetch email {email_id}")

            msg_tuple = msg_data[0]
            if not isinstance(msg_tuple, tuple) or len(msg_tuple) < 2:
                raise ConnectionError(
                    f"Invalid message data format for email {email_id}"
                )

            email_body = msg_tuple[1]
            if not isinstance(email_body, bytes):
                raise ConnectionError(
                    f"Email body is not bytes for email {email_id}"
                )

            email_message = email.message_from_bytes(email_body)

            email_dict = {
                "id": email_id,
                "subject": email_message.get("Subject", ""),
                "from": email_message.get("From", ""),
                "to": email_message.get("To", ""),
                "cc": email_message.get("Cc", ""),
                "bcc": email_message.get("Bcc", ""),
                "date": email_message.get("Date", ""),
                "message_id": email_message.get("Message-ID", ""),
                "reply_to": email_message.get("Reply-To", ""),
                "in_reply_to": email_message.get("In-Reply-To", ""),
                "references": email_message.get("References", ""),
                "priority": email_message.get("X-Priority", ""),
                "size": len(email_body)
                if isinstance(email_body, bytes)
                else 0,
            }

            # Get email body content
            email_dict["body"] = self._extract_email_body(email_message)

            logger.info("Successfully retrieved email %s", email_id)
            return email_dict

        except (ConnectionError, imaplib.IMAP4.error) as e:
            logger.error("Error retrieving email %s: %s", email_id, e)
            raise

    def send_email(
        self,
        to_recipients: List[str],
        subject: str,
        body: str,
        cc_recipients: Optional[List[str]] = None,
        bcc_recipients: Optional[List[str]] = None,
        html_body: Optional[str] = None,
    ) -> str:
        r"""Send an email via SMTP.

        Args:
            to_recipients (List[str]): List of recipient email addresses
            subject (str): Email subject line
            body (str): Plain text email body
            cc_recipients (List[str], optional): List of CC
                recipient email addresses
            bcc_recipients (List[str], optional): List of BCC
                recipient email addresses
            html_body (str, optional): HTML version of email body
            extra_headers (Dict[str, str], optional): Additional email headers

        Returns:
            str: Success message
        """
        if not self.username:
            raise ValueError("Username must be provided for sending emails")

        try:
            smtp = self._get_smtp_connection()

            msg = MIMEMultipart('alternative')
            msg['From'] = self.username
            msg['To'] = ", ".join(to_recipients)
            msg['Subject'] = subject

            if cc_recipients:
                msg['Cc'] = ", ".join(cc_recipients)
            if bcc_recipients:
                msg['Bcc'] = ", ".join(bcc_recipients)

            # Add plain text body
            msg.attach(MIMEText(body, 'plain'))

            # Add HTML body if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))

            # Send email
            recipients = (
                to_recipients + (cc_recipients or []) + (bcc_recipients or [])
            )
            smtp.send_message(
                msg, from_addr=self.username, to_addrs=recipients
            )

            logger.info(
                "Email sent successfully to %s", ", ".join(to_recipients)
            )
            return (
                f"Email sent successfully. To recipients: "
                f"{', '.join(to_recipients)}"
            )

        except (ConnectionError, smtplib.SMTPException) as e:
            logger.error("Error sending email: %s", e)
            raise

    def reply_to_email(
        self,
        original_email_id: str,
        reply_body: str,
        folder: Literal["INBOX"] = "INBOX",
        html_body: Optional[str] = None,
    ) -> str:
        r"""Send a reply to an existing email.

        Args:
            original_email_id (str): ID of the email to reply to
            reply_body (str): Reply message body
            folder (Literal["INBOX"]): Folder containing the original
                email (default: :obj:`"INBOX"`)
            html_body (str, optional): HTML version of reply body
                (default: :obj:`None`)

        Returns:
            str: Success message
        """
        try:
            # Get original email details
            original_email = self.get_email_by_id(original_email_id, folder)

            # Extract sender from original email
            original_from = original_email.get("from", "")

            # Create reply subject
            original_subject = original_email.get("subject", "")
            if not original_subject.startswith("Re: "):
                reply_subject = f"Re: {original_subject}"
            else:
                reply_subject = original_subject

            # Send reply
            result = self.send_email(
                to_recipients=[original_from],
                subject=reply_subject,
                body=reply_body,
                html_body=html_body,
            )

            logger.info("Successfully replied to email %s", original_email_id)
            return f"Reply sent successfully. {result}"

        except (
            ConnectionError,
            imaplib.IMAP4.error,
            smtplib.SMTPException,
        ) as e:
            logger.error(
                "Error replying to email %s: %s", original_email_id, e
            )
            raise

    def move_email_to_folder(
        self,
        email_id: str,
        target_folder: str,
        source_folder: Literal["INBOX"] = "INBOX",
    ) -> str:
        r"""Move an email to a different folder.

        Args:
            email_id (str): ID of the email to move
            target_folder (str): Destination folder name
            source_folder (Literal["INBOX"]): Source folder name
                (default: :obj:`"INBOX"`)

        Returns:
            str: Success message
        """
        try:
            imap = self._get_imap_connection()

            # Select source folder
            status, _ = imap.select(source_folder)
            self._ensure_imap_ok(status, "select source folder")

            # Copy email to target folder
            status, _ = imap.copy(email_id, target_folder)
            self._ensure_imap_ok(status, "copy email")

            # Mark email as deleted in source folder
            status, _ = imap.store(email_id, '+FLAGS', '\\Deleted')
            self._ensure_imap_ok(status, "mark email as deleted")
            status, _ = imap.expunge()
            self._ensure_imap_ok(status, "expunge deleted email")

            logger.info(
                "Successfully moved email %s from %s to %s",
                email_id,
                source_folder,
                target_folder,
            )
            return (
                f"Email {email_id} moved from {source_folder} to "
                f"{target_folder}"
            )

        except (ConnectionError, imaplib.IMAP4.error) as e:
            logger.error("Error moving email %s: %s", email_id, e)
            raise

    def delete_email(
        self,
        email_id: str,
        folder: Literal["INBOX"] = "INBOX",
        permanent: bool = False,
    ) -> str:
        r"""Delete an email.

        Args:
            email_id (str): ID of the email to delete
            folder (Literal["INBOX"]): Folder containing the email
                (default: :obj:`"INBOX"`)
            permanent (bool): If True, permanently
                delete the email (default: :obj:`False`)

        Returns:
            str: Success message
        """
        try:
            imap = self._get_imap_connection()
            status, _ = imap.select(folder)
            self._ensure_imap_ok(status, "select folder")

            if permanent:
                # Permanently delete
                status, _ = imap.store(email_id, '+FLAGS', '\\Deleted')
                self._ensure_imap_ok(status, "mark email as deleted")
                status, _ = imap.expunge()
                self._ensure_imap_ok(status, "expunge deleted email")
                action = "permanently deleted"
            else:
                # Move to trash (soft delete)
                try:
                    status, _ = imap.copy(email_id, "Trash")
                    self._ensure_imap_ok(status, "copy email to trash")
                    status, _ = imap.store(email_id, '+FLAGS', '\\Deleted')
                    self._ensure_imap_ok(status, "mark email as deleted")
                    status, _ = imap.expunge()
                    self._ensure_imap_ok(status, "expunge deleted email")
                    action = "moved to trash"
                except (imaplib.IMAP4.error, ConnectionError):
                    # If Trash folder doesn't exist, just mark as deleted
                    status, _ = imap.store(email_id, '+FLAGS', '\\Deleted')
                    self._ensure_imap_ok(status, "mark email as deleted")
                    status, _ = imap.expunge()
                    self._ensure_imap_ok(status, "expunge deleted email")
                    action = "marked as deleted"

            logger.info("Successfully %s email %s", action, email_id)
            return f"Email {email_id} {action}"

        except (ConnectionError, imaplib.IMAP4.error) as e:
            logger.error("Error deleting email %s: %s", email_id, e)
            raise

    def _extract_email_body(
        self, email_message: email.message.Message
    ) -> Dict[str, str]:
        r"""Extract plain text and HTML body from email message.

        Args:
            email_message: Email message object

        Returns:
            Dict[str, str]: Dictionary with 'plain' and 'html' body content
        """
        body_content = {"plain": "", "html": ""}

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # Skip attachments
                if "attachment" not in content_disposition:
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        if content_type == "text/plain":
                            body_content["plain"] += payload.decode(
                                'utf-8', errors='ignore'
                            )
                        elif content_type == "text/html":
                            body_content["html"] += payload.decode(
                                'utf-8', errors='ignore'
                            )
                    elif isinstance(payload, str):
                        if content_type == "text/plain":
                            body_content["plain"] += payload
                        elif content_type == "text/html":
                            body_content["html"] += payload
        else:
            content_type = email_message.get_content_type()
            payload = email_message.get_payload(decode=True)
            if isinstance(payload, bytes):
                if content_type == "text/plain":
                    body_content["plain"] = payload.decode(
                        'utf-8', errors='ignore'
                    )
                elif content_type == "text/html":
                    body_content["html"] = payload.decode(
                        'utf-8', errors='ignore'
                    )
            elif isinstance(payload, str):
                if content_type == "text/plain":
                    body_content["plain"] = payload
                elif content_type == "text/html":
                    body_content["html"] = payload

        return body_content

    def close(self) -> None:
        r"""Close all open connections.

        This method should be called when the toolkit is no longer needed
        to properly clean up network connections.
        """
        if self._imap_connection is not None:
            try:
                self._imap_connection.logout()
                logger.info("IMAP connection closed")
            except (imaplib.IMAP4.error, OSError) as e:
                logger.warning("Error closing IMAP connection: %s", e)
            finally:
                self._imap_connection = None

        if self._smtp_connection is not None:
            try:
                self._smtp_connection.quit()
                logger.info("SMTP connection closed")
            except (smtplib.SMTPException, OSError) as e:
                logger.warning("Error closing SMTP connection: %s", e)
            finally:
                self._smtp_connection = None

    def __del__(self) -> None:
        r"""Destructor to ensure connections are closed."""
        try:
            self.close()
        except Exception:
            # Silently ignore errors during cleanup to avoid issues
            # during interpreter shutdown
            pass

    def __enter__(self) -> 'IMAPMailToolkit':
        r"""Context manager entry.

        Returns:
            IMAPMailToolkit: Self instance
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        r"""Context manager exit, ensuring connections are closed.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        self.close()

    def get_tools(self) -> List[FunctionTool]:
        r"""Get list of tools provided by this toolkit.

        Returns:
            List[FunctionTool]: List of available tools
        """
        return [
            FunctionTool(self.fetch_emails),
            FunctionTool(self.get_email_by_id),
            FunctionTool(self.send_email),
            FunctionTool(self.reply_to_email),
            FunctionTool(self.move_email_to_folder),
            FunctionTool(self.delete_email),
        ]
