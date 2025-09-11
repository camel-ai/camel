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
import hashlib
import hmac
import os
import time
import urllib.parse
from typing import Any, Dict, List, Literal, Optional

import requests

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, api_keys_required, retry_on_error

logger = get_logger(__name__)

# Global variables for caching access token
_dingtalk_access_token = None
_dingtalk_access_token_expires_at = 0


@retry_on_error()
def _get_dingtalk_access_token() -> str:
    r"""Retrieves or refreshes the Dingtalk access token.

    Returns:
        str: The valid access token.

    Raises:
        ValueError: If credentials are missing or token retrieval fails.

    References:
        https://open.dingtalk.com/document/orgapp-server/obtain-identity-credentials
    """
    global _dingtalk_access_token, _dingtalk_access_token_expires_at

    if (
        _dingtalk_access_token
        and _dingtalk_access_token_expires_at > time.time()
    ):
        return _dingtalk_access_token

    app_key = os.environ.get("DINGTALK_APP_KEY", "")
    app_secret = os.environ.get("DINGTALK_APP_SECRET", "")

    url = "https://oapi.dingtalk.com/gettoken"
    params = {"appkey": app_key, "appsecret": app_secret}

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if data.get("errcode") == 0 and "access_token" in data:
        _dingtalk_access_token = data["access_token"]
        _dingtalk_access_token_expires_at = (
            time.time() + data.get("expires_in", 7200) - 60
        )
        logger.info("Dingtalk access token refreshed.")
        return _dingtalk_access_token
    else:
        errcode = data.get("errcode")
        errmsg = data.get("errmsg", "Unknown error")
        raise ValueError(f"Failed to get access token {errcode}: {errmsg}")


def _make_dingtalk_request(
    method: Literal["GET", "POST"], endpoint: str, **kwargs
) -> Dict[str, Any]:
    r"""Makes a request to Dingtalk API with proper error handling.

    Args:
        method (Literal["GET", "POST"]): HTTP method ('GET' or 'POST').
        endpoint (str): API endpoint path.
        **kwargs: Additional arguments for requests.

    Returns:
        Dict[str, Any]: API response data.

    Raises:
        requests.exceptions.RequestException: If request fails.
        ValueError: If API returns an error.
    """
    global _dingtalk_access_token, _dingtalk_access_token_expires_at
    access_token = _get_dingtalk_access_token()

    # Handle URL parameter concatenation
    separator = "&" if "?" in endpoint else "?"
    url = f"https://oapi.dingtalk.com{endpoint}{separator}access_token={access_token}"

    if method.upper() == "GET":
        response = requests.get(url, **kwargs)
    else:
        response = requests.post(url, **kwargs)

    response.raise_for_status()
    data = response.json()

    if data.get("errcode") and data.get("errcode") != 0:
        errcode = data.get("errcode")
        errmsg = data.get("errmsg", "Unknown error")
        raise ValueError(f"Dingtalk API error {errcode}: {errmsg}")

    return data


def _generate_signature(secret: str, timestamp: str) -> str:
    r"""Generate signature for Dingtalk webhook.

    Args:
        secret (str): Webhook secret.
        timestamp (str): Timestamp string.

    Returns:
        str: Base64 encoded signature.
    """
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode('utf-8'),
        string_to_sign.encode('utf-8'),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(hmac_code).decode('utf-8')


