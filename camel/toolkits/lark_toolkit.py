# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========

import json
import os
import time
from typing import Any, Dict, List, Literal, Optional

import requests

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, api_keys_required, dependencies_required

logger = get_logger(__name__)

# OAuth scopes for Lark API access
LARK_SCOPES = [
    "drive:drive",
    "drive:drive:readonly",
    "drive:file",
    "docx:document",
    "docx:document:readonly",
    "im:message",
    "im:message:readonly",
    "im:message.group_msg:readonly",
    "im:chat",
    "im:chat:readonly",
]

# Block type mappings for Lark documents
BLOCK_TYPES = {
    "text": 2,
    "heading1": 3,
    "heading2": 4,
    "heading3": 5,
    "heading4": 6,
    "heading5": 7,
    "heading6": 8,
    "heading7": 9,
    "heading8": 10,
    "heading9": 11,
    "bullet": 12,
    "ordered": 13,
    "code": 14,
    "quote": 15,
    "todo": 17,
    "divider": 22,
    "callout": 19,
}

# Token refresh buffer - refresh tokens this many seconds before expiry
TOKEN_REFRESH_BUFFER_SECONDS = 300  # 5 minutes


def _extract_text_from_element(element: Any) -> str:
    r"""Extracts plain text from a text element.

    Args:
        element: A text element object (dictionary from HTTP response).

    Returns:
        str: The plain text content.
    """
    # Handle dictionary responses from HTTP API
    if isinstance(element, dict):
        text_run = element.get("text_run")
        if text_run:
            return text_run.get("content", "")

        mention_user = element.get("mention_user")
        if mention_user:
            return f"@{mention_user.get('user_id', 'user')}"

        mention_doc = element.get("mention_doc")
        if mention_doc:
            return f"[Doc: {mention_doc.get('title', 'document')}]"

    return ""


def _extract_text_from_block(block: Any) -> str:
    r"""Extracts plain text from a block structure.

    Args:
        block: A Lark document block (dictionary from HTTP response).

    Returns:
        str: The extracted plain text content.
    """
    if not isinstance(block, dict):
        return ""

    block_type = block.get("block_type", 0)
    text_parts = []

    def _get_elements(content_obj: Any) -> list:
        r"""Helper to safely get elements from a content object."""
        if content_obj is None or not isinstance(content_obj, dict):
            return []
        return content_obj.get("elements", []) or []

    # Handle different block types
    if block_type == 1:  # Page block
        page = block.get("page", {})
        title = page.get("title", "") if page else ""
        text_parts.append(f"# {title}")
    elif block_type == 2:  # Text block
        text_content = block.get("text", {})
        elements = _get_elements(text_content)
        for elem in elements:
            text_parts.append(_extract_text_from_element(elem))
    elif 3 <= block_type <= 11:  # Heading blocks (1-9)
        heading_level = block_type - 2
        heading_content = block.get(f"heading{heading_level}", {})
        elements = _get_elements(heading_content)
        prefix = "#" * heading_level
        heading_text = "".join(
            _extract_text_from_element(elem) for elem in elements
        )
        text_parts.append(f"{prefix} {heading_text}")
    elif block_type == 12:  # Bullet list
        bullet_content = block.get("bullet", {})
        elements = _get_elements(bullet_content)
        bullet_text = "".join(
            _extract_text_from_element(elem) for elem in elements
        )
        text_parts.append(f"• {bullet_text}")
    elif block_type == 13:  # Ordered list
        ordered_content = block.get("ordered", {})
        elements = _get_elements(ordered_content)
        ordered_text = "".join(
            _extract_text_from_element(elem) for elem in elements
        )
        text_parts.append(f"1. {ordered_text}")
    elif block_type == 14:  # Code block
        code_content = block.get("code", {})
        elements = _get_elements(code_content)
        code_text = "".join(
            _extract_text_from_element(elem) for elem in elements
        )
        style = code_content.get("style", {}) if code_content else {}
        language = style.get("language", "") if style else ""
        text_parts.append(f"```{language}\n{code_text}\n```")
    elif block_type == 15:  # Quote block
        quote_content = block.get("quote", {})
        elements = _get_elements(quote_content)
        quote_text = "".join(
            _extract_text_from_element(elem) for elem in elements
        )
        text_parts.append(f"> {quote_text}")
    elif block_type == 17:  # Todo block
        todo_content = block.get("todo", {})
        elements = _get_elements(todo_content)
        style = todo_content.get("style", {}) if todo_content else {}
        done = style.get("done", False) if style else False
        todo_text = "".join(
            _extract_text_from_element(elem) for elem in elements
        )
        checkbox = "[x]" if done else "[ ]"
        text_parts.append(f"{checkbox} {todo_text}")
    elif block_type == 22:  # Divider
        text_parts.append("---")
    elif block_type == 19:  # Callout
        callout_content = block.get("callout", {})
        elements = _get_elements(callout_content)
        callout_text = "".join(
            _extract_text_from_element(elem) for elem in elements
        )
        text_parts.append(f"📌 {callout_text}")

    return "".join(text_parts)


