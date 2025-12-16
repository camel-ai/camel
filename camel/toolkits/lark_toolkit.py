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

import os
from typing import Any, Callable, Dict, List, Literal, Optional
from urllib.parse import quote

from typing_extensions import TypedDict

from camel.logger import get_logger
from camel.toolkits import FunctionTool
from camel.toolkits.base import BaseToolkit
from camel.utils import MCPServer, api_keys_required, dependencies_required

logger = get_logger(__name__)

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


class BlockOperation(TypedDict, total=False):
    r"""Type definition for batch block operations.

    This TypedDict defines the structure for operations passed to
    lark_batch_update_blocks. Using TypedDict ensures OpenAI's function
    calling schema validation passes (requires additionalProperties: false).

    Attributes:
        action: The operation type - "create", "update", or "delete".
        block_id: The block ID (required for "update" and "delete").
        block_type: The block type (required for "create").
        content: The text content (required for "create" and "update").
        parent_block_id: Optional parent block ID (for "create").
    """

    action: Literal["create", "update", "delete"]
    block_id: str
    block_type: Literal[
        "text",
        "heading1",
        "heading2",
        "heading3",
        "heading4",
        "heading5",
        "heading6",
        "heading7",
        "heading8",
        "heading9",
        "bullet",
        "ordered",
        "code",
        "quote",
        "todo",
        "divider",
        "callout",
    ]
    content: str
    parent_block_id: str


def _extract_text_from_element(element: Any) -> str:
    r"""Extracts plain text from a text element.

    Args:
        element: A text element object (Lark SDK object or dictionary).

    Returns:
        str: The plain text content.
    """
    # Handle Lark SDK objects using getattr
    text_run = getattr(element, "text_run", None)
    if text_run is not None:
        content = getattr(text_run, "content", "")
        return content if content else ""

    mention_user = getattr(element, "mention_user", None)
    if mention_user is not None:
        user_id = getattr(mention_user, "user_id", "user")
        return f"@{user_id}"

    mention_doc = getattr(element, "mention_doc", None)
    if mention_doc is not None:
        title = getattr(mention_doc, "title", "document")
        return f"[Doc: {title}]"

    return ""


def _extract_text_from_block(block: Any) -> str:
    r"""Extracts plain text from a block structure.

    Args:
        block: A Lark document block (SDK object or dictionary).

    Returns:
        str: The extracted plain text content.
    """
    block_type = getattr(block, "block_type", 0)
    text_parts = []

    def _get_elements(content_obj: Any) -> list:
        """Helper to safely get elements from a content object."""
        if content_obj is None:
            return []
        elements = getattr(content_obj, "elements", None)
        return elements if elements else []

    # Handle different block types
    if block_type == 1:  # Page block
        page = getattr(block, "page", None)
        title = getattr(page, "title", "") if page else ""
        text_parts.append(f"# {title}")
    elif block_type == 2:  # Text block
        text_content = getattr(block, "text", None)
        elements = _get_elements(text_content)
        for elem in elements:
            text_parts.append(_extract_text_from_element(elem))
    elif 3 <= block_type <= 11:  # Heading blocks (1-9)
        heading_level = block_type - 2
        heading_content = getattr(block, f"heading{heading_level}", None)
        elements = _get_elements(heading_content)
        prefix = "#" * heading_level
        heading_text = "".join(
            _extract_text_from_element(elem) for elem in elements
        )
        text_parts.append(f"{prefix} {heading_text}")
    elif block_type == 12:  # Bullet list
        bullet_content = getattr(block, "bullet", None)
        elements = _get_elements(bullet_content)
        bullet_text = "".join(
            _extract_text_from_element(elem) for elem in elements
        )
        text_parts.append(f"• {bullet_text}")
    elif block_type == 13:  # Ordered list
        ordered_content = getattr(block, "ordered", None)
        elements = _get_elements(ordered_content)
        ordered_text = "".join(
            _extract_text_from_element(elem) for elem in elements
        )
        text_parts.append(f"1. {ordered_text}")
    elif block_type == 14:  # Code block
        code_content = getattr(block, "code", None)
        elements = _get_elements(code_content)
        code_text = "".join(
            _extract_text_from_element(elem) for elem in elements
        )
        style = getattr(code_content, "style", None) if code_content else None
        language = getattr(style, "language", "") if style else ""
        text_parts.append(f"```{language}\n{code_text}\n```")
    elif block_type == 15:  # Quote block
        quote_content = getattr(block, "quote", None)
        elements = _get_elements(quote_content)
        quote_text = "".join(
            _extract_text_from_element(elem) for elem in elements
        )
        text_parts.append(f"> {quote_text}")
    elif block_type == 17:  # Todo block
        todo_content = getattr(block, "todo", None)
        elements = _get_elements(todo_content)
        style = getattr(todo_content, "style", None) if todo_content else None
        done = getattr(style, "done", False) if style else False
        todo_text = "".join(
            _extract_text_from_element(elem) for elem in elements
        )
        checkbox = "[x]" if done else "[ ]"
        text_parts.append(f"{checkbox} {todo_text}")
    elif block_type == 22:  # Divider
        text_parts.append("---")
    elif block_type == 19:  # Callout
        callout_content = getattr(block, "callout", None)
        elements = _get_elements(callout_content)
        callout_text = "".join(
            _extract_text_from_element(elem) for elem in elements
        )
        text_parts.append(f"📌 {callout_text}")

    return "".join(text_parts)


# ============================================================================
# OAUTH MIXIN - Remove this section if OAuth support is not needed
# ============================================================================