@MCPServer()
class DingtalkToolkit(BaseToolkit):
    r"""A toolkit for Dingtalk operations.

    This toolkit provides methods to interact with the Dingtalk API,
    allowing users to send messages, manage users, departments, and handle
    webhook operations.

    References:
        - Documentation: https://open.dingtalk.com/document/
        - Robot Webhook: https://open.dingtalk.com/document/robots/custom-robot-access

    Notes:
        Set environment variables: DINGTALK_APP_KEY, DINGTALK_APP_SECRET
        For webhook operations: DINGTALK_WEBHOOK_URL, DINGTALK_WEBHOOK_SECRET
    """

    def __init__(self, timeout: Optional[float] = None):
        r"""Initializes the DingtalkToolkit.

        Args:
            timeout (Optional[float]): Timeout for API requests in seconds.
        """
        super().__init__(timeout=timeout)
        self.base_url = "https://oapi.dingtalk.com"

        # Validate credentials
        app_key = os.environ.get("DINGTALK_APP_KEY", "")
        app_secret = os.environ.get("DINGTALK_APP_SECRET", "")

        if not all([app_key, app_secret]):
            raise ValueError(
                "Dingtalk credentials missing. Set DINGTALK_APP_KEY and"
                " DINGTALK_APP_SECRET."
            )

        # Initialize access token for enterprise reliability
        self._initialize_token_safely()

    def _initialize_token_safely(self):
        r"""Initialize access token with enterprise-grade error handling.

        This method attempts to fetch the access token during initialization
        to ensure the first API call will succeed. If token initialization
        fails, it logs a warning but doesn't raise an exception, allowing
        the toolkit to be created. The error will be caught on the first
        API call with a clear error message.
        """
        try:
            _get_dingtalk_access_token()
            logger.info("✅ Dingtalk access token initialized successfully.")
        except Exception as e:
            logger.warning(
                f"⚠️ Failed to initialize Dingtalk access token: {e}"
            )
            logger.warning(
                "The first API call may fail. Please check your credentials "
                "and network connection."
            )

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def send_text_message(
        self,
        userid: str,
        content: str,
    ) -> str:
        r"""Sends a text message to a Dingtalk user.

        Args:
            userid (str): The user's userid.
            content (str): Message content.

        Returns:
            str: Success or error message.

        References:
            https://open.dingtalk.com/document/orgapp-server/send-single-chat-message
        """
        payload = {
            "msg": {"msgtype": "text", "text": {"content": content}},
            "userid": userid,
        }

        try:
            _make_dingtalk_request(
                "POST",
                "/topapi/message/corpconversation/asyncsend_v2",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            return f"Message sent successfully to user {userid}."
        except Exception as e:
            return f"Failed to send message: {e!s}"

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def send_markdown_message(
        self,
        userid: str,
        title: str,
        markdown_content: str,
    ) -> str:
        r"""Sends a markdown message to a Dingtalk user.

        Args:
            userid (str): The user's userid.
            title (str): Message title.
            markdown_content (str): Markdown formatted content.

        Returns:
            str: Success or error message.
        """
        payload = {
            "msg": {
                "msgtype": "markdown",
                "markdown": {"title": title, "text": markdown_content},
            },
            "userid": userid,
        }

        try:
            _make_dingtalk_request(
                "POST",
                "/topapi/message/corpconversation/asyncsend_v2",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            return f"Markdown message sent successfully to user {userid}."
        except Exception as e:
            return f"Failed to send markdown message: {e!s}"

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def get_user_info(
        self,
        userid: str,
    ) -> Dict[str, Any]:
        r"""Retrieves Dingtalk user information.

        Args:
            userid (str): The user's userid.

        Returns:
            Dict[str, Any]: User information as dictionary or error
                information.

        References:
            https://open.dingtalk.com/document/orgapp-server/query-user-details
        """
        try:
            data = _make_dingtalk_request(
                "GET", f"/topapi/v2/user/get?userid={userid}"
            )
            return data
        except Exception as e:
            return {"error": f"Failed to get user info: {e!s}"}

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def get_department_list(
        self,
        dept_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        r"""Retrieves list of departments.

        Args:
            dept_id (Optional[int]): Department ID. If None, gets root
                departments.

        Returns:
            Dict[str, Any]: Department list as dictionary or error information.

        References:
            https://open.dingtalk.com/document/orgapp-server/obtain-the-department-list
        """
        try:
            endpoint = "/topapi/v2/department/listsub"
            if dept_id is not None:
                endpoint += f"?dept_id={dept_id}"
            data = _make_dingtalk_request("GET", endpoint)
            return data
        except Exception as e:
            return {"error": f"Failed to get department list: {e!s}"}

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def get_department_users(
        self,
        dept_id: int,
        offset: int = 0,
        size: int = 100,
    ) -> Dict[str, Any]:
        r"""Retrieves users in a department.

        Args:
            dept_id (int): Department ID.
            offset (int): Starting position. (default: 0)
            size (int): Number of users to retrieve (1-100). (default: 100)

        Returns:
            Dict[str, Any]: User list as dictionary or error information.

        References:
            https://open.dingtalk.com/document/orgapp-server/obtain-the-list-of-users-in-a-department
        """
        try:
            data = _make_dingtalk_request(
                "GET",
                f"/topapi/v2/user/list?dept_id={dept_id}&offset={offset}&size={size}",
            )
            return data
        except Exception as e:
            return {"error": f"Failed to get department users: {e!s}"}

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def search_users_by_name(
        self,
        name: str,
    ) -> Dict[str, Any]:
        r"""Searches for users by name.

        Args:
            name (str): User name to search for.

        Returns:
            Dict[str, Any]: Search results as dictionary or error information.

        References:
            https://open.dingtalk.com/document/orgapp-server/search-for-users
        """
        try:
            data = _make_dingtalk_request(
                "GET", f"/topapi/v2/user/list?name={urllib.parse.quote(name)}"
            )
            return data
        except Exception as e:
            return {"error": f"Failed to search users: {e!s}"}

    # Include more webhook methods if useful. Double check link implementation
    # is done correctly here.
    def send_webhook_message(
        self,
        content: str,
        msgtype: Literal["text", "markdown", "link", "actionCard"] = "text",
        title: Optional[str] = None,
        webhook_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ) -> str:
        r"""Sends a message via Dingtalk webhook.

        Args:
            content (str): Message content. For link messages, this should be
                the URL.
            msgtype (Literal["text", "markdown", "link", "actionCard"]):
                Message type.
            title (Optional[str]): Message title. For link messages, this is
                the link title.
            webhook_url (Optional[str]): Webhook URL. If None, uses
                DINGTALK_WEBHOOK_URL.
            webhook_secret (Optional[str]): Webhook secret. If None, uses
                DINGTALK_WEBHOOK_SECRET.

        Returns:
            str: Success or error message.

        Examples:
            # Text message
            send_webhook_message("Hello World!")

            # Markdown message
            send_webhook_message(
                "# Hello\nThis is **bold**", "markdown", "Important Update"
            )

            # Link message
            send_webhook_message(
                "https://example.com", "link", "Visit Our Website"
            )

            # ActionCard message
            send_webhook_message(
                "Click the button below to proceed", "actionCard",
                "Action Required"
            )

        References:
            https://open.dingtalk.com/document/robots/custom-robot-access
        """
        if not webhook_url:
            webhook_url = os.environ.get("DINGTALK_WEBHOOK_URL", "")
        if not webhook_secret:
            webhook_secret = os.environ.get("DINGTALK_WEBHOOK_SECRET", "")

        if not webhook_url:
            return (
                "Webhook URL not provided. Set DINGTALK_WEBHOOK_URL "
                "environment variable."
            )

        # Generate signature if secret is provided
        timestamp = str(round(time.time() * 1000))
        sign = ""
        if webhook_secret:
            sign = _generate_signature(webhook_secret, timestamp)

        # Build webhook URL with parameters
        url_params = {"timestamp": timestamp}
        if sign:
            url_params["sign"] = sign
        webhook_url_with_params = f"{webhook_url}&" + "&".join(
            [f"{k}={v}" for k, v in url_params.items()]
        )

        # Build message payload
        payload: Dict[str, Any] = {"msgtype": msgtype}

        if msgtype == "text":
            payload["text"] = {"content": content}
        elif msgtype == "markdown":
            payload["markdown"] = {
                "title": title or "Message",
                "text": content,
            }
        elif msgtype == "link":
            # For link messages, content should be the URL, title is the
            # link title
            payload["link"] = {
                "messageUrl": content,
                "title": title or "Link",
                "text": title or "Click to open link",
            }
        elif msgtype == "actionCard":
            # For actionCard messages, content is the card text, title is the
            # card title
            payload["actionCard"] = {
                "title": title or "Action Card",
                "text": content,
                "btnOrientation": "0",  # Vertical button arrangement
            }

        try:
            response = requests.post(
                webhook_url_with_params,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout or 30,
            )
            response.raise_for_status()
            result = response.json()

            if result.get("errcode") == 0:
                return "Webhook message sent successfully."
            else:
                return (
                    f"Webhook error: {result.get('errmsg', 'Unknown error')}"
                )
        except Exception as e:
            return f"Failed to send webhook message: {e!s}"

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def create_group(
        self,
        name: str,
        owner: str,
        useridlist: List[str],
    ) -> Dict[str, Any]:
        r"""Creates a Dingtalk group.

        Args:
            name (str): Group name.
            owner (str): Group owner userid.
            useridlist (List[str]): List of user IDs to add to the group.

        Returns:
            Dict[str, Any]: Group creation result or error information.

        References:
            https://open.dingtalk.com/document/orgapp-server/create-a-group-chat
        """
        payload = {"name": name, "owner": owner, "useridlist": useridlist}

        try:
            data = _make_dingtalk_request(
                "POST",
                "/topapi/im/chat/group/create",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            return data
        except Exception as e:
            return {"error": f"Failed to create group: {e!s}"}

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def send_group_message(
        self,
        chatid: str,
        content: str,
        msgtype: Literal["text", "markdown"] = "text",
    ) -> str:
        r"""Sends a message to a Dingtalk group.

        Args:
            chatid (str): Group chat ID.
            content (str): Message content.
            msgtype (Literal["text", "markdown"]): Message type.

        Returns:
            str: Success or error message.

        References:
            https://open.dingtalk.com/document/orgapp-server/send-group-chat-messages
        """
        payload: Dict[str, Any] = {
            "chatid": chatid,
            "msg": {
                "msgtype": msgtype,
                "text": {"content": content} if msgtype == "text" else None,
                "markdown": (
                    {"text": content} if msgtype == "markdown" else None
                ),
            },
        }

        # Remove None values
        if payload["msg"]["text"] is None:
            del payload["msg"]["text"]
        if payload["msg"]["markdown"] is None:
            del payload["msg"]["markdown"]

        try:
            _make_dingtalk_request(
                "POST",
                "/topapi/im/chat/send",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            return f"Group message sent successfully to chat {chatid}."
        except Exception as e:
            return f"Failed to send group message: {e!s}"

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns toolkit functions as tools."""
        return [
            FunctionTool(self.send_text_message),
            FunctionTool(self.send_markdown_message),
            FunctionTool(self.get_user_info),
            FunctionTool(self.get_department_list),
            FunctionTool(self.get_department_users),
            FunctionTool(self.search_users_by_name),
            FunctionTool(self.send_webhook_message),
            FunctionTool(self.create_group),
            FunctionTool(self.send_group_message),
        ]


# many other functionalities, cards etc build on top after initial works