@MCPServer()
class LarkToolkit(BaseToolkit):
    r"""A toolkit for Lark (Feishu) document operations.

    This toolkit provides methods to interact with the Lark Open Platform API
    for creating, reading, updating, and deleting documents and document
    blocks.

    Args:
        app_id (Optional[str]): The Lark application ID.
        app_secret (Optional[str]): The Lark application secret.
        use_feishu (bool): Whether to use Feishu (China) instead of Lark.
    """

    @api_keys_required(
        [
            ("app_id", "LARK_APP_ID"),
            ("app_secret", "LARK_APP_SECRET"),
        ]
    )
    @dependencies_required("lark_oapi")
    def __init__(
        self,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        use_feishu: bool = False,
        timeout: Optional[float] = None,
        user_access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        oauth_port: int = 9000,
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
            user_access_token (Optional[str]): Pre-existing user access token
                for OAuth authentication. If provided, API calls will be made
                as this user instead of as the application.
            refresh_token (Optional[str]): Pre-existing refresh token for
                refreshing the user access token.
            oauth_port (int): Port number for the local OAuth callback server.
                (default: :obj:`9000`)
        """
        super().__init__(timeout=timeout)
        import lark_oapi as lark

        self._app_id = app_id or os.environ.get("LARK_APP_ID", "")
        self._app_secret = app_secret or os.environ.get("LARK_APP_SECRET", "")
        self._use_feishu = use_feishu

        # Set domain based on region
        if use_feishu:
            self._domain = "https://open.feishu.cn"
            lark_domain = lark.FEISHU_DOMAIN
        else:
            self._domain = "https://open.larksuite.com"
            lark_domain = lark.LARK_DOMAIN

        # Build the client with automatic token management
        self._client = (
            lark.Client.builder()
            .app_id(self._app_id)
            .app_secret(self._app_secret)
            .domain(lark_domain)
            .build()
        )

        # Initialize OAuth-related attributes
        from pathlib import Path

        self._user_access_token = user_access_token
        self._refresh_token = refresh_token
        self._oauth_redirect_uri: Optional[str] = None
        self._token_file_path = str(Path.home() / '.camel' / 'lark_token.json')
        self._token_expires_at: Optional[float] = None
        self._oauth_port = oauth_port

        region = "Feishu (China)" if use_feishu else "Lark (International)"
        logger.info(f"LarkToolkit initialized for {region}")

        # Auto-authenticate: use provided token, cached token, or browser OAuth
        if user_access_token:
            logger.info("Using provided user access token")
        else:
            self._authenticate()

    # =========================================================================
    # OAuth / Authentication (Internal)
    # =========================================================================

    def _get_oauth_url(self, state: str = "") -> str:
        r"""Generate the OAuth authorization URL for user login.

        Args:
            state (str): Optional state parameter for CSRF protection.
                (default: :obj:`""`)

        Returns:
            str: The OAuth authorization URL.
        """
        from urllib.parse import quote

        if not self._oauth_redirect_uri:
            raise ValueError("oauth_redirect_uri must be set to use OAuth.")

        base = self._domain

        encoded_redirect = quote(self._oauth_redirect_uri, safe="")

        scopes = " ".join(LARK_SCOPES)
        encoded_scopes = quote(scopes, safe="")

        return (
            f"{base}/open-apis/authen/v1/authorize"
            f"?app_id={self._app_id}"
            f"&redirect_uri={encoded_redirect}"
            f"&scope={encoded_scopes}"
            f"&state={state}"
        )

    def _save_tokens_to_disk(self) -> None:
        r"""Save current tokens to disk cache."""
        if not self._token_file_path:
            return

        from pathlib import Path

        token_file = Path(self._token_file_path)
        token_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(token_file, 'w') as f:
                json.dump(
                    {
                        'user_access_token': self._user_access_token,
                        'refresh_token': self._refresh_token,
                        'expires_at': self._token_expires_at,
                    },
                    f,
                )
            os.chmod(token_file, 0o600)
            logger.info(f"Tokens saved to {token_file}")
        except Exception as e:
            logger.warning(f"Failed to save tokens: {e}")

    def clear_cached_tokens(self) -> bool:
        r"""Clears cached OAuth tokens from memory and disk.

        Use this method to force re-authentication on the next API call,
        or when switching users/accounts.

        Returns:
            bool: True if tokens were cleared successfully, False otherwise.

        """
        from pathlib import Path

        # Clear in-memory tokens
        self._user_access_token = None
        self._refresh_token = None
        self._token_expires_at = None

        # Delete cached token file
        if self._token_file_path:
            token_file = Path(self._token_file_path)
            if token_file.exists():
                try:
                    token_file.unlink()
                    logger.info(f"Deleted cached token file: {token_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete token file: {e}")
                    return False

        logger.info("Cleared cached OAuth tokens")
        return True

    def _exchange_code_for_token(self, code: str) -> None:
        r"""Exchange an authorization code for user access tokens.

        Args:
            code (str): The authorization code received from OAuth callback.

        Raises:
            RuntimeError: If the token exchange fails.
        """
        from lark_oapi.api.authen.v1 import (
            CreateOidcAccessTokenRequest,
            CreateOidcAccessTokenRequestBody,
        )

        request = (
            CreateOidcAccessTokenRequest.builder()
            .request_body(
                CreateOidcAccessTokenRequestBody.builder()
                .grant_type("authorization_code")
                .code(code)
                .build()
            )
            .build()
        )

        response = self._client.authen.v1.oidc_access_token.create(request)

        if not response.success():
            logger.error(
                f"Failed to exchange code for token: {response.code} - "
                f"{response.msg}"
            )
            raise RuntimeError(f"Failed to exchange code: {response.msg}")

        data = response.data
        self._user_access_token = data.access_token
        self._refresh_token = data.refresh_token
        self._token_expires_at = time.time() + data.expires_in

        self._save_tokens_to_disk()
        logger.info("Successfully obtained user access token via OAuth")

    def _refresh_user_token(self) -> None:
        r"""Refresh the user access token using the refresh token.

        Raises:
            ValueError: If no refresh token is available.
            RuntimeError: If the token refresh fails.
        """
        if not self._refresh_token:
            raise ValueError("No refresh token available.")

        from lark_oapi.api.authen.v1 import (
            CreateOidcRefreshAccessTokenRequest,
            CreateOidcRefreshAccessTokenRequestBody,
        )

        request = (
            CreateOidcRefreshAccessTokenRequest.builder()
            .request_body(
                CreateOidcRefreshAccessTokenRequestBody.builder()
                .grant_type("refresh_token")
                .refresh_token(self._refresh_token)
                .build()
            )
            .build()
        )

        response = self._client.authen.v1.oidc_refresh_access_token.create(
            request
        )

        if not response.success():
            logger.error(
                f"Failed to refresh token: {response.code} - "
                f"{response.msg}"
            )
            raise RuntimeError(f"Failed to refresh token: {response.msg}")

        data = response.data
        self._user_access_token = data.access_token
        self._refresh_token = data.refresh_token
        self._token_expires_at = time.time() + data.expires_in

        self._save_tokens_to_disk()
        logger.info("Successfully refreshed user access token")

    def _authenticate(
        self,
        timeout: int = 120,
    ) -> None:
        r"""Authenticate with Lark, using cached tokens if available.

        This method attempts authentication in the following order:
        1. Load cached tokens from disk
        2. If cached token is expired or near expiry, attempt to refresh it
        3. If no valid cached tokens, start browser OAuth flow

        Args:
            timeout (int): Timeout in seconds for browser OAuth flow.
                (default: :obj:`120`)

        Raises:
            RuntimeError: If authentication fails.
        """
        from pathlib import Path

        # Try to load cached tokens
        token_loaded = False
        if self._token_file_path:
            token_file = Path(self._token_file_path)
            if token_file.exists():
                try:
                    with open(token_file, 'r') as f:
                        data = json.load(f)

                    self._user_access_token = data.get('user_access_token')
                    self._refresh_token = data.get('refresh_token')
                    self._token_expires_at = data.get('expires_at')

                    if self._user_access_token and self._token_expires_at:
                        logger.info("Loaded cached Lark tokens")
                        token_loaded = True
                except Exception as e:
                    logger.warning(f"Failed to load cached tokens: {e}")

        if token_loaded and self._token_expires_at is not None:
            # Check if token is expired or will expire soon
            time_remaining = self._token_expires_at - time.time()
            if time_remaining < TOKEN_REFRESH_BUFFER_SECONDS:
                logger.info(
                    f"Token expires in {time_remaining:.0f}s, refreshing..."
                )
                if self._refresh_token:
                    try:
                        self._refresh_user_token()
                        logger.info("Successfully refreshed cached tokens")
                        return
                    except Exception as e:
                        logger.warning(f"Token refresh failed: {e}")
                        # Fall through to browser auth
            else:
                logger.info("Using cached access token")
                return

        logger.info("No valid cached tokens, starting browser authentication")
        self._run_browser_oauth(
            port=self._oauth_port, timeout=timeout, open_browser=True
        )

    def _run_browser_oauth(
        self,
        port: int = 9000,
        timeout: int = 120,
        open_browser: bool = True,
    ) -> None:
        r"""Run the browser-based OAuth flow.

        Args:
            port (int): Port number for the local OAuth callback server.
                (default: :obj:`9000`)
            timeout (int): Timeout in seconds for waiting for OAuth callback.
                (default: :obj:`120`)
            open_browser (bool): Whether to automatically open the browser.
                (default: :obj:`True`)

        Raises:
            TimeoutError: If authentication times out.
            RuntimeError: If OAuth callback fails or authorization is denied.
        """
        import secrets
        import socket
        import webbrowser
        from urllib.parse import parse_qs, urlparse

        redirect_uri = f"http://localhost:{port}/callback"
        self._oauth_redirect_uri = redirect_uri

        state = secrets.token_urlsafe(16)
        auth_url = self._get_oauth_url(state=state)

        if open_browser:
            logger.info("Opening browser for Lark authentication...")
            logger.info(f"If browser doesn't open, visit: {auth_url}")
            webbrowser.open(auth_url)
        else:
            logger.info(
                f"Open this URL in your browser to authenticate: {auth_url}"
            )

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.settimeout(timeout)

        try:
            server.bind(("localhost", port))
            server.listen(1)
            logger.info(
                f"Waiting for OAuth callback on port {port} "
                f"(timeout: {timeout}s)..."
            )

            conn, addr = server.accept()
            conn.settimeout(10)

            request_data = conn.recv(4096).decode("utf-8")

            first_line = request_data.split("\n")[0]
            path = first_line.split(" ")[1]
            query_params = parse_qs(urlparse(path).query)

            received_code = query_params.get("code", [None])[0]
            received_state = query_params.get("state", [None])[0]
            error = query_params.get("error", [None])[0]

            if error:
                response_body = f"Authentication failed: {error}"
                response = (
                    "HTTP/1.1 400 Bad Request\r\n"
                    "Content-Type: text/html; charset=utf-8\r\n"
                    f"Content-Length: {len(response_body)}\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                    f"{response_body}"
                )
            elif received_code:
                response_body = (
                    "Authentication successful! You can close this tab."
                )
                response = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/html; charset=utf-8\r\n"
                    f"Content-Length: {len(response_body)}\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                    f"{response_body}"
                )
            else:
                response_body = "No authorization code received."
                response = (
                    "HTTP/1.1 400 Bad Request\r\n"
                    "Content-Type: text/html; charset=utf-8\r\n"
                    f"Content-Length: {len(response_body)}\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                    f"{response_body}"
                )

            conn.send(response.encode("utf-8"))
            conn.close()

        except socket.timeout:
            server.close()
            raise TimeoutError(
                f"Authentication timed out after {timeout} seconds. "
                "Please try again."
            )
        except Exception as e:
            server.close()
            raise RuntimeError(f"OAuth callback failed: {e}")
        finally:
            server.close()

        if error:
            raise RuntimeError(f"OAuth authorization failed: {error}")

        if not received_code:
            raise RuntimeError("No authorization code received from Lark")

        if received_state != state:
            raise RuntimeError(
                "State mismatch - possible CSRF attack. Please try again."
            )

        logger.info("Exchanging authorization code for tokens...")
        self._exchange_code_for_token(received_code)
        logger.info("OAuth authentication completed successfully")

    # =========================================================================
    # HTTP Headers
    # =========================================================================

    def _get_http_headers(self) -> Dict[str, str]:
        r"""Get HTTP headers with user access token authorization.

        Requires user_access_token from OAuth flow. Use this for user
        operations like reading documents, listing files, etc.

        Automatically refreshes the token if it's expired or near expiry
        (within 5 minutes).

        Returns:
            Dict[str, str]: Headers dict with Content-Type and Authorization.

        Raises:
            ValueError: If user_access_token is not available.
        """
        if not self._user_access_token:
            raise ValueError(
                "user_access_token is required for this operation. "
                "Please authenticate using OAuth flow first."
            )

        # Auto-refresh if token is expired or near expiry
        if self._token_expires_at:
            time_remaining = self._token_expires_at - time.time()
            if time_remaining < TOKEN_REFRESH_BUFFER_SECONDS:
                try:
                    self._refresh_user_token()
                    logger.info("Auto-refreshed expired user token")
                except Exception as e:
                    logger.warning(f"Failed to auto-refresh token: {e}")
                    # Continue with current token, let API call fail if invalid

        return {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self._user_access_token}",
        }

    def _get_tenant_http_headers(self) -> Dict[str, str]:
        r"""Get HTTP headers with tenant access token authorization.

        Always uses tenant_access_token regardless of whether user_access_token
        is available. Use this for bot operations like sending messages.

        Returns:
            Dict[str, str]: Headers dict with Content-Type and Authorization.
        """
        from lark_oapi.api.auth.v3 import (
            InternalTenantAccessTokenRequest,
            InternalTenantAccessTokenRequestBody,
        )

        headers = {"Content-Type": "application/json; charset=utf-8"}

        # Get tenant access token using the SDK
        request = (
            InternalTenantAccessTokenRequest.builder()
            .request_body(
                InternalTenantAccessTokenRequestBody.builder()
                .app_id(self._app_id)
                .app_secret(self._app_secret)
                .build()
            )
            .build()
        )

        response = self._client.auth.v3.tenant_access_token.internal(request)

        if response.success():
            # Parse token from raw response
            raw_data = json.loads(response.raw.content.decode())
            token = raw_data.get("tenant_access_token")
            headers["Authorization"] = f"Bearer {token}"
        else:
            logger.error(
                f"Failed to get tenant access token: {response.code} - "
                f"{response.msg}"
            )
            raise RuntimeError(
                f"Failed to get tenant access token: {response.msg}"
            )

        return headers

    def lark_create_document(
        self,
        title: str,
        folder_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Creates a new Lark document.

        The document will be created in the specified folder, or in the user's
        root folder if no folder_token is provided. This ensures the document
        appears in the user's document list immediately.

        Args:
            title (str): The title of the document.
            folder_token (Optional[str]): The folder token where the document
                will be created. If not provided, automatically creates in the
                user's root folder so it appears in their document list.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - document_id: The unique identifier of the created document
                - title: The document title
                - url: The URL to access the document
                - revision_id: The revision ID of the document
                - folder_token: The folder where the document was created
        """
        try:
            url = f"{self._domain}/open-apis/docx/v1/documents"
            headers = self._get_http_headers()

            body: Dict[str, Any] = {"title": title}
            if folder_token:
                body["folder_token"] = folder_token

            response = requests.post(
                url, headers=headers, json=body, timeout=30
            )
            result = response.json()

            if result.get("code") != 0:
                logger.error(
                    f"Failed to create document: {result.get('code')} - "
                    f"{result.get('msg')}"
                )
                return {
                    "error": f"Failed to create document: {result.get('msg')}",
                    "code": result.get("code"),
                }

            doc = result.get("data", {}).get("document", {})
            base_url = "feishu.cn" if self._use_feishu else "larksuite.com"
            return {
                "document_id": doc.get("document_id"),
                "title": doc.get("title"),
                "revision_id": doc.get("revision_id"),
                "url": f"https://{base_url}/docx/{doc.get('document_id')}",
                "folder_token": folder_token,
            }

        except Exception as e:
            logger.error(f"Error creating document: {e}")
            return {"error": f"Error creating document: {e!s}"}

    def lark_get_document(
        self,
        document_id: str,
    ) -> Dict[str, Any]:
        r"""Gets metadata of a Lark document.

        Args:
            document_id (str): The unique identifier of the document.

        Returns:
            Dict[str, Any]: A dictionary containing document metadata:
                - document_id: The document ID
                - title: The document title
                - revision_id: Current revision ID
        """
        try:
            url = f"{self._domain}/open-apis/docx/v1/documents/{document_id}"
            headers = self._get_http_headers()

            response = requests.get(url, headers=headers, timeout=30)
            result = response.json()

            if result.get("code") != 0:
                logger.error(
                    f"Failed to get document: {result.get('code')} - "
                    f"{result.get('msg')}"
                )
                return {
                    "error": f"Failed to get document: {result.get('msg')}",
                    "code": result.get("code"),
                }

            doc = result.get("data", {}).get("document", {})
            return {
                "document_id": doc.get("document_id"),
                "title": doc.get("title"),
                "revision_id": doc.get("revision_id"),
            }

        except Exception as e:
            logger.error(f"Error getting document: {e}")
            return {"error": f"Error getting document: {e!s}"}

    def lark_get_document_content(
        self,
        document_id: str,
    ) -> Dict[str, Any]:
        r"""Gets the raw content of a Lark document as plain text.

        This method fetches all blocks in the document and extracts their
        text content, converting the document to a readable plain text format.

        Args:
            document_id (str): The unique identifier of the document.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - document_id: The document ID
                - content: The extracted plain text content
        """
        try:
            url = (
                f"{self._domain}/open-apis/docx/v1/documents/"
                f"{document_id}/raw_content"
            )
            headers = self._get_http_headers()

            response = requests.get(url, headers=headers, timeout=30)
            result = response.json()

            if result.get("code") != 0:
                logger.error(
                    f"Failed to get document content: {result.get('code')} - "
                    f"{result.get('msg')}"
                )
                return {
                    "error": f"Failed to get document content: "
                    f"{result.get('msg')}",
                    "code": result.get("code"),
                }

            return {
                "document_id": document_id,
                "content": result.get("data", {}).get("content", ""),
            }

        except Exception as e:
            logger.error(f"Error getting document content: {e}")
            return {"error": f"Error getting document content: {e!s}"}

    def lark_list_document_blocks(
        self,
        document_id: str,
        page_size: int = 50,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Lists all blocks in a Lark document.

        Args:
            document_id (str): The unique identifier of the document.
            page_size (int): Number of blocks to return per page (max 500).
                (default: :obj:`50`)
            page_token (Optional[str]): Token for pagination. Use the
                page_token from previous response to get next page.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - document_id: The document ID
                - blocks: List of block objects with type and content
                - has_more: Whether there are more blocks to fetch
                - page_token: Token to fetch the next page
        """
        try:
            url = (
                f"{self._domain}/open-apis/docx/v1/documents/"
                f"{document_id}/blocks"
            )
            headers = self._get_http_headers()

            params: Dict[str, Any] = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token

            response = requests.get(
                url, headers=headers, params=params, timeout=30
            )
            result = response.json()

            if result.get("code") != 0:
                logger.error(
                    f"Failed to list blocks: {result.get('code')} - "
                    f"{result.get('msg')}"
                )
                return {
                    "error": f"Failed to list blocks: {result.get('msg')}",
                    "code": result.get("code"),
                }

            data = result.get("data", {})
            blocks = []
            items = data.get("items", []) or []
            for block in items:
                block_info = {
                    "block_id": block.get("block_id"),
                    "block_type": block.get("block_type"),
                    "parent_id": block.get("parent_id"),
                }

                # Try to extract text content
                text_content = _extract_text_from_block(block)
                if text_content:
                    block_info["text_content"] = text_content

                blocks.append(block_info)

            return {
                "document_id": document_id,
                "blocks": blocks,
                "has_more": data.get("has_more", False),
                "page_token": data.get("page_token"),
            }

        except Exception as e:
            logger.error(f"Error listing blocks: {e}")
            return {"error": f"Error listing blocks: {e!s}"}

    def lark_get_block(
        self,
        document_id: str,
        block_id: str,
    ) -> Dict[str, Any]:
        r"""Gets a specific block from a Lark document.

        Args:
            document_id (str): The unique identifier of the document.
            block_id (str): The unique identifier of the block.

        Returns:
            Dict[str, Any]: A dictionary containing block information:
                - block_id: The block ID
                - block_type: The type of the block
                - parent_id: The parent block ID
                - children: List of child block IDs
                - text_content: Extracted text content (if applicable)
        """
        try:
            url = (
                f"{self._domain}/open-apis/docx/v1/documents/"
                f"{document_id}/blocks/{block_id}"
            )
            headers = self._get_http_headers()

            response = requests.get(url, headers=headers, timeout=30)
            result = response.json()

            if result.get("code") != 0:
                logger.error(
                    f"Failed to get block: {result.get('code')} - "
                    f"{result.get('msg')}"
                )
                return {
                    "error": f"Failed to get block: {result.get('msg')}",
                    "code": result.get("code"),
                }

            block = result.get("data", {}).get("block", {})
            block_info = {
                "block_id": block.get("block_id"),
                "block_type": block.get("block_type"),
                "parent_id": block.get("parent_id"),
                "children": block.get("children", []) or [],
            }

            # Try to extract text content
            text_content = _extract_text_from_block(block)
            if text_content:
                block_info["text_content"] = text_content

            return block_info

        except Exception as e:
            logger.error(f"Error getting block: {e}")
            return {"error": f"Error getting block: {e!s}"}

    def lark_get_block_children(
        self,
        document_id: str,
        block_id: str,
        page_size: int = 50,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Gets child blocks of a specific block.

        Args:
            document_id (str): The unique identifier of the document.
            block_id (str): The unique identifier of the parent block.
            page_size (int): Number of children to return per page (max 500).
                (default: :obj:`50`)
            page_token (Optional[str]): Token for pagination.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - block_id: The parent block ID
                - children: List of child block objects
                - has_more: Whether there are more children to fetch
                - page_token: Token to fetch the next page
        """
        try:
            url = (
                f"{self._domain}/open-apis/docx/v1/documents/"
                f"{document_id}/blocks/{block_id}/children"
            )
            headers = self._get_http_headers()

            params: Dict[str, Any] = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token

            response = requests.get(
                url, headers=headers, params=params, timeout=30
            )
            result = response.json()

            if result.get("code") != 0:
                logger.error(
                    f"Failed to get block children: {result.get('code')} - "
                    f"{result.get('msg')}"
                )
                return {
                    "error": f"Failed to get block children: "
                    f"{result.get('msg')}",
                    "code": result.get("code"),
                }

            data = result.get("data", {})
            children = []
            items = data.get("items", []) or []
            for block in items:
                block_info = {
                    "block_id": block.get("block_id"),
                    "block_type": block.get("block_type"),
                    "parent_id": block.get("parent_id"),
                }

                text_content = _extract_text_from_block(block)
                if text_content:
                    block_info["text_content"] = text_content

                children.append(block_info)

            return {
                "block_id": block_id,
                "children": children,
                "has_more": data.get("has_more", False),
                "page_token": data.get("page_token"),
            }

        except Exception as e:
            logger.error(f"Error getting block children: {e}")
            return {"error": f"Error getting block children: {e!s}"}

    def lark_create_block(
        self,
        document_id: str,
        block_type: Literal[
            "text",
            "heading",
            "bullet",
            "ordered",
            "code",
            "quote",
            "todo",
            "divider",
            "callout",
        ],
        content: Optional[str] = None,
        heading_level: Optional[int] = None,
        code_language: Optional[str] = None,
        todo_checked: Optional[bool] = None,
        parent_block_id: Optional[str] = None,
        index: int = -1,
    ) -> Dict[str, Any]:
        r"""Creates a new block in a Lark document.

        Args:
            document_id (str): The unique identifier of the document.
            block_type (str): The type of block to create. Supported types:
                text, heading, bullet, ordered, code, quote, todo, divider,
                callout.
            content (Optional[str]): The text content of the block. Required
                for all types except "divider".
            heading_level (Optional[int]): Heading level 1-9. Only used when
                block_type is "heading". Defaults to 1.
            code_language (Optional[str]): Programming language for syntax
                highlighting. Only used when block_type is "code".
            todo_checked (Optional[bool]): Whether the todo item is checked.
                Only used when block_type is "todo". Defaults to False.
            parent_block_id (Optional[str]): The parent block ID. If not
                provided, the block will be added to the document root.
            index (int): The position to insert the block. -1 means append
                at the end. (default: :obj:`-1`)

        Returns:
            Dict[str, Any]: A dictionary containing:
                - block_id: The ID of the created block
                - block_type: The type of the created block
                - document_revision_id: The new document revision ID
        """
        try:
            # Validate content requirement
            if block_type != "divider" and not content:
                return {
                    "error": "content is required for non-divider blocks",
                    "code": "INVALID_PARAMETER",
                }

            # Validate heading level
            if block_type == "heading":
                level = heading_level or 1
                if not 1 <= level <= 9:
                    return {
                        "error": "heading_level must be between 1 and 9",
                        "code": "INVALID_PARAMETER",
                    }
                actual_block_type = f"heading{level}"
            else:
                actual_block_type = block_type

            # Normalize index (LLM tool calls may pass None)
            if index is None:
                index = -1

            # Determine the parent block ID
            target_block_id = parent_block_id or document_id

            url = (
                f"{self._domain}/open-apis/docx/v1/documents/"
                f"{document_id}/blocks/{target_block_id}/children"
            )
            headers = self._get_http_headers()

            # Get the block type number
            block_type_num = BLOCK_TYPES.get(actual_block_type, 2)

            # Build the block based on type
            block: Dict[str, Any] = {"block_type": block_type_num}

            if block_type == "divider":
                block["divider"] = {}
            elif block_type == "callout":
                text_element = {"text_run": {"content": content or ""}}
                block["callout"] = {"elements": [text_element]}
            elif block_type == "code":
                text_element = {"text_run": {"content": content or ""}}
                code_obj: Dict[str, Any] = {"elements": [text_element]}
                if code_language:
                    code_obj["style"] = {"language": code_language}
                block["code"] = code_obj
            elif block_type == "todo":
                text_element = {"text_run": {"content": content or ""}}
                todo_obj: Dict[str, Any] = {"elements": [text_element]}
                if todo_checked is not None:
                    todo_obj["style"] = {"done": todo_checked}
                block["todo"] = todo_obj
            else:
                # For text, headings, bullet, ordered, quote
                text_element = {"text_run": {"content": content or ""}}
                text_obj = {"elements": [text_element]}
                block[actual_block_type] = text_obj

            # Build request body
            body: Dict[str, Any] = {"children": [block]}
            if index >= 0:
                body["index"] = index

            response = requests.post(
                url, headers=headers, json=body, timeout=30
            )
            result = response.json()

            if result.get("code") != 0:
                logger.error(
                    f"Failed to create block: {result.get('code')} - "
                    f"{result.get('msg')}"
                )
                return {
                    "error": f"Failed to create block: {result.get('msg')}",
                    "code": result.get("code"),
                }

            data = result.get("data", {})
            created_blocks = data.get("children", []) or []
            if created_blocks:
                return {
                    "block_id": created_blocks[0].get("block_id"),
                    "block_type": block_type,
                    "document_revision_id": data.get("document_revision_id"),
                }

            return {
                "document_revision_id": data.get("document_revision_id"),
            }

        except Exception as e:
            logger.error(f"Error creating block: {e}")
            return {"error": f"Error creating block: {e!s}"}

    def lark_update_block(
        self,
        document_id: str,
        block_id: str,
        content: str,
    ) -> Dict[str, Any]:
        r"""Updates the content of an existing block.

        Args:
            document_id (str): The unique identifier of the document.
            block_id (str): The unique identifier of the block to update.
            content (str): The new text content for the block.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - block_id: The ID of the updated block
                - document_revision_id: The new document revision ID
        """
        try:
            url = (
                f"{self._domain}/open-apis/docx/v1/documents/"
                f"{document_id}/blocks/{block_id}"
            )
            headers = self._get_http_headers()

            # Build the update request body
            body = {
                "update_text_elements": {
                    "elements": [{"text_run": {"content": content}}]
                }
            }

            response = requests.patch(
                url, headers=headers, json=body, timeout=30
            )
            result = response.json()

            if result.get("code") != 0:
                logger.error(
                    f"Failed to update block: {result.get('code')} - "
                    f"{result.get('msg')}"
                )
                return {
                    "error": f"Failed to update block: {result.get('msg')}",
                    "code": result.get("code"),
                }

            data = result.get("data", {})
            return {
                "block_id": block_id,
                "document_revision_id": data.get("document_revision_id"),
            }

        except Exception as e:
            logger.error(f"Error updating block: {e}")
            return {"error": f"Error updating block: {e!s}"}

    def lark_delete_block(
        self,
        document_id: str,
        block_id: str,
        parent_block_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Deletes a block from a Lark document.

        Args:
            document_id (str): The unique identifier of the document.
            block_id (str): The unique identifier of the block to delete.
            parent_block_id (Optional[str]): The parent block ID. If provided,
                skips an API call to look up the parent. Use this when you
                already know the parent from lark_list_document_blocks.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - block_id: The ID of the deleted block
                - document_revision_id: The new document revision ID
        """
        try:
            # Use provided parent_id or fetch it
            if parent_block_id:
                parent_id = parent_block_id
            else:
                block_info = self.lark_get_block(document_id, block_id)
                if "error" in block_info:
                    return block_info
                parent_id = block_info.get("parent_id", document_id)

            # Get the parent's children to find the index of our target block
            children_result = self.lark_get_block_children(
                document_id, parent_id
            )
            if "error" in children_result:
                return children_result

            # Find the index of the block we want to delete
            children = children_result.get("children", [])
            block_index = None
            for i, child in enumerate(children):
                if child.get("block_id") == block_id:
                    block_index = i
                    break

            if block_index is None:
                return {
                    "error": f"Block {block_id} not found in parent",
                    "code": "BLOCK_NOT_FOUND",
                }

            url = (
                f"{self._domain}/open-apis/docx/v1/documents/"
                f"{document_id}/blocks/{parent_id}/children/batch_delete"
            )
            headers = self._get_http_headers()

            # Use the correct index for the target block
            body = {"start_index": block_index, "end_index": block_index + 1}

            response = requests.delete(
                url, headers=headers, json=body, timeout=30
            )

            # Handle non-JSON responses
            try:
                result = response.json()
            except Exception as json_err:
                logger.error(
                    f"Failed to parse delete response: {json_err}, "
                    f"status={response.status_code}, "
                    f"body={response.text[:500]}"
                )
                return {
                    "error": (
                        f"Invalid response from API: {response.text[:200]}"
                    ),
                    "status_code": response.status_code,
                }

            if result.get("code") != 0:
                logger.error(
                    f"Failed to delete block: {result.get('code')} - "
                    f"{result.get('msg')}"
                )
                return {
                    "error": f"Failed to delete block: {result.get('msg')}",
                    "code": result.get("code"),
                }

            data = result.get("data", {})
            return {
                "block_id": block_id,
                "document_revision_id": data.get("document_revision_id"),
            }

        except Exception as e:
            logger.error(f"Error deleting block: {e}")
            return {"error": f"Error deleting block: {e!s}"}

    def lark_list_folder_contents(
        self,
        folder_token: Optional[str] = None,
        page_size: int = 50,
        page_token: Optional[str] = None,
        order_by: Literal[
            "EditedTime", "CreatedTime", "DeletedTime"
        ] = "EditedTime",
        direction: Literal["ASC", "DESC"] = "DESC",
    ) -> Dict[str, Any]:
        r"""Lists files and folders in a Lark Drive folder.

        Use this method to discover folder tokens for use with
        lark_create_document(). Files created via API don't appear in your
        document list until you either visit them or create them in a specific
        folder.

        Args:
            folder_token (Optional[str]): The folder token to list contents of.
                If not provided, lists the root folder contents.
            page_size (int): Number of items to return per page (max 200).
                (default: :obj:`50`)
            page_token (Optional[str]): Token for pagination. Use the
                page_token from previous response to get next page.
            order_by (str): Field to sort by. Options: "EditedTime",
                "CreatedTime", "DeletedTime". (default: :obj:`"EditedTime"`)
            direction (str): Sort direction. Options: "ASC", "DESC".
                (default: :obj:`"DESC"`)

        Returns:
            Dict[str, Any]: A dictionary containing:
                - files: List of file/folder objects with token, name, type
                - has_more: Whether there are more items to fetch
                - page_token: Token to fetch the next page
        """
        try:
            url = f"{self._domain}/open-apis/drive/v1/files"
            headers = self._get_http_headers()

            params: Dict[str, Any] = {
                "page_size": page_size,
                "order_by": order_by,
                "direction": direction,
            }
            if folder_token:
                params["folder_token"] = folder_token
            if page_token:
                params["page_token"] = page_token

            response = requests.get(
                url, headers=headers, params=params, timeout=30
            )
            result = response.json()

            if result.get("code") != 0:
                logger.error(
                    f"Failed to list folder contents: {result.get('code')} - "
                    f"{result.get('msg')}"
                )
                return {
                    "error": f"Failed to list folder contents: "
                    f"{result.get('msg')}",
                    "code": result.get("code"),
                }

            data = result.get("data", {})
            files = []
            file_list = data.get("files", []) or []
            for file in file_list:
                file_info = {
                    "token": file.get("token"),
                    "name": file.get("name"),
                    "type": file.get("type"),
                    "parent_token": file.get("parent_token"),
                    "created_time": file.get("created_time"),
                    "modified_time": file.get("modified_time"),
                    "owner_id": file.get("owner_id"),
                }

                # Add URL for easy access
                file_type = file.get("type")
                file_token = file.get("token")
                base_url = "feishu.cn" if self._use_feishu else "larksuite.com"
                if file_type == "folder":
                    file_info["url"] = (
                        f"https://{base_url}/drive/folder/{file_token}"
                    )
                elif file_type == "docx":
                    file_info["url"] = f"https://{base_url}/docx/{file_token}"
                elif file_type == "sheet":
                    file_info["url"] = (
                        f"https://{base_url}/sheets/{file_token}"
                    )
                elif file_type == "bitable":
                    file_info["url"] = f"https://{base_url}/base/{file_token}"

                files.append(file_info)

            return {
                "folder_token": folder_token or "root",
                "files": files,
                "has_more": data.get("has_more", False),
                "page_token": data.get("next_page_token"),
            }

        except Exception as e:
            logger.error(f"Error listing folder contents: {e}")
            return {"error": f"Error listing folder contents: {e!s}"}

    def lark_get_root_folder_token(self) -> Dict[str, Any]:
        r"""Gets the token of the user's root folder in Lark Drive.

        The root folder is the top-level "My Space" folder where you can
        create documents that will be visible in your document list.

        This method uses the dedicated Root Folder Meta API to get the
        authenticated user's personal root folder token. When using OAuth
        (user_access_token), this returns the USER's personal folder, not
        the app's folder.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - token: The root folder token
                - id: The folder ID
                - user_id: The folder owner's user ID
        """
        try:
            url = (
                f"{self._domain}/open-apis/drive/explorer/v2/root_folder/meta"
            )
            headers = self._get_http_headers()

            response = requests.get(url, headers=headers, timeout=30)
            result = response.json()

            if result.get("code") != 0:
                logger.error(
                    f"Failed to get root folder meta: {result.get('msg')}"
                )
                return {
                    "error": f"Failed to get root folder meta: "
                    f"{result.get('msg')}",
                    "code": result.get("code"),
                }

            data = result.get("data", {})
            token = data.get("token")
            folder_id = data.get("id")
            user_id = data.get("user_id")

            logger.info(
                f"Got root folder token: {token}, owner user_id: {user_id}"
            )

            return {
                "token": token,
                "id": folder_id,
                "user_id": user_id,
            }

        except Exception as e:
            logger.error(f"Error getting root folder: {e}")
            return {"error": f"Error getting root folder: {e!s}"}

    def lark_create_folder(
        self,
        name: str,
        folder_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Creates a new folder in Lark Drive.

        Args:
            name (str): The name of the folder to create.
            folder_token (Optional[str]): The parent folder token. If not
                provided, creates in the root folder.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - token: The token of the created folder
                - url: The URL to access the folder
        """
        try:
            # If no folder token provided, get the root folder
            parent_token = folder_token
            if not parent_token:
                root_result = self.lark_get_root_folder_token()
                if "error" in root_result:
                    return root_result
                parent_token = root_result["token"]

            url = f"{self._domain}/open-apis/drive/v1/files/create_folder"
            headers = self._get_http_headers()

            body = {"name": name, "folder_token": parent_token}

            response = requests.post(
                url, headers=headers, json=body, timeout=30
            )
            result = response.json()

            if result.get("code") != 0:
                logger.error(
                    f"Failed to create folder: {result.get('code')} - "
                    f"{result.get('msg')}"
                )
                return {
                    "error": f"Failed to create folder: {result.get('msg')}",
                    "code": result.get("code"),
                }

            data = result.get("data", {})
            return {
                "token": data.get("token"),
                "url": data.get("url"),
            }

        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            return {"error": f"Error creating folder: {e!s}"}

    def lark_send_message(
        self,
        receive_id: str,
        content: str,
        receive_id_type: Literal[
            "open_id", "user_id", "union_id", "email", "chat_id"
        ] = "open_id",
    ) -> Dict[str, Any]:
        r"""Sends a text message to a user or group chat.

        Use this method to send direct messages (DMs) to individual users or
        messages to group chats. For DMs, use the user's open_id, user_id,
        union_id, or email. For group messages, use the chat_id.

        Args:
            receive_id (str): The recipient identifier. This can be a user ID
                (for DMs) or a chat ID (for group messages).
            content (str): The text message content to send.
            receive_id_type (str): The type of receive_id being used:
                - "open_id": User's open ID (default, recommended for DMs)
                - "user_id": User's user ID
                - "union_id": User's union ID (for cross-app identification)
                - "email": User's email address
                - "chat_id": Group chat ID (for group messages)

        Returns:
            Dict[str, Any]: A dictionary containing:
                - message_id: The unique identifier of the sent message
                - chat_id: The chat ID where the message was sent
                - create_time: Timestamp when the message was created
        """

        try:
            url = f"{self._domain}/open-apis/im/v1/messages"
            headers = self._get_tenant_http_headers()
            params = {"receive_id_type": receive_id_type}

            body = {
                "receive_id": receive_id,
                "msg_type": "text",
                "content": json.dumps({"text": content}),
            }

            response = requests.post(
                url, headers=headers, params=params, json=body, timeout=30
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

            data = result.get("data", {})
            return {
                "message_id": data.get("message_id"),
                "chat_id": data.get("chat_id"),
                "create_time": data.get("create_time"),
            }

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return {"error": f"Error sending message: {e!s}"}

    def lark_list_chats(
        self,
        page_size: int = 50,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Lists chats and groups that the user belongs to.

        Use this method to discover available chats and obtain chat_id values
        for sending group messages with lark_send_message().

        Args:
            page_size (int): Number of chats to return per page (max 100).
                (default: :obj:`50`)
            page_token (Optional[str]): Token for pagination. Use the
                page_token from previous response to get next page.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - items: List of chat objects with chat_id, name, avatar,
                    owner_id, chat_type (p2p or group)
                - has_more: Whether there are more chats to fetch
                - page_token: Token to fetch the next page
        """
        try:
            url = f"{self._domain}/open-apis/im/v1/chats"
            headers = self._get_tenant_http_headers()

            params: Dict[str, Any] = {"page_size": page_size}
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

            data = result.get("data", {})
            items = []
            chat_list = data.get("items", []) or []
            for chat in chat_list:
                chat_info = {
                    "chat_id": chat.get("chat_id"),
                    "name": chat.get("name"),
                    "avatar": chat.get("avatar"),
                    "owner_id": chat.get("owner_id"),
                    "chat_type": chat.get("chat_type"),
                    "description": chat.get("description"),
                }
                items.append(chat_info)

            return {
                "items": items,
                "has_more": data.get("has_more", False),
                "page_token": data.get("page_token"),
            }

        except Exception as e:
            logger.error(f"Error listing chats: {e}")
            return {"error": f"Error listing chats: {e!s}"}

    def lark_get_chat(
        self,
        chat_id: str,
    ) -> Dict[str, Any]:
        r"""Gets detailed information about a specific chat.

        Args:
            chat_id (str): The unique identifier of the chat.

        Returns:
            Dict[str, Any]: A dictionary containing chat details:
                - chat_id: The chat ID
                - name: The chat name
                - description: The chat description
                - owner_id: The owner's user ID
                - chat_type: Type of chat (p2p or group)
                - member_count: Number of members in the chat
                - avatar: Chat avatar URL
        """
        try:
            url = f"{self._domain}/open-apis/im/v1/chats/{chat_id}"
            headers = self._get_tenant_http_headers()

            response = requests.get(url, headers=headers, timeout=30)
            result = response.json()

            if result.get("code") != 0:
                logger.error(
                    f"Failed to get chat: {result.get('code')} - "
                    f"{result.get('msg')}"
                )
                return {
                    "error": f"Failed to get chat: {result.get('msg')}",
                    "code": result.get("code"),
                }

            data = result.get("data", {})
            return {
                "chat_id": data.get("chat_id"),
                "name": data.get("name"),
                "description": data.get("description"),
                "owner_id": data.get("owner_id"),
                "chat_type": data.get("chat_type"),
                "member_count": data.get("user_count"),
                "avatar": data.get("avatar"),
            }

        except Exception as e:
            logger.error(f"Error getting chat: {e}")
            return {"error": f"Error getting chat: {e!s}"}

    def lark_get_chat_messages(
        self,
        container_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        sort_type: Literal[
            "ByCreateTimeAsc", "ByCreateTimeDesc"
        ] = "ByCreateTimeDesc",
        page_size: int = 50,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Gets message history from a chat with optional time filtering.

        Retrieves messages from a specific chat. Requires the bot to be a
        member of the chat.

        Args:
            container_id (str): The chat ID to retrieve messages from.
            start_time (Optional[str]): Start time filter (Unix timestamp in
                seconds, e.g., "1609459200"). Messages created after this time.
            end_time (Optional[str]): End time filter (Unix timestamp in
                seconds). Messages created before this time.
            sort_type (str): Sort order for messages. Options:
                - "ByCreateTimeAsc": Oldest first
                - "ByCreateTimeDesc": Newest first (default)
            page_size (int): Number of messages to return per page (max 50).
                (default: :obj:`50`)
            page_token (Optional[str]): Token for pagination. Use the
                page_token from previous response to get next page.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - items: List of message objects with message_id, msg_type,
                    content, sender_id, sender_type, create_time, chat_id
                - has_more: Whether there are more messages to fetch
                - page_token: Token to fetch the next page
        """
        try:
            url = f"{self._domain}/open-apis/im/v1/messages"
            headers = self._get_tenant_http_headers()

            params: Dict[str, Any] = {
                "container_id_type": "chat",
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
                    "error": f"Failed to get messages: {result.get('msg')}",
                    "code": result.get("code"),
                }

            data = result.get("data", {})
            items = []
            message_list = data.get("items", []) or []
            for msg in message_list:
                # Extract sender info
                sender = msg.get("sender", {})
                sender_id = sender.get("id") if sender else None

                # Parse message content
                content = msg.get("body", {}).get("content", "")

                msg_info = {
                    "message_id": msg.get("message_id"),
                    "msg_type": msg.get("msg_type"),
                    "content": content,
                    "sender_id": sender_id,
                    "sender_type": sender.get("sender_type")
                    if sender
                    else None,
                    "create_time": msg.get("create_time"),
                    "chat_id": msg.get("chat_id"),
                }
                items.append(msg_info)

            return {
                "items": items,
                "has_more": data.get("has_more", False),
                "page_token": data.get("page_token"),
            }

        except Exception as e:
            logger.error(f"Error getting chat messages: {e}")
            return {"error": f"Error getting chat messages: {e!s}"}

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            FunctionTool(self.lark_get_root_folder_token),
            FunctionTool(self.lark_list_folder_contents),
            FunctionTool(self.lark_create_folder),
            FunctionTool(self.lark_create_document),
            FunctionTool(self.lark_get_document),
            FunctionTool(self.lark_get_document_content),
            FunctionTool(self.lark_list_document_blocks),
            FunctionTool(self.lark_get_block),
            FunctionTool(self.lark_get_block_children),
            FunctionTool(self.lark_create_block),
            FunctionTool(self.lark_update_block),
            FunctionTool(self.lark_delete_block),
            FunctionTool(self.lark_send_message),
            FunctionTool(self.lark_list_chats),
            FunctionTool(self.lark_get_chat),
            FunctionTool(self.lark_get_chat_messages),
        ]
