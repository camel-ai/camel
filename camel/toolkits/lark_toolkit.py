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
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union

import requests

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, api_keys_required

logger = get_logger(__name__)


@MCPServer()
class LarkToolkit(BaseToolkit):
    r"""A toolkit for Lark (Feishu) chat operations."""

    @api_keys_required(
        [
            ("app_id", "LARK_APP_ID"),
            ("app_secret", "LARK_APP_SECRET"),
        ]
    )
    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        use_feishu: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initializes the LarkToolkit.

        Args:
            app_id (Optional[str]): The Lark application ID. If not provided,
                uses LARK_APP_ID environment variable.
            app_secret (Optional[str]): The Lark application secret. If not
                provided, uses LARK_APP_SECRET environment variable.
            use_feishu (bool): Set to True to use Feishu (China) API endpoints
                instead of Lark (international). (default: :obj:`False`)
            timeout (Optional[float]): Request timeout in seconds.
        """
        super().__init__(timeout=timeout)

        self._app_id = app_id or os.environ.get("LARK_APP_ID", "")
        self._app_secret = app_secret or os.environ.get("LARK_APP_SECRET", "")
        self._use_feishu = use_feishu

        # Set domain based on region
        if use_feishu:
            self._domain = "https://open.feishu.cn"
        else:
            self._domain = "https://open.larksuite.com"

        self._tenant_access_token: Optional[str] = None
        self._tenant_token_expires_at: Optional[float] = None
        camel_workdir = os.environ.get("CAMEL_WORKDIR")
        if camel_workdir:
            self.working_dir = os.path.abspath(camel_workdir)
        else:
            self.working_dir = os.path.abspath("./workspace")

        region = "Feishu (China)" if use_feishu else "Lark (International)"
        logger.info(f"LarkToolkit initialized for {region}")

    def _get_tenant_http_headers(self) -> Dict[str, str]:
        r"""Get HTTP headers with tenant access token authorization.

        Returns:
            Dict[str, str]: Headers dict with Content-Type and Authorization.
        """
        headers = {"Content-Type": "application/json; charset=utf-8"}
        now = time.time()
        if self._tenant_access_token and self._tenant_token_expires_at:
            if self._tenant_token_expires_at - now > 1800:
                headers["Authorization"] = (
                    f"Bearer {self._tenant_access_token}"
                )
                return headers

        url = f"{self._domain}/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": self._app_id, "app_secret": self._app_secret}
        response = requests.post(
            url, headers=headers, json=payload, timeout=30
        )
        result = response.json()

        if result.get("code") == 0:
            token = result.get("tenant_access_token")
            expire = result.get("expire")
            if token:
                self._tenant_access_token = token
                if isinstance(expire, (int, float)):
                    self._tenant_token_expires_at = now + float(expire)
                headers["Authorization"] = f"Bearer {token}"
                return headers

        logger.error(
            "Failed to get tenant access token: "
            f"{result.get('code')} - {result.get('msg')}"
        )
        raise RuntimeError(
            f"Failed to get tenant access token: {result.get('msg')}"
        )

    def _convert_timestamp(self, ts: Any) -> str:
        r"""Convert millisecond timestamp to readable datetime string.

        Args:
            ts: Timestamp value (can be string or int, in milliseconds).

        Returns:
            str: ISO format datetime string, or original value if conversion
                fails.
        """
        try:
            ts_int = int(ts)
            # Convert milliseconds to seconds
            dt = datetime.fromtimestamp(ts_int / 1000, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except (ValueError, TypeError, OSError):
            return str(ts)

    def _process_message_items(
        self, items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        r"""Process message items to agent-friendly format.

        Args:
            items: List of message items from API response.

        Returns:
            List[Dict[str, Any]]: Simplified items with only essential fields.
        """
        processed = []
        for item in items:
            # Parse message content
            text = ""
            body = item.get("body", {})
            content = body.get("content", "")
            if content:
                try:
                    content_obj = json.loads(content)
                    if "text" in content_obj:
                        text = content_obj["text"]
                    elif "template" in content_obj:
                        # System message: render template
                        tpl = content_obj["template"]
                        for key in ["from_user", "to_chatters"]:
                            val = content_obj.get(key, [])
                            if val:
                                tpl = tpl.replace(
                                    "{" + key + "}", ", ".join(val)
                                )
                            else:
                                tpl = tpl.replace("{" + key + "}", "")
                        text = tpl.strip()
                    elif "image_key" in content_obj:
                        text = f"[Image: {content_obj['image_key']}]"
                    elif "file_key" in content_obj:
                        text = f"[File: {content_obj['file_key']}]"
                except (json.JSONDecodeError, TypeError):
                    text = content

            # Build simplified message
            sender = item.get("sender", {})
            msg = {
                "message_id": item.get("message_id"),
                "msg_type": item.get("msg_type"),
                "text": text,
                "time": self._convert_timestamp(item.get("create_time", "")),
                "sender_id": sender.get("id") or None,
                "sender_type": sender.get("sender_type") or None,
            }
            processed.append(msg)
        return processed

    def lark_list_chats(
        self,
        sort_type: Literal["ByCreateTimeAsc", "ByActiveTimeDesc"] = (
            "ByCreateTimeAsc"
        ),
        page_size: int = 20,
        page_token: Optional[str] = None,
    ) -> Dict[str, object]:
        r"""Lists chats and groups that the user belongs to.

        Use this method to discover available chats and obtain chat_id values.

        Args:
            sort_type (str): Sort order for chats. Options:
                - "ByCreateTimeAsc" (default)
                - "ByActiveTimeDesc"
            page_size (int): Number of chats to return per page (max 100).
                (default: :obj:`20`)
            page_token (Optional[str]): Token for pagination. Use the
                page_token from previous response to get next page.

        Returns:
            Dict[str, object]: A dictionary containing:
                - chats: List of chat objects with chat_id and name
                - has_more: Whether there are more chats to fetch
                - page_token: Token to fetch the next page
        """
        try:
            url = f"{self._domain}/open-apis/im/v1/chats"
            headers = self._get_tenant_http_headers()

            params: Dict[str, Union[str, int]] = {
                "page_size": min(page_size, 100),
                "sort_type": sort_type,
            }
            if page_token:
                params["page_token"] = page_token

            response = requests.get(
                url, headers=headers, params=params, timeout=30
            )
            result = response.json()

            if result.get("code") != 0:
                logger.error(
                    f"Failed to list chats: {result.get('code')} - "
                    f"{result.get('msg')}"
                )
                return {
                    "error": f"Failed to list chats: {result.get('msg')}",
                    "code": result.get("code"),
                }

            # Simplify chat items
            data = result.get("data", {})
            items = data.get("items", [])
            simplified = [
                {"chat_id": c.get("chat_id"), "name": c.get("name", "")}
                for c in items
            ]
            return {
                "chats": simplified,
                "has_more": data.get("has_more", False),
                "page_token": data.get("page_token", ""),
            }

        except Exception as e:
            logger.error(f"Error listing chats: {e}")
            return {"error": f"Error listing chats: {e!s}"}

    def lark_get_chat_messages(
        self,
        container_id: str,
        container_id_type: Literal["chat", "thread"] = "chat",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        sort_type: Literal[
            "ByCreateTimeAsc", "ByCreateTimeDesc"
        ] = "ByCreateTimeAsc",
        page_size: int = 20,
        page_token: Optional[str] = None,
    ) -> Dict[str, object]:
        r"""Gets message history from a chat with optional time filtering.

        Retrieves messages from a specific chat. Requires the bot to be a
        member of the chat.

        Args:
            container_id (str): The container ID to retrieve messages from.
            container_id_type (str): The container type. Options:
                - "chat": Chat (p2p or group)
                - "thread": Thread
            start_time (Optional[str]): Start time filter (Unix timestamp in
                seconds, e.g., "1609459200"). Messages created after this time.
                Not supported for "thread" container type.
            end_time (Optional[str]): End time filter (Unix timestamp in
                seconds). Messages created before this time.
                Not supported for "thread" container type.
            sort_type (str): Sort order for messages. Options:
                - "ByCreateTimeAsc": Oldest first (default)
                - "ByCreateTimeDesc": Newest first
            page_size (int): Number of messages to return per page (max 50).
                (default: :obj:`20`)
            page_token (Optional[str]): Token for pagination. Use the
                page_token from previous response to get next page.

        Returns:
            Dict[str, object]: A dictionary containing:
                - messages: List of processed message objects with fields:
                    - message_id: Message identifier
                    - msg_type: Message type (text, image, file, etc.)
                    - text: Extracted message text content
                    - time: Human-readable timestamp (UTC)
                    - sender_id: Sender's user ID
                    - sender_type: Type of sender
                - has_more: Whether there are more messages to fetch
                - page_token: Token to fetch the next page
        """
        try:
            url = f"{self._domain}/open-apis/im/v1/messages"
            headers = self._get_tenant_http_headers()

            params: Dict[str, Union[str, int]] = {
                "container_id_type": container_id_type,
                "container_id": container_id,
                "page_size": min(page_size, 50),
                "sort_type": sort_type,
            }
            if start_time:
                params["start_time"] = start_time
            if end_time:
                params["end_time"] = end_time
            if page_token:
                params["page_token"] = page_token

            response = requests.get(
                url, headers=headers, params=params, timeout=30
            )
            result = response.json()

            if result.get("code") != 0:
                logger.error(
                    f"Failed to get chat messages: {result.get('code')} - "
                    f"{result.get('msg')}"
                )
                return {
                    "error": (
                        "Failed to get chat messages: " f"{result.get('msg')}"
                    ),
                    "code": result.get("code"),
                }

            # Process and simplify messages
            data = result.get("data", {})
            items = data.get("items", [])
            return {
                "messages": self._process_message_items(items),
                "has_more": data.get("has_more", False),
                "page_token": data.get("page_token", ""),
            }

        except Exception as e:
            logger.error(f"Error getting chat messages: {e}")
            return {"error": f"Error getting chat messages: {e!s}"}

    def lark_send_message(
        self,
        receive_id: str,
        text: str,
        receive_id_type: Literal[
            "open_id", "user_id", "union_id", "email", "chat_id"
        ] = "chat_id",
    ) -> Dict[str, object]:
        r"""Sends a message to a user or chat. If send message to
        a chat, use lark_list_chats to get chat_id first, if send
        message to a user, need user provide open_id, user_id,
        union_id or email.

        Args:
            receive_id (str): The recipient identifier.
            text (str): The text message content.
            receive_id_type (str): The recipient ID type. Options:
                - "open_id"
                - "user_id"
                - "union_id"
                - "email"
                - "chat_id" (default)

        Returns:
            Dict[str, object]: A dictionary containing:
                - message_id: The sent message ID
                - chat_id: The chat ID the message belongs to
                - msg_type: Message type (text)
        """
        # NOTE: Currently supports plain text messages only.
        try:
            url = f"{self._domain}/open-apis/im/v1/messages"
            headers = self._get_tenant_http_headers()
            params = {"receive_id_type": receive_id_type}
            payload = {
                "receive_id": receive_id,
                "msg_type": "text",
                "content": json.dumps({"text": text}),
            }

            response = requests.post(
                url, headers=headers, params=params, json=payload, timeout=30
            )
            result = response.json()

            if result.get("code") != 0:
                logger.error(
                    f"Failed to send message: {result.get('code')} - "
                    f"{result.get('msg')}"
                )
                return {
                    "error": f"Failed to send message: {result.get('msg')}",
                    "code": result.get("code"),
                }

            data = result.get("data", {}) or {}
            return {
                "message_id": data.get("message_id"),
                "chat_id": data.get("chat_id"),
                "msg_type": data.get("msg_type"),
            }

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {"error": f"Error sending message: {e!s}"}

    def lark_get_message_resource(
        self,
        message_id: str,
        file_key: str,
        resource_type: Literal["image", "file"],
    ) -> Dict[str, object]:
        r"""Obtains resource files in messages, including audios, videos,
        images, and files. Emoji resources cannot be downloaded, and the
        resource files for download cannot exceed 100 MB.

        Args:
            message_id (str): The message ID containing the resource.
            file_key (str): The resource file key from message content.
            resource_type (str): Resource type, either "image" or "file".

        Returns:
            Dict[str, object]: A dictionary containing:
                - content_type: Response Content-Type header value
                - path: File path where content was saved
                - size: Content size in bytes
        """
        try:
            url = (
                f"{self._domain}/open-apis/im/v1/messages/"
                f"{message_id}/resources/{file_key}"
            )
            headers = self._get_tenant_http_headers()
            params = {"type": resource_type}

            response = requests.get(
                url, headers=headers, params=params, timeout=30
            )
            if response.status_code != 200:
                try:
                    result = response.json()
                except Exception:
                    result = {
                        "code": response.status_code,
                        "msg": "Failed to download message resource.",
                    }
                logger.error(
                    "Failed to download message resource: "
                    f"{response.status_code} - {result}"
                )
                return {
                    "error": "Failed to download message resource.",
                    "code": result.get("code", response.status_code),
                    "msg": result.get("msg"),
                }

            content = response.content or b""
            content_type = response.headers.get("Content-Type") or ""
            media_type = content_type.split(";", 1)[0].strip()
            extension = ""
            if "/" in media_type:
                extension = media_type.rsplit("/", 1)[1].strip().lower()
            filename = file_key
            if extension and not os.path.splitext(file_key)[1]:
                filename = f"{file_key}.{extension}"
            target_dir = os.path.join(self.working_dir, "lark_file")
            os.makedirs(target_dir, exist_ok=True)
            file_path = os.path.join(target_dir, filename)
            with open(file_path, "wb") as f:
                f.write(content)
            return {
                "content_type": content_type,
                "path": file_path,
                "size": len(content),
            }

        except Exception as e:
            logger.error(f"Error downloading message resource: {e}")
            return {"error": f"Error downloading message resource: {e!s}"}

    def lark_get_message_resource_key(
        self,
        message_id: str,
    ) -> Dict[str, object]:
        r"""Gets the resource key from a message's content.

        Args:
            message_id (str): The message ID to fetch.

        Returns:
            Dict[str, object]: A dictionary containing:
                - key: The resource key from message content
        """
        try:
            url = f"{self._domain}/open-apis/im/v1/messages/{message_id}"
            headers = self._get_tenant_http_headers()

            response = requests.get(url, headers=headers, timeout=30)
            result = response.json()

            if result.get("code") != 0:
                logger.error(
                    f"Failed to get message: {result.get('code')} - "
                    f"{result.get('msg')}"
                )
                return {
                    "error": f"Failed to get message: {result.get('msg')}",
                    "code": result.get("code"),
                }

            data = result.get("data", {}) or {}
            items = data.get("items", []) or []
            if not items:
                return {"error": "No message found."}
            # Get the first message item
            item = items[0]
            body = item.get("body", {}) or {}
            content = body.get("content", "")
            if not content:
                return {"error": "Message content is empty."}

            try:
                content_obj = json.loads(content)
            except json.JSONDecodeError:
                return {"error": "Message content is not valid JSON."}

            key = None
            for candidate in ("image_key", "file_key"):
                if candidate in content_obj:
                    key = content_obj.get(candidate)
                    break
            if key is None:
                for k in sorted(content_obj.keys()):
                    if k.endswith("_key"):
                        key = content_obj.get(k)
                        break

            if not key:
                return {"error": "No resource key found in message content."}

            return {"key": key}

        except Exception as e:
            logger.error(f"Error getting message resource key: {e}")
            return {"error": f"Error getting message resource key: {e!s}"}

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.lark_list_chats),
            FunctionTool(self.lark_get_chat_messages),
            FunctionTool(self.lark_send_message),
            FunctionTool(self.lark_get_message_resource),
            FunctionTool(self.lark_get_message_resource_key),
        ]
