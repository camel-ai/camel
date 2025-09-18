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

from typing import Dict, List, Optional, cast

from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.utils import MCPServer, api_keys_required


@MCPServer()
class ResendToolkit(BaseToolkit):
    r"""A toolkit for sending emails using the Resend API.

    This toolkit provides functionality to send emails using Resend's
    Python SDK.It supports sending both HTML and plain text emails,
    with options for multiple recipients, CC, BCC, reply-to
    addresses, and custom headers.

    Notes:
        To use this toolkit, you need to set the following environment
        variable:
        - RESEND_API_KEY: Your Resend API key. You can get one from
          https://resend.com/api-keys

    Example:
        .. code-block:: python

            from camel.toolkits import ResendToolkit

            # Initialize the toolkit
            toolkit = ResendToolkit()

            # Get tools
            tools = toolkit.get_tools()
    """

    @api_keys_required([(None, "RESEND_API_KEY")])
    def send_email(
        self,
        to: List[str],
        subject: str,
        from_email: str,
        html: Optional[str] = None,
        text: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        tags: Optional[List[Dict[str, str]]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        r"""Send an email using the Resend API.

        Args:
            to (List[str]): List of recipient email addresses.
            subject (str): The email subject line.
            from_email (str): The sender email address. Must be from a verified
                domain.
            html (Optional[str]): The HTML content of the email. Either html or
                text must be provided. (default: :obj:`None`)
            text (Optional[str]): The plain text content of the email. Either
                html or text must be provided. (default: :obj:`None`)
            cc (Optional[List[str]]): List of CC recipient email addresses.
                (default: :obj:`None`)
            bcc (Optional[List[str]]): List of BCC recipient email addresses.
                (default: :obj:`None`)
            reply_to (Optional[str]): The reply-to email address.
                (default: :obj:`None`)
            tags (Optional[List[Dict[str, str]]]): List of tags to attach to
                the email. Each tag should be a dict with 'name' and
                'value' keys. (default: :obj:`None`)
            headers (Optional[Dict[str, str]]): Custom headers to include in
                the email.(default: :obj:`None`)

        Returns:
            str: A success message with the email ID if sent successfully,
                or an error message if the send failed.

        Raises:
            ValueError: If neither html nor text content is provided.

        Example:
            .. code-block:: python

                toolkit = ResendToolkit()
                result = toolkit.send_email(
                    to=["recipient@example.com"],
                    subject="Hello World",
                    from_email="sender@yourdomain.com",
                    html="<h1>Hello, World!</h1>",
                    text="Hello, World!"
                )
        """
        import os

        if not html and not text:
            raise ValueError(
                "Either 'html' or 'text' content must be provided"
            )

        try:
            import resend
        except ImportError:
            raise ImportError(
                "Please install the resend package first. "
                "You can install it by running `pip install resend`."
            )

        # Set the API key
        resend.api_key = os.getenv("RESEND_API_KEY")

        # Prepare email parameters
        params: resend.Emails.SendParams = {
            "from": from_email,
            "to": to,
            "subject": subject,
        }

        # Add content
        if html:
            params["html"] = html
        if text:
            params["text"] = text

        # Add optional parameters
        if cc:
            params["cc"] = cc
        if bcc:
            params["bcc"] = bcc
        if reply_to:
            params["reply_to"] = reply_to
        if tags:
            params["tags"] = cast('list[resend.emails._tag.Tag]', tags)
        if headers:
            params["headers"] = headers

        try:
            # Send the email
            email = resend.Emails.send(params)
            return (
                f"Email sent successfully. "
                f"Email ID: {email.get('id', 'Unknown')}"
            )
        except Exception as e:
            return f"Failed to send email: {e!s}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.send_email),
        ]
