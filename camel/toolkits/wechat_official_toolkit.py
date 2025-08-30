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
import time
from typing import Any, Dict, List, Optional

import requests

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, api_keys_required, retry_on_error

logger = get_logger(__name__)

# Global variables for caching access token
_wechat_access_token = None
_wechat_access_token_expires_at = 0


@retry_on_error()
def _get_wechat_access_token() -> str:
    r"""Retrieves or refreshes the WeChat Official Account access token.

    Returns:
        str: The valid access token.
    
    Raises:
        ValueError: If credentials are missing or token retrieval fails.
    
    References:
        https://developers.weixin.qq.com/doc/offiaccount/Basic_Information/Get_access_token.html
    """
    global _wechat_access_token, _wechat_access_token_expires_at
    
    if _wechat_access_token and _wechat_access_token_expires_at > time.time():
        return _wechat_access_token

    app_id = os.environ.get("WECHAT_APP_ID", "")
    app_secret = os.environ.get("WECHAT_APP_SECRET", "")
    
    if not app_id or not app_secret:
        raise ValueError(
            "WeChat credentials missing. Set WECHAT_APP_ID and WECHAT_APP_SECRET."
        )

    url = (
        "https://api.weixin.qq.com/cgi-bin/token?"
        f"grant_type=client_credential&appid={app_id}&secret={app_secret}"
    )
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    if "access_token" in data:
        _wechat_access_token = data["access_token"]
        _wechat_access_token_expires_at = time.time() + data.get("expires_in", 7200) - 60
        logger.info("WeChat access token refreshed.")
        return _wechat_access_token
    else:
        raise ValueError(f"Failed to get access token: {data.get('errmsg', 'Unknown error')}")

def _make_wechat_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    r"""Makes a request to WeChat API with proper error handling.
    
    Args:
        method (str): HTTP method ('GET' or 'POST').
        endpoint (str): API endpoint path.
        **kwargs: Additional arguments for requests.
        
    Returns:
        Dict[str, Any]: API response data.
        
    Raises:
        requests.exceptions.RequestException: If request fails.
        ValueError: If API returns an error.
    """
    global _wechat_access_token, _wechat_access_token_expires_at
    access_token = _get_wechat_access_token()
    
    # Handle URL parameter concatenation
    separator = "&" if "?" in endpoint else "?"
    url = f"https://api.weixin.qq.com{endpoint}{separator}access_token={access_token}"
    
    if method.upper() == "GET":
        response = requests.get(url, **kwargs)
    else:
        response = requests.post(url, **kwargs)
    
    response.raise_for_status()
    data = response.json()
    
    if data.get("errcode") and data.get("errcode") != 0:
        raise ValueError(f"WeChat API error: {data.get('errmsg', 'Unknown error')}")
    
    return data

@api_keys_required([(None, "WECHAT_APP_ID"), (None, "WECHAT_APP_SECRET")])
def send_wechat_customer_message(openid: str, content: str, msgtype: str = "text") -> str:
    r"""Sends a customer service message to a WeChat user.

    Args:
        openid (str): The user's OpenID.
        content (str): Message content or media_id for non-text messages.
        msgtype (str): Message type: "text", "image", "voice", "video". 
                      (default: "text")

    Returns:
        str: Success or error message.

    References:
        https://developers.weixin.qq.com/doc/offiaccount/Message_Management/Service_Center_messages.html
    """
    payload: Dict[str, Any] = {"touser": openid, "msgtype": msgtype}
    
    if msgtype == "text":
        payload["text"] = {"content": content}
    elif msgtype in ["image", "voice"]:
        payload[msgtype] = {"media_id": content}
    elif msgtype == "video":
        parts = content.split(",", 2)
        payload["video"] = {
            "media_id": parts[0],
            "title": parts[1] if len(parts) > 1 else "",
            "description": parts[2] if len(parts) > 2 else "",
        }
    else:
        return f"Unsupported message type: {msgtype}"

    try:
        _make_wechat_request("POST", "/cgi-bin/message/custom/send", 
                           headers={"Content-Type": "application/json"}, json=payload)
        return f"Message sent successfully to {openid}."
    except Exception as e:
        return f"Failed to send message: {e!s}"

@api_keys_required([(None, "WECHAT_APP_ID"), (None, "WECHAT_APP_SECRET")])
def get_wechat_user_info(openid: str, lang: str = "zh_CN") -> str:
    r"""Retrieves WeChat user information.

    Args:
        openid (str): The user's OpenID.
        lang (str): Response language: "zh_CN", "zh_TW", "en". (default: "zh_CN")

    Returns:
        str: User information as JSON string or error message.
        
    References:
        https://developers.weixin.qq.com/doc/offiaccount/User_Management/Getting_user_basic_information.html
    """
    try:
        data = _make_wechat_request("GET", f"/cgi-bin/user/info?openid={openid}&lang={lang}")
        return data
    except Exception as e:
        return f"Failed to get user info for {openid}: {e!s}"

@api_keys_required([(None, "WECHAT_APP_ID"), (None, "WECHAT_APP_SECRET")])
def get_wechat_followers_list(next_openid: str = "") -> str:
    r"""Retrieves list of followers' OpenIDs.

    Args:
        next_openid (str): Starting OpenID for pagination. (default: "")

    Returns:
        str: Followers list as JSON string or error message.
        
    References:
        https://developers.weixin.qq.com/doc/offiaccount/User_Management/Getting_a_list_of_followers.html
    """
    try:
        endpoint = "/cgi-bin/user/get"
        if next_openid:
            endpoint += f"?next_openid={next_openid}"
        data = _make_wechat_request("GET", endpoint)
        return data
    except Exception as e:
        return f"Failed to get followers list: {e!s}"