class LarkOAuthMixin:
    r"""Mixin class providing OAuth (User Access Token) support for Lark.

    This mixin adds the ability to authenticate as a specific user rather than
    as the application. When a user_access_token is set, API calls will be made
    with that user's identity and permissions.

    To remove OAuth support, simply:
    1. Remove this entire LarkOAuthMixin class
    2. Remove LarkOAuthMixin from LarkToolkit's parent classes
    3. Remove OAuth-related parameters from LarkToolkit.__init__
    4. Remove the _get_request_option method override

    Attributes:
        _user_access_token (Optional[str]): The current user access token.
        _refresh_token (Optional[str]): Token used to refresh the access token.
        _oauth_redirect_uri (Optional[str]): Redirect URI for OAuth flow.
        _on_token_refresh (Optional[Callable]): Callback when tokens are
            refreshed.
    """

    _user_access_token: Optional[str] = None
    _refresh_token: Optional[str] = None
    _oauth_redirect_uri: Optional[str] = None
    _on_token_refresh: Optional[Callable[[str, str], None]] = None
    _app_id: str  # Type hint for app_id from main class
    _client: Any  # Type hint for the Lark client from main class
    _domain: str  # Type hint for domain from main class

    def _init_oauth(
        self,
        user_access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        oauth_redirect_uri: Optional[str] = None,
        on_token_refresh: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        r"""Initialize OAuth-related attributes.

        Args:
            user_access_token (Optional[str]): Pre-existing user access token.
            refresh_token (Optional[str]): Pre-existing refresh token.
            oauth_redirect_uri (Optional[str]): Redirect URI registered in
                your Lark app for OAuth callbacks.
            on_token_refresh (Optional[Callable[[str, str], None]]): Callback
                function called when tokens are refreshed. Receives
                (access_token, refresh_token) as arguments. Use this to
                persist tokens.
        """
        self._user_access_token = user_access_token
        self._refresh_token = refresh_token
        self._oauth_redirect_uri = oauth_redirect_uri
        self._on_token_refresh = on_token_refresh

    def _get_request_option(self) -> Any:
        r"""Get request options with user access token if available.

        Returns:
            RequestOption with user_access_token set, or None if not using
            OAuth.
        """
        if self._user_access_token:
            import lark_oapi as lark

            return (
                lark.RequestOption.builder()
                .user_access_token(self._user_access_token)
                .build()
            )
        return None

    def get_oauth_url(self, state: str = "") -> str:
        r"""Generate the OAuth authorization URL for user login.

        Direct the user to this URL to initiate the OAuth flow. After the user
        logs in and grants permission, they will be redirected to your
        oauth_redirect_uri with an authorization code.

        Args:
            state (str): Optional state parameter to maintain request context
                and prevent CSRF attacks. This value will be returned in the
                callback. (default: "")

        Returns:
            str: The authorization URL to redirect the user to.

        Raises:
            ValueError: If oauth_redirect_uri is not configured.

        Example:
            >>> toolkit = LarkToolkit(
            ...     oauth_redirect_uri="http://localhost:3000/callback"
            ... )
            >>> url = toolkit.get_oauth_url(state="session123")
            >>> # Redirect user to this URL
        """
        if not self._oauth_redirect_uri:
            raise ValueError(
                "oauth_redirect_uri must be set to use OAuth. "
                "Pass it to the LarkToolkit constructor."
            )

        if "feishu" in self._domain.lower():
            base = "https://open.feishu.cn"
        else:
            base = "https://open.larksuite.com"

        encoded_redirect = quote(self._oauth_redirect_uri, safe="")

        return (
            f"{base}/open-apis/authen/v1/authorize"
            f"?app_id={self._app_id}"
            f"&redirect_uri={encoded_redirect}"
            f"&state={state}"
        )

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        r"""Exchange an authorization code for user access tokens.

        After the user completes OAuth login, Lark redirects to your
        oauth_redirect_uri with a `code` parameter. Use this method to
        exchange that code for access tokens.

        Args:
            code (str): The authorization code from the OAuth callback.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - user_access_token: Token for making API calls as the user
                - refresh_token: Token for refreshing the access token
                - expires_in: Access token validity in seconds (~2 hours)
                - token_type: Token type (usually "Bearer")
                - scope: Granted permission scopes

        Example:
            >>> # In your callback handler:
            >>> code = request.args.get("code")
            >>> tokens = toolkit.exchange_code_for_token(code)
            >>> print(f"Logged in! Token expires in {tokens['expires_in']}s")
        """
        from lark_oapi.api.authen.v1 import (
            CreateOidcAccessTokenRequest,
            CreateOidcAccessTokenRequestBody,
        )

        try:
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
                return {
                    "error": f"Failed to exchange code: {response.msg}",
                    "code": response.code,
                }

            data = response.data
            self._user_access_token = data.access_token
            self._refresh_token = data.refresh_token

            # Notify callback so tokens can be persisted
            if (
                self._on_token_refresh
                and data.access_token
                and data.refresh_token
            ):
                self._on_token_refresh(data.access_token, data.refresh_token)

            logger.info("Successfully obtained user access token via OAuth")

            return {
                "user_access_token": data.access_token,
                "refresh_token": data.refresh_token,
                "expires_in": data.expires_in,
                "token_type": data.token_type,
                "scope": data.scope,
            }

        except Exception as e:
            logger.error(f"Error exchanging code for token: {e}")
            return {"error": f"Error exchanging code for token: {e!s}"}

    def refresh_user_token(self) -> Dict[str, Any]:
        r"""Refresh the user access token using the refresh token.

        User access tokens expire after approximately 2 hours. Use this method
        to obtain a new access token without requiring the user to log in
        again. The refresh token has a longer validity (~30 days).

        Returns:
            Dict[str, Any]: A dictionary containing:
                - user_access_token: New access token
                - refresh_token: New refresh token (save this!)
                - expires_in: New token validity in seconds

        Raises:
            ValueError: If no refresh token is available.

        Example:
            >>> # Refresh before token expires
            >>> new_tokens = toolkit.refresh_user_token()
            >>> save_to_database(new_tokens["refresh_token"])
        """
        if not self._refresh_token:
            raise ValueError(
                "No refresh token available. Complete OAuth flow first "
                "using get_oauth_url() and exchange_code_for_token()."
            )

        from lark_oapi.api.authen.v1 import (
            CreateOidcRefreshAccessTokenRequest,
            CreateOidcRefreshAccessTokenRequestBody,
        )

        try:
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
                return {
                    "error": f"Failed to refresh token: {response.msg}",
                    "code": response.code,
                }

            data = response.data
            self._user_access_token = data.access_token
            self._refresh_token = data.refresh_token

            # Notify callback so tokens can be persisted
            if (
                self._on_token_refresh
                and data.access_token
                and data.refresh_token
            ):
                self._on_token_refresh(data.access_token, data.refresh_token)

            logger.info("Successfully refreshed user access token")

            return {
                "user_access_token": data.access_token,
                "refresh_token": data.refresh_token,
                "expires_in": data.expires_in,
            }

        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return {"error": f"Error refreshing token: {e!s}"}

    def set_user_access_token(self, access_token: str) -> None:
        r"""Manually set the user access token.

        Use this if you have a pre-existing token (e.g., loaded from storage).

        Args:
            access_token (str): The user access token to use.
        """
        self._user_access_token = access_token
        logger.info("User access token set manually")

    def set_refresh_token(self, refresh_token: str) -> None:
        r"""Manually set the refresh token.

        Use this if you have a pre-existing token (e.g., loaded from storage).

        Args:
            refresh_token (str): The refresh token to use.
        """
        self._refresh_token = refresh_token

    def clear_user_tokens(self) -> None:
        r"""Clear stored user tokens and revert to app-level authentication."""
        self._user_access_token = None
        self._refresh_token = None
        logger.info(
            "User tokens cleared, reverted to app-level authentication"
        )

    def is_user_authenticated(self) -> bool:
        r"""Check if a user access token is currently set.

        Returns:
            bool: True if user authentication is active.
        """
        return self._user_access_token is not None

    def authenticate(
        self,
        port: int = 9000,
        timeout: int = 120,
        open_browser: bool = True,
    ) -> Dict[str, Any]:
        r"""Authenticate with Lark using OAuth in a single call.

        This method handles the complete OAuth flow automatically:
        1. Opens browser to Lark's login page
        2. Starts a temporary local server to capture the callback
        3. Exchanges the authorization code for tokens
        4. Stores the tokens for subsequent API calls

        Similar to Google's `flow.run_local_server()` - no Flask or HTML
        needed.

        Args:
            port (int): Local port for the OAuth callback server.
                (default: 9000)
            timeout (int): Seconds to wait for user to complete login.
                (default: 120)
            open_browser (bool): Whether to automatically open the browser.
                If False, the URL will be printed for manual opening.
                (default: True)

        Returns:
            Dict[str, Any]: A dictionary containing:
                - user_access_token: Token for making API calls as the user
                - refresh_token: Token for refreshing the access token
                - expires_in: Access token validity in seconds (~2 hours)
                - scope: Granted permission scopes

        Raises:
            TimeoutError: If the user doesn't complete login within timeout.
            RuntimeError: If the OAuth callback fails.

        Example:
            >>> toolkit = LarkToolkit()
            >>> toolkit.authenticate()  # Opens browser, handles everything
            >>> toolkit.lark_create_document(title="My Doc")  # Authenticated
        """
        import secrets
        import socket
        import webbrowser
        from urllib.parse import parse_qs, urlparse

        # Set up redirect URI for this authentication session
        redirect_uri = f"http://localhost:{port}/callback"
        self._oauth_redirect_uri = redirect_uri

        # Generate CSRF protection state
        state = secrets.token_urlsafe(16)

        # Generate the OAuth URL
        auth_url = self.get_oauth_url(state=state)

        # Open browser or print URL
        if open_browser:
            logger.info("Opening browser for Lark authentication...")
            print("\nOpening browser for Lark authentication...")
            print("If the browser doesn't open, visit this URL manually:")
            print(f"\n{auth_url}\n")
            webbrowser.open(auth_url)
        else:
            print("\nOpen this URL in your browser to authenticate:")
            print(f"\n{auth_url}\n")

        # Start minimal loopback server to capture the callback
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.settimeout(timeout)

        try:
            server.bind(("localhost", port))
            server.listen(1)
            logger.info(f"Waiting for OAuth callback on port {port}...")
            print(f"Waiting for authentication (timeout: {timeout}s)...")

            # Wait for the callback
            conn, addr = server.accept()
            conn.settimeout(10)

            # Read the HTTP request
            request_data = conn.recv(4096).decode("utf-8")

            # Parse the request to extract code and state
            # Format: GET /callback?code=XXX&state=YYY HTTP/1.1
            first_line = request_data.split("\n")[0]
            path = first_line.split(" ")[1]
            query_params = parse_qs(urlparse(path).query)

            received_code = query_params.get("code", [None])[0]
            received_state = query_params.get("state", [None])[0]
            error = query_params.get("error", [None])[0]

            # Send response to browser
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

        # Validate response
        if error:
            return {"error": f"OAuth authorization failed: {error}"}

        if not received_code:
            return {"error": "No authorization code received from Lark"}

        # Validate state to prevent CSRF
        if received_state != state:
            return {
                "error": "State mismatch - possible CSRF attack. "
                "Please try again."
            }

        # Exchange code for tokens
        logger.info("Exchanging authorization code for tokens...")
        print("Authentication received! Exchanging code for tokens...")

        result = self.exchange_code_for_token(received_code)

        if "error" not in result:
            print("Successfully authenticated with Lark!")
            logger.info("OAuth authentication completed successfully")

        return result


# ============================================================================
# END OF OAUTH MIXIN
# ============================================================================


@MCPServer()
class LarkToolkit(LarkOAuthMixin, BaseToolkit):
    r"""A toolkit for Lark (Feishu) document operations.

    This toolkit provides methods to interact with the Lark Open Platform API
    for creating, reading, updating, and deleting documents and document
    blocks.

    Attributes:
        app_id (Optional[str]): The Lark application ID.
        app_secret (Optional[str]): The Lark application secret.
        domain (str): The API domain (default: https://open.larksuite.com).
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
        domain: str = "https://open.larksuite.com",
        timeout: Optional[float] = None,
        # ---- OAuth parameters (optional, remove if OAuth not needed) ----
        user_access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        oauth_redirect_uri: Optional[str] = None,
        on_token_refresh: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        r"""Initializes the LarkToolkit.

        Args:
            app_id (Optional[str]): The Lark application ID. If not provided,
                uses LARK_APP_ID environment variable.
            app_secret (Optional[str]): The Lark application secret. If not
                provided, uses LARK_APP_SECRET environment variable.
            domain (str): The API domain. Use "https://open.larksuite.com" for
                international or "https://open.feishu.cn" for China.
                (default: "https://open.larksuite.com")
            timeout (Optional[float]): Request timeout in seconds.
            user_access_token (Optional[str]): Pre-existing user access token
                for OAuth authentication. If provided, API calls will be made
                as this user instead of as the application.
            refresh_token (Optional[str]): Pre-existing refresh token for
                refreshing the user access token.
            oauth_redirect_uri (Optional[str]): Redirect URI for OAuth flow.
                Required if you want to use get_oauth_url().
            on_token_refresh (Optional[Callable[[str, str], None]]): Callback
                function called when tokens are refreshed. Receives
                (access_token, refresh_token). Use this to persist tokens.
        """
        super().__init__(timeout=timeout)
        import lark_oapi as lark

        self._app_id = app_id or os.environ.get("LARK_APP_ID", "")
        self._app_secret = app_secret or os.environ.get("LARK_APP_SECRET", "")
        self._domain = domain

        # Determine the domain constant
        if "feishu" in domain.lower():
            lark_domain = lark.FEISHU_DOMAIN
        else:
            lark_domain = lark.LARK_DOMAIN

        # Build the client with automatic token management
        self._client = (
            lark.Client.builder()
            .app_id(self._app_id)
            .app_secret(self._app_secret)
            .domain(lark_domain)
            .build()
        )

        # Initialize OAuth support (remove this if OAuth mixin is removed)
        self._init_oauth(
            user_access_token=user_access_token,
            refresh_token=refresh_token,
            oauth_redirect_uri=oauth_redirect_uri,
            on_token_refresh=on_token_refresh,
        )

        logger.info(f"LarkToolkit initialized with domain: {domain}")
        if user_access_token:
            logger.info("Using user access token for authentication")

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
        from lark_oapi.api.docx.v1 import (
            CreateDocumentRequest,
            CreateDocumentRequestBody,
        )

        try:
            # If no folder token provided, get the user's root folder
            # This ensures documents appear in the user's document list
            target_folder = folder_token
            if not target_folder:
                root_result = self.lark_get_root_folder_token()
                if "error" not in root_result:
                    target_folder = root_result.get("token")
                    logger.info(f"Using root folder token: {target_folder}")

            request_body = (
                CreateDocumentRequestBody.builder().title(title).build()
            )

            if target_folder:
                request_body = (
                    CreateDocumentRequestBody.builder()
                    .title(title)
                    .folder_token(target_folder)
                    .build()
                )

            request = (
                CreateDocumentRequest.builder()
                .request_body(request_body)
                .build()
            )

            # Use user token if available (OAuth), otherwise app token
            option = self._get_request_option()
            if option:
                response = self._client.docx.v1.document.create(
                    request, option
                )
            else:
                response = self._client.docx.v1.document.create(request)

            if not response.success():
                logger.error(
                    f"Failed to create document: {response.code} - "
                    f"{response.msg}"
                )
                return {
                    "error": f"Failed to create document: {response.msg}",
                    "code": response.code,
                }

            doc = response.data.document
            domain = "feishu" if "feishu" in self._domain else "larksuite"
            return {
                "document_id": doc.document_id,
                "title": doc.title,
                "revision_id": doc.revision_id,
                "url": f"https://{domain}.com/docx/{doc.document_id}",
                "folder_token": target_folder,
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
                - create_time: Document creation timestamp
        """
        from lark_oapi.api.docx.v1 import GetDocumentRequest

        try:
            request = (
                GetDocumentRequest.builder().document_id(document_id).build()
            )

            option = self._get_request_option()
            if option:
                response = self._client.docx.v1.document.get(request, option)
            else:
                response = self._client.docx.v1.document.get(request)

            if not response.success():
                logger.error(
                    f"Failed to get document: {response.code} - {response.msg}"
                )
                return {
                    "error": f"Failed to get document: {response.msg}",
                    "code": response.code,
                }

            doc = response.data.document
            return {
                "document_id": doc.document_id,
                "title": doc.title,
                "revision_id": doc.revision_id,
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
                - block_count: Total number of blocks in the document
        """
        from lark_oapi.api.docx.v1 import RawContentDocumentRequest

        try:
            request = (
                RawContentDocumentRequest.builder()
                .document_id(document_id)
                .build()
            )

            option = self._get_request_option()
            if option:
                response = self._client.docx.v1.document.raw_content(
                    request, option
                )
            else:
                response = self._client.docx.v1.document.raw_content(request)

            if not response.success():
                logger.error(
                    f"Failed to get document content: {response.code} - "
                    f"{response.msg}"
                )
                return {
                    "error": f"Failed to get document content: {response.msg}",
                    "code": response.code,
                }

            return {
                "document_id": document_id,
                "content": response.data.content,
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
                (default: 50)
            page_token (Optional[str]): Token for pagination. Use the
                page_token from previous response to get next page.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - document_id: The document ID
                - blocks: List of block objects with type and content
                - has_more: Whether there are more blocks to fetch
                - page_token: Token to fetch the next page
        """
        from lark_oapi.api.docx.v1 import ListDocumentBlockRequest

        try:
            request_builder = (
                ListDocumentBlockRequest.builder()
                .document_id(document_id)
                .page_size(page_size)
            )

            if page_token:
                request_builder = request_builder.page_token(page_token)

            request = request_builder.build()
            option = self._get_request_option()
            if option:
                response = self._client.docx.v1.document_block.list(
                    request, option
                )
            else:
                response = self._client.docx.v1.document_block.list(request)

            if not response.success():
                logger.error(
                    f"Failed to list blocks: {response.code} - {response.msg}"
                )
                return {
                    "error": f"Failed to list blocks: {response.msg}",
                    "code": response.code,
                }

            blocks = []
            if response.data.items:
                for block in response.data.items:
                    block_info = {
                        "block_id": block.block_id,
                        "block_type": block.block_type,
                        "parent_id": block.parent_id,
                    }

                    # Try to extract text content
                    text_content = _extract_text_from_block(block)
                    if text_content:
                        block_info["text_content"] = text_content

                    blocks.append(block_info)

            return {
                "document_id": document_id,
                "blocks": blocks,
                "has_more": response.data.has_more or False,
                "page_token": response.data.page_token,
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
        from lark_oapi.api.docx.v1 import GetDocumentBlockRequest

        try:
            request = (
                GetDocumentBlockRequest.builder()
                .document_id(document_id)
                .block_id(block_id)
                .build()
            )

            option = self._get_request_option()
            if option:
                response = self._client.docx.v1.document_block.get(
                    request, option
                )
            else:
                response = self._client.docx.v1.document_block.get(request)

            if not response.success():
                logger.error(
                    f"Failed to get block: {response.code} - {response.msg}"
                )
                return {
                    "error": f"Failed to get block: {response.msg}",
                    "code": response.code,
                }

            block = response.data.block
            block_info = {
                "block_id": block.block_id,
                "block_type": block.block_type,
                "parent_id": block.parent_id,
                "children": block.children or [],
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
                (default: 50)
            page_token (Optional[str]): Token for pagination.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - block_id: The parent block ID
                - children: List of child block objects
                - has_more: Whether there are more children to fetch
                - page_token: Token to fetch the next page
        """
        from lark_oapi.api.docx.v1 import GetDocumentBlockChildrenRequest

        try:
            request_builder = (
                GetDocumentBlockChildrenRequest.builder()
                .document_id(document_id)
                .block_id(block_id)
                .page_size(page_size)
            )

            if page_token:
                request_builder = request_builder.page_token(page_token)

            request = request_builder.build()
            option = self._get_request_option()
            if option:
                response = self._client.docx.v1.document_block_children.get(
                    request, option
                )
            else:
                response = self._client.docx.v1.document_block_children.get(
                    request
                )

            if not response.success():
                logger.error(
                    f"Failed to get block children: {response.code} - "
                    f"{response.msg}"
                )
                return {
                    "error": f"Failed to get block children: {response.msg}",
                    "code": response.code,
                }

            children = []
            if response.data.items:
                for block in response.data.items:
                    block_info = {
                        "block_id": block.block_id,
                        "block_type": block.block_type,
                        "parent_id": block.parent_id,
                    }

                    text_content = _extract_text_from_block(block)
                    if text_content:
                        block_info["text_content"] = text_content

                    children.append(block_info)

            return {
                "block_id": block_id,
                "children": children,
                "has_more": response.data.has_more or False,
                "page_token": response.data.page_token,
            }

        except Exception as e:
            logger.error(f"Error getting block children: {e}")
            return {"error": f"Error getting block children: {e!s}"}

    def lark_create_block(
        self,
        document_id: str,
        block_type: Literal[
            "text",
            "heading1",
            "heading2",
            "heading3",
            "heading4",
            "heading5",
            "heading6",
            "heading7",
            "heading8",
            "heading9",
            "bullet",
            "ordered",
            "code",
            "quote",
            "todo",
            "divider",
            "callout",
        ],
        content: str,
        parent_block_id: Optional[str] = None,
        index: int = -1,
    ) -> Dict[str, Any]:
        r"""Creates a new block in a Lark document.

        Args:
            document_id (str): The unique identifier of the document.
            block_type (str): The type of block to create. Supported types:
                text, heading1-9, bullet, ordered, code, quote, todo, divider,
                callout.
            content (str): The text content of the block.
            parent_block_id (Optional[str]): The parent block ID. If not
                provided, the block will be added to the document root.
            index (int): The position to insert the block. -1 means append
                at the end. (default: -1)

        Returns:
            Dict[str, Any]: A dictionary containing:
                - block_id: The ID of the created block
                - block_type: The type of the created block
                - document_revision_id: The new document revision ID
        """
        from lark_oapi.api.docx.v1 import (
            BlockBuilder,
            CalloutBuilder,
            CreateDocumentBlockChildrenRequest,
            CreateDocumentBlockChildrenRequestBody,
            DividerBuilder,
            TextBuilder,
            TextElementBuilder,
            TextRunBuilder,
        )

        try:
            # Get the block type number
            block_type_num = BLOCK_TYPES.get(block_type, 2)

            # Build text element
            text_element = (
                TextElementBuilder()
                .text_run(TextRunBuilder().content(content).build())
                .build()
            )

            # Build a Text object (used for most block types)
            text_obj = TextBuilder().elements([text_element]).build()

            # Build the block based on type using the builder pattern
            block_builder = BlockBuilder().block_type(block_type_num)

            if block_type == "text":
                block_builder = block_builder.text(text_obj)
            elif block_type == "heading1":
                block_builder = block_builder.heading1(text_obj)
            elif block_type == "heading2":
                block_builder = block_builder.heading2(text_obj)
            elif block_type == "heading3":
                block_builder = block_builder.heading3(text_obj)
            elif block_type == "heading4":
                block_builder = block_builder.heading4(text_obj)
            elif block_type == "heading5":
                block_builder = block_builder.heading5(text_obj)
            elif block_type == "heading6":
                block_builder = block_builder.heading6(text_obj)
            elif block_type == "heading7":
                block_builder = block_builder.heading7(text_obj)
            elif block_type == "heading8":
                block_builder = block_builder.heading8(text_obj)
            elif block_type == "heading9":
                block_builder = block_builder.heading9(text_obj)
            elif block_type == "bullet":
                block_builder = block_builder.bullet(text_obj)
            elif block_type == "ordered":
                block_builder = block_builder.ordered(text_obj)
            elif block_type == "code":
                block_builder = block_builder.code(text_obj)
            elif block_type == "quote":
                block_builder = block_builder.quote(text_obj)
            elif block_type == "todo":
                block_builder = block_builder.todo(text_obj)
            elif block_type == "divider":
                block_builder = block_builder.divider(DividerBuilder().build())
            elif block_type == "callout":
                block_builder = block_builder.callout(
                    CalloutBuilder().elements([text_element]).build()
                )

            block = block_builder.build()

            # Build the request
            request_body_builder = (
                CreateDocumentBlockChildrenRequestBody.builder().children(
                    [block]
                )
            )

            if index >= 0:
                request_body_builder = request_body_builder.index(index)

            request_body = request_body_builder.build()

            # Determine the parent block ID
            target_block_id = parent_block_id or document_id

            request = (
                CreateDocumentBlockChildrenRequest.builder()
                .document_id(document_id)
                .block_id(target_block_id)
                .request_body(request_body)
                .build()
            )

            option = self._get_request_option()
            if option:
                response = self._client.docx.v1.document_block_children.create(
                    request, option
                )
            else:
                response = self._client.docx.v1.document_block_children.create(
                    request
                )

            if not response.success():
                logger.error(
                    f"Failed to create block: {response.code} - {response.msg}"
                )
                return {
                    "error": f"Failed to create block: {response.msg}",
                    "code": response.code,
                }

            created_blocks = response.data.children or []
            if created_blocks:
                return {
                    "block_id": created_blocks[0].block_id,
                    "block_type": block_type,
                    "document_revision_id": response.data.document_revision_id,
                }

            return {
                "success": True,
                "document_revision_id": response.data.document_revision_id,
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

        Note: This method updates the text content of a block. The block type
        cannot be changed through this method.

        Args:
            document_id (str): The unique identifier of the document.
            block_id (str): The unique identifier of the block to update.
            content (str): The new text content for the block.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - success: Whether the update was successful
                - block_id: The ID of the updated block
                - document_revision_id: The new document revision ID
        """
        from lark_oapi.api.docx.v1 import (
            PatchDocumentBlockRequest,
            TextElementBuilder,
            TextRunBuilder,
            UpdateBlockRequestBuilder,
            UpdateTextElementsRequestBuilder,
        )

        try:
            # Build the text element with content
            text_run = TextRunBuilder().content(content).build()
            text_element = TextElementBuilder().text_run(text_run).build()

            # Build the update text elements request
            update_text_elements = (
                UpdateTextElementsRequestBuilder()
                .elements([text_element])
                .build()
            )

            # Build the update block request
            update_block = (
                UpdateBlockRequestBuilder()
                .update_text_elements(update_text_elements)
                .build()
            )

            # Build the patch request
            request = (
                PatchDocumentBlockRequest.builder()
                .document_id(document_id)
                .block_id(block_id)
                .request_body(update_block)
                .build()
            )

            option = self._get_request_option()
            if option:
                response = self._client.docx.v1.document_block.patch(
                    request, option
                )
            else:
                response = self._client.docx.v1.document_block.patch(request)

            if not response.success():
                logger.error(
                    f"Failed to update block: {response.code} - {response.msg}"
                )
                return {
                    "error": f"Failed to update block: {response.msg}",
                    "code": response.code,
                }

            return {
                "success": True,
                "block_id": block_id,
                "document_revision_id": response.data.document_revision_id,
            }

        except Exception as e:
            logger.error(f"Error updating block: {e}")
            return {"error": f"Error updating block: {e!s}"}

    def lark_delete_block(
        self,
        document_id: str,
        block_id: str,
    ) -> Dict[str, Any]:
        r"""Deletes a block from a Lark document.

        Args:
            document_id (str): The unique identifier of the document.
            block_id (str): The unique identifier of the block to delete.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - success: Whether the deletion was successful
                - block_id: The ID of the deleted block
                - document_revision_id: The new document revision ID
        """
        from lark_oapi.api.docx.v1 import (
            BatchDeleteDocumentBlockChildrenRequest,
            BatchDeleteDocumentBlockChildrenRequestBody,
        )

        try:
            # First, get the parent block ID
            block_info = self.lark_get_block(document_id, block_id)
            if "error" in block_info:
                return block_info

            parent_id = block_info.get("parent_id", document_id)

            request = (
                BatchDeleteDocumentBlockChildrenRequest.builder()
                .document_id(document_id)
                .block_id(parent_id)
                .request_body(
                    BatchDeleteDocumentBlockChildrenRequestBody.builder()
                    .start_index(0)
                    .end_index(1)
                    .build()
                )
                .build()
            )

            option = self._get_request_option()
            if option:
                response = (
                    self._client.docx.v1.document_block_children.batch_delete(
                        request, option
                    )
                )
            else:
                response = (
                    self._client.docx.v1.document_block_children.batch_delete(
                        request
                    )
                )

            if not response.success():
                logger.error(
                    f"Failed to delete block: {response.code} - {response.msg}"
                )
                return {
                    "error": f"Failed to delete block: {response.msg}",
                    "code": response.code,
                }

            return {
                "success": True,
                "block_id": block_id,
                "document_revision_id": response.data.document_revision_id,
            }

        except Exception as e:
            logger.error(f"Error deleting block: {e}")
            return {"error": f"Error deleting block: {e!s}"}

    def lark_batch_update_blocks(
        self,
        document_id: str,
        operations_json: str,
    ) -> Dict[str, Any]:
        r"""Performs batch operations on document blocks.

        This method allows you to perform multiple block operations in a single
        API call, which is more efficient than making individual requests.

        Args:
            document_id (str): The unique identifier of the document.
            operations_json (str): A JSON string containing a list of
                operations.
                Each operation is a dictionary with:
                - action: "create", "update", or "delete"
                - block_id: Required for "update" and "delete" actions
                - block_type: Required for "create" action
                - content: Required for "create" and "update" actions
                - parent_block_id: Optional, for "create" action

        Returns:
            Dict[str, Any]: A dictionary containing:
                - success: Whether all operations were successful
                - results: List of results for each operation
                - document_revision_id: The final document revision ID

        Example:
            >>> operations_json = '''[
            ...     {"action": "create", "block_type": "text",
            ...      "content": "New paragraph"},
            ...     {"action": "update", "block_id": "block123",
            ...      "content": "Updated text"},
            ...     {"action": "delete", "block_id": "block456"}
            ... ]'''
            >>> toolkit.lark_batch_update_blocks(document_id, operations_json)
        """
        import json

        try:
            operations = json.loads(operations_json)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON in operations_json: {e}"}

        if not isinstance(operations, list):
            return {"error": "operations_json must be a JSON array"}

        results = []
        final_revision_id = None

        for i, op in enumerate(operations):
            action = op.get("action", "").lower()
            result = {"index": i, "action": action}

            try:
                if action == "create":
                    block_type = op.get("block_type", "text")
                    content = op.get("content", "")
                    parent_block_id = op.get("parent_block_id")

                    create_result = self.lark_create_block(
                        document_id=document_id,
                        block_type=block_type,
                        content=content,
                        parent_block_id=parent_block_id,
                    )
                    result.update(create_result)
                    if "document_revision_id" in create_result:
                        final_revision_id = create_result[
                            "document_revision_id"
                        ]

                elif action == "update":
                    block_id = op.get("block_id")
                    content = op.get("content", "")

                    if not block_id:
                        result["error"] = "block_id is required for update"
                    else:
                        update_result = self.lark_update_block(
                            document_id=document_id,
                            block_id=block_id,
                            content=content,
                        )
                        result.update(update_result)
                        if "document_revision_id" in update_result:
                            final_revision_id = update_result[
                                "document_revision_id"
                            ]

                elif action == "delete":
                    block_id = op.get("block_id")

                    if not block_id:
                        result["error"] = "block_id is required for delete"
                    else:
                        delete_result = self.lark_delete_block(
                            document_id=document_id,
                            block_id=block_id,
                        )
                        result.update(delete_result)
                        if "document_revision_id" in delete_result:
                            final_revision_id = delete_result[
                                "document_revision_id"
                            ]

                else:
                    result["error"] = f"Unknown action: {action}"

            except Exception as e:
                result["error"] = str(e)

            results.append(result)

        # Check if all operations were successful
        all_success = all("error" not in r for r in results)

        return {
            "success": all_success,
            "results": results,
            "document_revision_id": final_revision_id,
        }

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
                (default: 50)
            page_token (Optional[str]): Token for pagination. Use the
                page_token from previous response to get next page.
            order_by (str): Field to sort by. Options: "EditedTime",
                "CreatedTime", "DeletedTime". (default: "EditedTime")
            direction (str): Sort direction. Options: "ASC", "DESC".
                (default: "DESC")

        Returns:
            Dict[str, Any]: A dictionary containing:
                - files: List of file/folder objects with token, name, type
                - has_more: Whether there are more items to fetch
                - page_token: Token to fetch the next page

        Example:
            >>> # List root folder to find available folders
            >>> result = toolkit.lark_list_folder_contents()
            >>> for item in result["files"]:
            ...     print(f"{item['name']} ({item['type']}): {item['token']}")
            ...
            >>> # Use a folder token to create documents in that folder
            >>> toolkit.lark_create_document(
            ...     title="My Doc",
            ...     folder_token=result["files"][0]["token"]
            ... )
        """
        from lark_oapi.api.drive.v1 import ListFileRequest

        try:
            # Build the request
            request_builder = (
                ListFileRequest.builder()
                .page_size(page_size)
                .order_by(order_by)
                .direction(direction)
            )

            if folder_token:
                request_builder = request_builder.folder_token(folder_token)

            if page_token:
                request_builder = request_builder.page_token(page_token)

            request = request_builder.build()

            # Use user token if available (OAuth), otherwise app token
            option = self._get_request_option()
            if option:
                response = self._client.drive.v1.file.list(request, option)
            else:
                response = self._client.drive.v1.file.list(request)

            if not response.success():
                logger.error(
                    f"Failed to list folder contents: {response.code} - "
                    f"{response.msg}"
                )
                return {
                    "error": f"Failed to list folder contents: {response.msg}",
                    "code": response.code,
                }

            files = []
            if response.data.files:
                for file in response.data.files:
                    file_info = {
                        "token": file.token,
                        "name": file.name,
                        "type": file.type,
                        "parent_token": file.parent_token,
                        "created_time": file.created_time,
                        "modified_time": file.modified_time,
                        "owner_id": file.owner_id,
                    }

                    # Add URL for easy access
                    if file.type == "folder":
                        file_info["url"] = (
                            f"https://larksuite.com/drive/folder/{file.token}"
                        )
                    elif file.type == "docx":
                        file_info["url"] = (
                            f"https://larksuite.com/docx/{file.token}"
                        )
                    elif file.type == "sheet":
                        file_info["url"] = (
                            f"https://larksuite.com/sheets/{file.token}"
                        )
                    elif file.type == "bitable":
                        file_info["url"] = (
                            f"https://larksuite.com/base/{file.token}"
                        )

                    files.append(file_info)

            return {
                "folder_token": folder_token or "root",
                "files": files,
                "has_more": response.data.has_more or False,
                "page_token": response.data.next_page_token,
            }

        except Exception as e:
            logger.error(f"Error listing folder contents: {e}")
            return {"error": f"Error listing folder contents: {e!s}"}

    def lark_get_root_folder_token(self) -> Dict[str, Any]:
        r"""Gets the token of the user's root folder in Lark Drive.

        The root folder is the top-level "My Space" folder where you can
        create documents that will be visible in your document list.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - token: The root folder token
                - id: The root folder ID
                - user_id: The owner's user ID

        Example:
            >>> # Get root folder and create a document there
            >>> root = toolkit.lark_get_root_folder_token()
            >>> toolkit.lark_create_document(
            ...     title="My Doc",
            ...     folder_token=root["token"]
            ... )
        """
        try:
            # Get the root folder token by listing files and extracting
            # the parent_token from any file in the root folder.
            # This is more reliable than the explorer/v2 endpoint which
            # may not be available in all SDK versions.
            result = self.lark_list_folder_contents(page_size=1)

            if "error" in result:
                return result

            # If there are files, get the parent_token which is the root
            if result.get("files") and len(result["files"]) > 0:
                root_token = result["files"][0].get("parent_token")
                if root_token:
                    return {
                        "token": root_token,
                        "id": root_token,
                        "user_id": None,
                    }

            # If no files exist, we can still use "root" as a fallback
            # which works for some operations
            return {
                "token": "root",
                "id": "root",
                "user_id": None,
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

        Example:
            >>> # Create a folder in root
            >>> folder = toolkit.lark_create_folder("My Project")
            >>> # Create a document in the new folder
            >>> toolkit.lark_create_document(
            ...     title="README",
            ...     folder_token=folder["token"]
            ... )
        """
        from lark_oapi.api.drive.v1 import (
            CreateFolderFileRequest,
            CreateFolderFileRequestBody,
        )

        try:
            # If no folder token provided, get the root folder
            parent_token = folder_token
            if not parent_token:
                root_result = self.lark_get_root_folder_token()
                if "error" in root_result:
                    return root_result
                parent_token = root_result["token"]

            request = (
                CreateFolderFileRequest.builder()
                .request_body(
                    CreateFolderFileRequestBody.builder()
                    .name(name)
                    .folder_token(parent_token)
                    .build()
                )
                .build()
            )

            # Use user token if available (OAuth), otherwise app token
            option = self._get_request_option()
            if option:
                response = self._client.drive.v1.file.create_folder(
                    request, option
                )
            else:
                response = self._client.drive.v1.file.create_folder(request)

            if not response.success():
                logger.error(
                    f"Failed to create folder: {response.code} - "
                    f"{response.msg}"
                )
                return {
                    "error": f"Failed to create folder: {response.msg}",
                    "code": response.code,
                }

            return {
                "token": response.data.token,
                "url": response.data.url,
            }

        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            return {"error": f"Error creating folder: {e!s}"}

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        return [
            # Drive operations
            FunctionTool(self.lark_get_root_folder_token),
            FunctionTool(self.lark_list_folder_contents),
            FunctionTool(self.lark_create_folder),
            # Basic document operations
            FunctionTool(self.lark_create_document),
            FunctionTool(self.lark_get_document),
            FunctionTool(self.lark_get_document_content),
            FunctionTool(self.lark_list_document_blocks),
            # Block operations
            FunctionTool(self.lark_get_block),
            FunctionTool(self.lark_get_block_children),
            FunctionTool(self.lark_create_block),
            FunctionTool(self.lark_update_block),
            FunctionTool(self.lark_delete_block),
            FunctionTool(self.lark_batch_update_blocks),
        ]
