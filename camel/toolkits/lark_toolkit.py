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
from typing import Dict, List, Literal, Optional, Union

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
                - code: Error code, 0 indicates success
                - msg: Error description
                - data: Response payload including:
                    - items: list_chat[]
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

            return result

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
                - code: Error code, 0 indicates success
                - msg: Error description
                - data: Response payload including:
                    - items: message[]
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

            return result

        except Exception as e:
            logger.error(f"Error getting chat messages: {e}")
            return {"error": f"Error getting chat messages: {e!s}"}

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
            body = data.get("body", {}) or {}
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
            FunctionTool(self.lark_get_message_resource),
            FunctionTool(self.lark_get_message_resource_key),
        ]
