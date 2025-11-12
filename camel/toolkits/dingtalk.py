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
import re
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
    r"""Gets access token for Dingtalk API.

    Returns:
        str: Access token for API requests.
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

    response = requests.get(url, params=params, timeout=30)
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
    r"""Makes authenticated request to Dingtalk API.

    Args:
        method (Literal["GET", "POST"]): HTTP method to use.
        endpoint (str): API endpoint path.
        **kwargs: Additional arguments passed to requests.

    Returns:
        Dict[str, Any]: API response data.

    Raises:
        Exception: If API request fails or returns error.
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
    r"""Generates signature for Dingtalk webhook.

    Args:
        secret (str): Webhook secret.
        timestamp (str): Current timestamp.

    Returns:
        str: Generated signature.
    """
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256
    ).digest()
    return base64.b64encode(hmac_code).decode('utf-8')


@MCPServer()
class DingtalkToolkit(BaseToolkit):
    r"""A toolkit for Dingtalk operations.

    This toolkit provides methods to interact with the Dingtalk API,
    allowing users to send messages, manage users, departments, and handle
    webhook operations.
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
        r"""Safely initializes access token during toolkit setup.

        This method attempts to get an access token during initialization
        but doesn't raise exceptions if it fails, allowing the toolkit
        to be instantiated even if credentials are temporarily invalid.
        """
        try:
            _get_dingtalk_access_token()
            logger.info("Dingtalk toolkit initialized successfully.")
        except Exception as e:
            logger.warning(f"Failed to initialize access token: {e}")
            logger.warning(
                "Toolkit created but may fail on actual API calls. "
                "Check your credentials."
            )

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def dingtalk_send_text_message(
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
    def dingtalk_send_markdown_message(
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

        References:
            https://open.dingtalk.com/document/orgapp-server/send-single-chat-message
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
    def dingtalk_get_user_info(
        self,
        userid: str,
    ) -> Dict[str, Any]:
        r"""Retrieves Dingtalk user information.

        Args:
            userid (str): The user's userid.

        Returns:
            Dict[str, Any]: User information or error information.

        References:
            https://open.dingtalk.com/document/orgapp-server/query-user-details
        """
        payload = {"userid": userid}

        try:
            data = _make_dingtalk_request(
                "POST",
                "/topapi/v2/user/get",
                headers={"Content-Type": "application/json"},
                json=payload,
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
    def dingtalk_get_department_list(
        self,
        dept_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        r"""Retrieves list of departments.

        Args:
            dept_id (Optional[int]): Department ID. If None, gets root
                departments.

        Returns:
            Dict[str, Any]: Department list or error information.

        References:
            https://open.dingtalk.com/document/orgapp-server/obtain-the-department-list-v2
        """
        payload = {}
        if dept_id is not None:
            payload["dept_id"] = dept_id

        try:
            data = _make_dingtalk_request(
                "POST",
                "/topapi/v2/department/listsub",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            return data
        except Exception as e:
            return {"error": f"Failed to get department list: {e!s}"}

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def dingtalk_get_department_users(
        self,
        dept_id: int,
        offset: int = 0,
        size: int = 100,
    ) -> Dict[str, Any]:
        r"""Retrieves users in a department.

        Args:
            dept_id (int): Department ID.
            offset (int): Offset for pagination (default: 0).
            size (int): Number of users to retrieve (default: 100, max: 100).

        Returns:
            Dict[str, Any]: Users list or error information.

        References:
            https://open.dingtalk.com/document/orgapp-server/queries-the-complete-information-of-a-department-user
        """
        payload = {"dept_id": dept_id, "offset": offset, "size": size}

        try:
            data = _make_dingtalk_request(
                "POST",
                "/topapi/v2/user/list",
                headers={"Content-Type": "application/json"},
                json=payload,
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
    def dingtalk_search_users_by_name(
        self,
        name: str,
    ) -> Dict[str, Any]:
        r"""Searches for users by name.

        Args:
            name (str): User name to search for.

        Returns:
            Dict[str, Any]: Search results or error information.

        References:
            https://open.dingtalk.com/document/orgapp-server/query-users
        """
        payload = {"name": name}

        try:
            data = _make_dingtalk_request(
                "POST",
                "/topapi/user/search",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            return data
        except Exception as e:
            return {"error": f"Failed to search users: {e!s}"}

    # Include more webhook methods if useful. Double check link implementation
    # is done correctly here.
    def dingtalk_send_webhook_message(
        self,
        content: str,
        msgtype: Literal["text", "markdown", "link", "actionCard"] = "text",
        title: Optional[str] = None,
        webhook_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ) -> str:
        r"""Sends a message via Dingtalk webhook.

        Args:
            content (str): Message content.
            msgtype (Literal): Message type (text, markdown, link, actionCard).
            title (Optional[str]): Message title (required for markdown).
            webhook_url (Optional[str]): Webhook URL. If None, uses env var.
            webhook_secret (Optional[str]): Webhook secret. If None, uses env
                var.

        Returns:
            str: Success or error message.

        References:
            https://open.dingtalk.com/document/robots/custom-robot-access
        """
        # Get webhook configuration
        url = webhook_url or os.environ.get("DINGTALK_WEBHOOK_URL", "")
        secret = webhook_secret or os.environ.get(
            "DINGTALK_WEBHOOK_SECRET", ""
        )

        if not url:
            return "Error: Webhook URL not provided or set in environment"

        # Prepare message payload
        payload: Dict[str, Any] = {"msgtype": msgtype}

        if msgtype == "text":
            payload["text"] = {"content": content}
        elif msgtype == "markdown":
            if not title:
                return "Error: Title is required for markdown messages"
            payload["markdown"] = {"title": title, "text": content}
        elif msgtype == "link":
            # For link messages, content should be structured differently
            # This is a simplified implementation
            payload["link"] = {
                "text": content,
                "title": title or "Link Message",
                "messageUrl": "https://www.dingtalk.com/",
            }
        elif msgtype == "actionCard":
            payload["actionCard"] = {
                "title": title or "Action Card",
                "text": content,
                "singleTitle": "Read More",
                "singleURL": "https://www.dingtalk.com/",
            }

        # Add signature if secret is provided
        if secret:
            timestamp = str(round(time.time() * 1000))
            sign = _generate_signature(secret, timestamp)
            url += f"&timestamp={timestamp}&sign={urllib.parse.quote(sign)}"

        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()

            result = response.json()
            if result.get("errcode") == 0:
                return "Webhook message sent successfully"
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
    def dingtalk_create_group(
        self,
        name: str,
        owner: str,
        useridlist: List[str],
    ) -> Dict[str, Any]:
        r"""Creates a Dingtalk group.

        Args:
            name (str): Group name.
            owner (str): Group owner's userid.
            useridlist (List[str]): List of user IDs to add to the group.

        Returns:
            Dict[str, Any]: Group creation result with chatid or error.

        References:
            https://open.dingtalk.com/document/orgapp-server/create-group-session
        """
        payload = {
            "name": name,
            "owner": owner,
            "useridlist": useridlist,
        }

        try:
            data = _make_dingtalk_request(
                "POST",
                "/topapi/im/chat/create",
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
    def dingtalk_send_group_message(
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
            https://open.dingtalk.com/document/orgapp-server/send-group-messages
        """
        msg_data: Dict[str, Any] = {"msgtype": msgtype}

        if msgtype == "text":
            msg_data["text"] = {"content": content}
        elif msgtype == "markdown":
            msg_data["markdown"] = {"text": content}

        payload = {
            "msg": msg_data,
            "chatid": chatid,
        }

        try:
            _make_dingtalk_request(
                "POST",
                "/topapi/message/corpconversation/asyncsend_v2",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            return f"Message sent successfully to group {chatid}."
        except Exception as e:
            return f"Failed to send group message: {e!s}"

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def dingtalk_send_link_message(
        self,
        userid: str,
        title: str,
        text: str,
        message_url: str,
        pic_url: Optional[str] = None,
    ) -> str:
        r"""Sends a link message to a Dingtalk user.

        Args:
            userid (str): The user's userid.
            title (str): Link title.
            text (str): Link description text.
            message_url (str): URL to link to.
            pic_url (Optional[str]): Picture URL for the link.

        Returns:
            str: Success or error message.

        References:
            https://open.dingtalk.com/document/orgapp-server/send-single-chat-message
        """
        link_data: Dict[str, Any] = {
            "title": title,
            "text": text,
            "messageUrl": message_url,
        }

        if pic_url:
            link_data["picUrl"] = pic_url

        payload = {
            "msg": {"msgtype": "link", "link": link_data},
            "userid": userid,
        }

        try:
            _make_dingtalk_request(
                "POST",
                "/topapi/message/corpconversation/asyncsend_v2",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            return f"Link message sent successfully to user {userid}."
        except Exception as e:
            return f"Failed to send link message: {e!s}"

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def dingtalk_send_action_card_message(
        self,
        userid: str,
        title: str,
        text: str,
        single_title: str,
        single_url: str,
    ) -> str:
        r"""Sends an action card message to a Dingtalk user.

        Args:
            userid (str): The user's userid.
            title (str): Card title.
            text (str): Card content text.
            single_title (str): Action button title.
            single_url (str): Action button URL.

        Returns:
            str: Success or error message.

        References:
            https://open.dingtalk.com/document/orgapp-server/send-single-chat-message
        """
        payload = {
            "msg": {
                "msgtype": "actionCard",
                "actionCard": {
                    "title": title,
                    "text": text,
                    "singleTitle": single_title,
                    "singleURL": single_url,
                },
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
            return f"Action card message sent successfully to user {userid}."
        except Exception as e:
            return f"Failed to send action card message: {e!s}"

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def dingtalk_get_user_by_mobile(self, mobile: str) -> Dict[str, Any]:
        r"""Gets user information by mobile number.

        Args:
            mobile (str): User's mobile number. Should be a valid Chinese
                mobile number format (11 digits starting with 1).

        Returns:
            Dict[str, Any]: User information or error information.
        """
        # Validate mobile number format (Chinese mobile number: 11 digits
        # starting with 1)
        mobile_pattern = r'^1[3-9]\d{9}$'
        if not re.match(mobile_pattern, mobile):
            return {
                "error": "Invalid mobile number format. Expected 11 digits "
                "starting with 1 (e.g., 13800000000)."
            }

        payload = {"mobile": mobile}

        try:
            data = _make_dingtalk_request(
                "POST",
                "/topapi/v2/user/getbymobile",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            return data
        except Exception as e:
            return {"error": f"Failed to get user by mobile: {e!s}"}

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def dingtalk_get_user_by_unionid(self, unionid: str) -> Dict[str, Any]:
        r"""Gets user information by unionid.

        Args:
            unionid (str): User's unique identifier across all DingTalk
                organizations. This is a global identifier that remains
                consistent even if the user belongs to multiple DingTalk
                organizations, unlike userid which is organization-specific.

        Returns:
            Dict[str, Any]: User information or error information.

        References:
            https://open.dingtalk.com/document/orgapp-server/query-a-user-by-the-union-id
        """
        try:
            data = _make_dingtalk_request(
                "POST",
                "/topapi/user/getbyunionid",
                headers={"Content-Type": "application/json"},
                json={"unionid": unionid},
            )
            return data
        except Exception as e:
            return {"error": f"Failed to get user by unionid: {e!s}"}

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def dingtalk_get_department_detail(self, dept_id: int) -> Dict[str, Any]:
        r"""Gets detailed information about a department.

        Args:
            dept_id (int): Department ID.

        Returns:
            Dict[str, Any]: Department details or error information.

        References:
            https://open.dingtalk.com/document/orgapp-server/query-department-details0-v2
        """
        payload = {"dept_id": dept_id}

        try:
            data = _make_dingtalk_request(
                "POST",
                "/topapi/v2/department/get",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            return data
        except Exception as e:
            return {"error": f"Failed to get department detail: {e!s}"}

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def dingtalk_send_oa_message(
        self,
        userid: str,
        message_url: str,
        head_bgcolor: str,
        head_text: str,
        body_title: str,
        body_content: str,
    ) -> str:
        r"""Sends an OA (Office Automation) message to a Dingtalk user.

        Args:
            userid (str): The user's userid.
            message_url (str): URL for the message action.
            head_bgcolor (str): Header background color (hex format).
            head_text (str): Header text.
            body_title (str): Body title.
            body_content (str): Body content.

        Returns:
            str: Success or error message.

        References:
            https://open.dingtalk.com/document/orgapp-server/send-single-chat-message
        """
        oa_data: Dict[str, Any] = {
            "message_url": message_url,
            "head": {
                "bgcolor": head_bgcolor,
                "text": head_text,
            },
            "body": {
                "title": body_title,
                "form": [{"key": "Content:", "value": body_content}],
            },
        }

        payload = {
            "msg": {"msgtype": "oa", "oa": oa_data},
            "userid": userid,
        }

        try:
            _make_dingtalk_request(
                "POST",
                "/topapi/message/corpconversation/asyncsend_v2",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            return f"OA message sent successfully to user {userid}."
        except Exception as e:
            return f"Failed to send OA message: {e!s}"

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def dingtalk_get_group_info(self, chatid: str) -> Dict[str, Any]:
        r"""Gets information about a group chat.

        Args:
            chatid (str): Group chat ID.

        Returns:
            Dict[str, Any]: Group information or error information.

        References:
            https://open.dingtalk.com/document/orgapp-server/query-group-session-information
        """
        payload = {"chatid": chatid}

        try:
            data = _make_dingtalk_request(
                "POST",
                "/topapi/im/chat/get",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            return data
        except Exception as e:
            return {"error": f"Failed to get group info: {e!s}"}

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def dingtalk_update_group(
        self,
        chatid: str,
        name: Optional[str] = None,
        owner: Optional[str] = None,
        add_useridlist: Optional[List[str]] = None,
        del_useridlist: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        r"""Updates a Dingtalk group configuration.

        Args:
            chatid (str): Group chat ID.
            name (Optional[str]): New group name.
            owner (Optional[str]): New group owner userid.
            add_useridlist (Optional[List[str]]): List of user IDs to add.
                Note: Internally converted to comma-separated string as
                required by the DingTalk API.
            del_useridlist (Optional[List[str]]): List of user IDs to remove.
                Note: Internally converted to comma-separated string as
                required by the DingTalk API.

        Returns:
            Dict[str, Any]: Update result or error information.

        References:
            https://open.dingtalk.com/document/orgapp-server/modify-group-session
        """
        payload: Dict[str, Any] = {"chatid": chatid}

        if name:
            payload["name"] = name
        if owner:
            payload["owner"] = owner
        # Note: DingTalk update group API requires comma-separated string
        # format
        # This is different from send_work_notification which uses array format
        if add_useridlist:
            payload["add_useridlist"] = ",".join(add_useridlist)
        if del_useridlist:
            payload["del_useridlist"] = ",".join(del_useridlist)

        try:
            data = _make_dingtalk_request(
                "POST",
                "/topapi/im/chat/update",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            return data
        except Exception as e:
            return {"error": f"Failed to update group: {e!s}"}

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def dingtalk_send_work_notification(
        self,
        userid_list: List[str],
        msg_content: str,
        msg_type: Literal["text", "markdown"] = "text",
    ) -> str:
        r"""Sends work notification to multiple users.

        Args:
            userid_list (List[str]): List of user IDs to send to.
                Note: This API accepts array format, unlike some other APIs
                that require comma-separated strings.
            msg_content (str): Message content.
            msg_type (Literal["text", "markdown"]): Message type.

        Returns:
            str: Success or error message.

        References:
            https://open.dingtalk.com/document/orgapp-server/asynchronous-sending-of-enterprise-session-messages
        """
        if not userid_list:
            return "Error: userid_list cannot be empty"

        if len(userid_list) > 100:
            return "Error: Cannot send to more than 100 users at once"

        msg_data: Dict[str, Any] = {"msgtype": msg_type}
        if msg_type == "text":
            msg_data["text"] = {"content": msg_content}
        elif msg_type == "markdown":
            msg_data["markdown"] = {"text": msg_content}

        payload = {
            "msg": msg_data,
            "userid_list": userid_list,  # Array format for this API
        }

        try:
            _make_dingtalk_request(
                "POST",
                "/topapi/message/corpconversation/asyncsend_v2",
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            return (
                f"Work notification sent successfully to "
                f"{len(userid_list)} users."
            )
        except Exception as e:
            return f"Failed to send work notification: {e!s}"

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def dingtalk_get_userid_by_phone(self, phone_number: str) -> str:
        r"""Gets user ID by phone number for LLM agents.

        Args:
            phone_number (str): User's phone number.

        Returns:
            str: User ID or error message.

        References:
            https://open.dingtalk.com/document/orgapp-server/query-user-details
        """
        try:
            user_info = self.dingtalk_get_user_by_mobile(phone_number)
            if 'result' in user_info and 'userid' in user_info['result']:
                return user_info['result']['userid']
            else:
                return f"User not found for phone number: {phone_number}"
        except Exception as e:
            return f"Failed to get user ID by phone: {e!s}"

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def dingtalk_get_userid_by_name(self, user_name: str) -> str:
        r"""Gets user ID by user name for LLM agents.

        Args:
            user_name (str): User's display name.

        Returns:
            str: User ID or error message.

        References:
            https://open.dingtalk.com/document/orgapp-server/query-users
        """
        try:
            search_result = self.dingtalk_search_users_by_name(user_name)
            if search_result.get('result'):
                # Return the first match
                return search_result['result'][0].get(
                    'userid', f"No userid found for user: {user_name}"
                )
            else:
                return f"User not found with name: {user_name}"
        except Exception as e:
            return f"Failed to get user ID by name: {e!s}"

    @api_keys_required(
        [
            (None, "DINGTALK_APP_KEY"),
            (None, "DINGTALK_APP_SECRET"),
        ]
    )
    def dingtalk_get_department_id_by_name(self, department_name: str) -> str:
        r"""Gets department ID by department name for LLM agents.

        Args:
            department_name (str): Department name to search for.

        Returns:
            str: Department ID or error message.
        """
        try:
            dept_list = self.dingtalk_get_department_list()
            if 'result' in dept_list:
                for dept in dept_list['result']:
                    if dept.get('name') == department_name:
                        return str(dept.get('id', ''))
                return f"Department not found: {department_name}"
            else:
                return "Failed to get department list"
        except Exception as e:
            return f"Failed to get department ID by name: {e!s}"

    def dingtalk_get_chatid_by_group_name(self, group_name: str) -> str:
        r"""Gets chat ID by group name for LLM agents.

        Note: This function provides guidance as Dingtalk API doesn't directly
        support searching groups by name. Users should use the group creation
        response or group management features to obtain chat IDs.

        Args:
            group_name (str): Group name to search for.

        Returns:
            str: Guidance message for obtaining chat ID.
        """
        return (
            f"To get chat ID for group '{group_name}': "
            "1. Use dingtalk_create_group() and save the returned chatid, or "
            "2. Contact group admin to provide the chat ID, or "
            "3. Use Dingtalk admin console to find the group ID. "
            "Chat IDs are typically returned when creating groups."
        )

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns toolkit functions as tools."""
        return [
            # Original message functions
            FunctionTool(self.dingtalk_send_text_message),
            FunctionTool(self.dingtalk_send_markdown_message),
            FunctionTool(self.dingtalk_send_webhook_message),
            # New message types
            FunctionTool(self.dingtalk_send_link_message),
            FunctionTool(self.dingtalk_send_action_card_message),
            FunctionTool(self.dingtalk_send_oa_message),
            FunctionTool(self.dingtalk_send_work_notification),
            # User management functions
            FunctionTool(self.dingtalk_get_user_info),
            FunctionTool(self.dingtalk_get_user_by_mobile),
            FunctionTool(self.dingtalk_get_user_by_unionid),
            FunctionTool(self.dingtalk_search_users_by_name),
            # Department management functions
            FunctionTool(self.dingtalk_get_department_list),
            FunctionTool(self.dingtalk_get_department_users),
            FunctionTool(self.dingtalk_get_department_detail),
            # Group management functions
            FunctionTool(self.dingtalk_create_group),
            FunctionTool(self.dingtalk_send_group_message),
            FunctionTool(self.dingtalk_get_group_info),
            FunctionTool(self.dingtalk_update_group),
            # Helper functions for LLM agents to get IDs
            FunctionTool(self.dingtalk_get_userid_by_phone),
            FunctionTool(self.dingtalk_get_userid_by_name),
            FunctionTool(self.dingtalk_get_department_id_by_name),
            FunctionTool(self.dingtalk_get_chatid_by_group_name),
        ]


# many other functionalities, cards etc build on top after initial works