@api_keys_required([(None, "WECHAT_APP_ID"), (None, "WECHAT_APP_SECRET")])
def upload_wechat_media(media_type: str, file_path: str, permanent: bool = False, 
                       description: Optional[str] = None) -> str:
    r"""Uploads media file to WeChat.

    Args:
        media_type (str): Media type: "image", "voice", "video", "thumb".
        file_path (str): Local file path.
        permanent (bool): Whether to upload as permanent media. (default: False)
        description (Optional[str]): Video description in JSON format for permanent upload.

    Returns:
        str: Upload result with media_id or error message.
        
    References:
        - Temporary: https://developers.weixin.qq.com/doc/offiaccount/Asset_Management/Adding_Temporary_Assets.html
        - Permanent: https://developers.weixin.qq.com/doc/offiaccount/Asset_Management/Adding_Permanent_Assets.html
    """
    try:
        if permanent:
            endpoint = f"/cgi-bin/material/add_material?type={media_type}"
            files = {"media": open(file_path, "rb")}
            data_payload = {}
            
            if media_type == "video" and description:
                data_payload["description"] = description
                files["description"] = (None, description)
                
            data = _make_wechat_request("POST", endpoint, files=files, data=data_payload)
            files["media"].close()
        else:
            endpoint = f"/cgi-bin/media/upload?type={media_type}"
            with open(file_path, "rb") as f:
                files = {"media": f}
                data = _make_wechat_request("POST", endpoint, files=files)
        
        return str(data)
    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as e:
        return f"Failed to upload media: {e!s}"


@api_keys_required([(None, "WECHAT_APP_ID"), (None, "WECHAT_APP_SECRET")])
def get_wechat_media_list(media_type: str, offset: int = 0, count: int = 20) -> str:
    r"""Gets list of permanent media files.

    Args:
        media_type (str): Media type: "image", "voice", "video", "news".
        offset (int): Starting position. (default: 0)
        count (int): Number of items (1-20). (default: 20)

    Returns:
        str: Media list as JSON string or error message.
        
    References:
        https://developers.weixin.qq.com/doc/offiaccount/Asset_Management/Get_the_list_of_all_materials.html
    """
    try:
        payload = {"type": media_type, "offset": offset, "count": count}
        data = _make_wechat_request("POST", "/cgi-bin/material/batchget_material",
                                  headers={"Content-Type": "application/json"}, json=payload)
        return str(data)
    except Exception as e:
        return f"Failed to get media list: {e!s}"

@MCPServer()
class WeChatOfficialToolkit(BaseToolkit):
    r"""A toolkit for WeChat Official Account operations.

    This toolkit provides methods to interact with the WeChat Official Account API,
    allowing users to send messages, manage users, and handle media files.

    References:
        - Documentation: https://developers.weixin.qq.com/doc/offiaccount/Getting_Started/Overview.html
        - Test Account: https://mp.weixin.qq.com/debug/cgi-bin/sandbox?t=sandbox/login

    Notes:
        Set environment variables: WECHAT_APP_ID, WECHAT_APP_SECRET
    """

    def __init__(self, timeout: Optional[float] = None):
        r"""Initializes the WeChatOfficialToolkit."""
        super().__init__(timeout=timeout)
        self.base_url = "https://api.weixin.qq.com"
        
        # Validate credentials
        app_id = os.environ.get("WECHAT_APP_ID", "")
        app_secret = os.environ.get("WECHAT_APP_SECRET", "")
        
        if not all([app_id, app_secret]):
            raise ValueError(
                "WeChat credentials missing. Set WECHAT_APP_ID and WECHAT_APP_SECRET."
            )

    def send_customer_message(self, openid: str, content: str, msgtype: str = "text") -> str:
        r"""Sends a customer service message."""
        return send_wechat_customer_message(openid, content, msgtype)

    def get_user_info(self, openid: str, lang: str = "zh_CN") -> str:
        r"""Gets user information."""
        return get_wechat_user_info(openid, lang)

    def get_followers_list(self, next_openid: str = "") -> str:
        r"""Gets followers list."""
        return get_wechat_followers_list(next_openid)

    def upload_temporary_media(self, media_type: str, file_path: str) -> str:
        r"""Uploads temporary media."""
        return upload_wechat_media(media_type, file_path, permanent=False)

    def upload_permanent_media(self, media_type: str, file_path: str, 
                             description: Optional[str] = None) -> str:
        r"""Uploads permanent media."""
        return upload_wechat_media(media_type, file_path, permanent=True, description=description)

    def get_media_list(self, media_type: str, offset: int = 0, count: int = 20) -> str:
        r"""Gets media list."""
        return get_wechat_media_list(media_type, offset, count)

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns toolkit functions as tools."""
        return [
            FunctionTool(self.send_customer_message),
            FunctionTool(self.get_user_info),
            FunctionTool(self.get_followers_list),
            FunctionTool(self.upload_temporary_media),
            FunctionTool(self.upload_permanent_media),
            FunctionTool(self.get_media_list),
        ]