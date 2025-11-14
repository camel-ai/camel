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

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from camel.auth.auth_manager import AuthenticationManager
from camel.auth.base import (
    AuthenticationError,
    AuthenticationProvider,
)
from camel.auth.oauth2_provider import OAuth2Provider
from camel.auth.token_provider import TokenProvider
from camel.logger import get_logger

if TYPE_CHECKING:
    from ssl import SSLContext

    from slack_sdk import WebClient

logger = get_logger(__name__)


class SlackApplication(ABC):
    r"""Base class for Slack applications that provides unified authentication.

    This class serves as a foundation for Slack toolkits, triggers, and bots
    by providing a common authentication interface using the CAMEL auth system.
    It supports both Bot token and OAuth2 authentication flows.

    The class integrates with the CAMEL authentication system to provide:
    - Standardized credential management
    - Support for multiple authentication methods
    - Automatic token refresh capabilities
    - Environment variable fallbacks
    """

    def __init__(
        self,
        slack_token: Optional[str] = None,
        app_token: Optional[str] = None,
        signing_secret: Optional[str] = None,
        ssl: Optional[SSLContext] = None,
        auth_provider: Optional[AuthenticationProvider] = None,
        use_oauth2: bool = False,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        redirect_uri: Optional[str] = None,
    ):
        r"""Initialize the Slack application with authentication configuration.

        Args:
            slack_token (Optional[str]): The Slack Bot or User token.
                If not provided, attempts to retrieve from environment variables.
            app_token (Optional[str]): The Slack App-level token for Socket Mode.
                If not provided, attempts to retrieve from SLACK_APP_TOKEN.
            signing_secret (Optional[str]): The Slack signing secret for webhook verification.
                If not provided, attempts to retrieve from SLACK_SIGNING_SECRET.
            ssl (Optional[SSLContext]): SSL context for secure connections.
            auth_provider (Optional[AuthenticationProvider]): Custom authentication provider.
                If not provided, a TokenProvider or OAuth2Provider will be created automatically.
            use_oauth2 (bool): Whether to use OAuth2 authentication instead of Bot token.
                Defaults to False (Bot token authentication).
            client_id (Optional[str]): OAuth2 client ID for OAuth2 authentication.
            client_secret (Optional[str]): OAuth2 client secret for OAuth2 authentication.
            scopes (Optional[List[str]]): OAuth2 scopes for OAuth2 authentication.
                Defaults to common Slack scopes if not provided.
            redirect_uri (Optional[str]): OAuth2 redirect URI for OAuth2 authentication.
        """
        # Store initialization parameters
        self.slack_token = slack_token
        self.app_token = app_token
        self.signing_secret = signing_secret
        self.ssl = ssl
        self.use_oauth2 = use_oauth2
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or self._get_default_scopes()
        self.redirect_uri = redirect_uri

        # Authentication state
        self._client: Optional[WebClient] = None
        self._authenticated = False

        # Set up authentication system
        self.auth_manager = AuthenticationManager()

        # Set up authentication provider
        if auth_provider:
            self.auth_provider = auth_provider
            self.auth_manager.register_provider("slack", auth_provider)
        else:
            self._setup_auth_provider()

    def _get_default_scopes(self) -> List[str]:
        r"""Get default OAuth2 scopes for Slack applications.

        Returns:
            List[str]: List of default OAuth2 scopes.
        """
        return [
            "channels:read",
            "channels:write",
            "chat:write",
            "groups:read",
            "im:read",
            "mpim:read",
            "users:read",
            "app_mentions:read",
            "channels:history",
            "groups:history",
            "im:history",
            "mpim:history",
            "files:write",
            "files:read",
        ]

    def _setup_auth_provider(self) -> None:
        r"""Set up the authentication provider based on configuration.

        Raises:
            AuthenticationError: If authentication provider setup fails.
        """
        try:
            if self.use_oauth2:
                # Set up OAuth2 provider for Slack
                self.auth_provider = OAuth2Provider(
                    provider_name="slack",
                    client_id_env_var="SLACK_CLIENT_ID",
                    client_secret_env_var="SLACK_CLIENT_SECRET",
                    token_uri="https://slack.com/api/oauth.v2.access",
                    refresh_token_env_var="SLACK_REFRESH_TOKEN",
                    scopes=self.scopes,
                )
                logger.info(
                    "OAuth2 authentication provider configured for Slack"
                )
            else:
                # Set up Token provider for Slack Bot token
                self.auth_provider = TokenProvider(
                    provider_name="slack",
                    token_env_var="SLACK_BOT_TOKEN",
                    token_type="Bearer",
                    header_name="Authorization",
                )
                logger.info(
                    "Token authentication provider configured for Slack"
                )

            self.auth_manager.register_provider("slack", self.auth_provider)

        except Exception as e:
            logger.error(f"Failed to setup Slack authentication provider: {e}")
            raise AuthenticationError(
                f"Failed to setup Slack authentication: {e}"
            )

    def _get_credentials(self) -> Dict[str, Optional[str]]:
        r"""Retrieve Slack credentials from authentication provider or fallback to instance variables.

        Returns:
            Dict[str, Optional[str]]: Dictionary containing the credentials.
        """
        # Try to get credentials from auth provider first
        try:
            if self.auth_provider and self.auth_provider.is_authenticated():
                auth_credentials = self.auth_provider.get_credentials()

                if self.use_oauth2:
                    # For OAuth2, use access_token
                    slack_token = auth_credentials.get("access_token")
                else:
                    # For Token provider, use token
                    slack_token = auth_credentials.get("token")

                return {
                    "slack_token": slack_token,
                    "app_token": self.app_token
                    or os.environ.get("SLACK_APP_TOKEN"),
                    "signing_secret": (
                        self.signing_secret
                        or os.environ.get("SLACK_SIGNING_SECRET")
                    ),
                }
        except AuthenticationError:
            logger.warning(
                "Auth provider not authenticated, falling back to environment variables"
            )

        # Fallback to environment variables and instance variables
        return {
            "slack_token": (
                self.slack_token
                or os.environ.get("SLACK_BOT_TOKEN")
                or os.environ.get("SLACK_USER_TOKEN")
                or os.environ.get("SLACK_TOKEN")  # For SlackApp compatibility
            ),
            "app_token": self.app_token or os.environ.get("SLACK_APP_TOKEN"),
            "signing_secret": (
                self.signing_secret or os.environ.get("SLACK_SIGNING_SECRET")
            ),
        }

    async def authenticate(self) -> bool:
        r"""Authenticate with Slack API and verify credentials using the authentication provider.

        Returns:
            bool: True if authentication is successful, False otherwise.

        Raises:
            ImportError: If slack_sdk package is not installed.
        """
        try:
            from slack_sdk import WebClient
        except ImportError as e:
            logger.error(
                "Cannot import slack_sdk. Please install the package with "
                "`pip install slack_sdk`."
            )
            raise ImportError(
                "Cannot import slack_sdk. Please install the package with "
                "`pip install slack_sdk`."
            ) from e

        try:
            # First, authenticate with the auth provider
            if not self.auth_provider.is_authenticated():
                auth_kwargs = {
                    "token": self.slack_token,
                }

                if self.use_oauth2:
                    auth_kwargs.update(
                        {
                            "client_id": self.client_id
                            or os.environ.get("SLACK_CLIENT_ID"),
                            "client_secret": self.client_secret
                            or os.environ.get("SLACK_CLIENT_SECRET"),
                        }
                    )

                auth_success = self.auth_provider.authenticate(**auth_kwargs)

                if not auth_success:
                    logger.error("Failed to authenticate with auth provider")
                    return False

            # Get credentials from auth provider
            credentials = self._get_credentials()
            slack_token = credentials["slack_token"]

            if not slack_token:
                missing_vars = self.auth_provider.get_missing_env_vars()
                logger.error(
                    f"Slack token not found. Missing environment variables: {missing_vars}"
                )
                return False

            # Create Slack client and test connection
            self._client = WebClient(token=slack_token, ssl=self.ssl)

            # Test the connection
            response = self._client.auth_test()
            if response["ok"]:
                self._authenticated = True
                logger.info(
                    f"Slack authentication successful for user: {response.get('user', 'Unknown')} "
                    f"(team: {response.get('team', 'Unknown')})"
                )
                return True
            else:
                logger.error(
                    f"Slack authentication failed: {response.get('error', 'Unknown error')}"
                )
                return False

        except AuthenticationError as e:
            logger.error(f"Authentication provider error: {e}")
            return False
        except Exception as e:
            logger.error(f"Slack authentication error: {e}")
            return False

    def login_slack(
        self,
        slack_token: Optional[str] = None,
        ssl: Optional[SSLContext] = None,
    ) -> WebClient:
        r"""Legacy method for backwards compatibility with SlackToolkit.

        Authenticate using the Slack API and return a WebClient.

        Args:
            slack_token (str, optional): The Slack API token.
                If not provided, it attempts to retrieve the token from
                the authentication provider or environment variables.
            ssl (SSLContext, optional): SSL context for secure connections.
                Defaults to None.

        Returns:
            WebClient: A WebClient object for interacting with Slack API.

        Raises:
            ImportError: If slack_sdk package is not installed.
            AuthenticationError: If authentication fails.
        """
        try:
            from slack_sdk import WebClient
        except ImportError as e:
            raise ImportError(
                "Cannot import slack_sdk. Please install the package with "
                "`pip install slack_sdk`."
            ) from e

        # Update token if provided
        if slack_token:
            self.slack_token = slack_token

        # Authenticate if not already done
        if not self._authenticated:
            import asyncio

            success = asyncio.run(self.authenticate())
            if not success:
                raise AuthenticationError("Failed to authenticate with Slack")

        # Return the authenticated client
        if self._client:
            return self._client

        # Fallback: create client directly (for backwards compatibility)
        credentials = self._get_credentials()
        token = credentials["slack_token"]

        if not token:
            raise AuthenticationError(
                "SLACK_BOT_TOKEN, SLACK_USER_TOKEN, or SLACK_TOKEN "
                "environment variable not set."
            )

        client = WebClient(token=token, ssl=ssl or self.ssl)
        logger.info("Slack login successful.")
        return client

    async def refresh_auth_token(self) -> bool:
        r"""Refresh the authentication token and re-authenticate using the auth provider.

        Returns:
            bool: True if token refresh is successful, False otherwise.
        """
        logger.info("Refreshing Slack authentication token...")
        try:
            # Reset authentication state
            self._authenticated = False
            self._client = None

            # Refresh credentials via auth provider
            if self.auth_provider:
                refresh_success = self.auth_provider.refresh_credentials()
                if not refresh_success:
                    logger.error(
                        "Failed to refresh credentials via auth provider"
                    )
                    return False

            # Re-authenticate
            return await self.authenticate()

        except Exception as e:
            logger.error(f"Failed to refresh auth token: {e}")
            return False

    def get_client(self) -> Optional[WebClient]:
        r"""Get the authenticated Slack WebClient.

        Returns:
            Optional[WebClient]: The authenticated WebClient or None if not authenticated.
        """
        if not self._authenticated or not self._client:
            logger.warning(
                "Slack client not authenticated. Call authenticate() first."
            )
            return None
        return self._client

    def get_auth_headers(self) -> Dict[str, str]:
        r"""Get authentication headers from the auth provider.

        Returns:
            Dict[str, str]: Authentication headers for API requests.

        Raises:
            AuthenticationError: If not authenticated.
        """
        if not self._authenticated or not self.auth_provider:
            raise AuthenticationError("Slack application not authenticated")

        try:
            return self.auth_provider.get_auth_headers()
        except AuthenticationError:
            # Fallback to token-based header if auth provider fails
            credentials = self._get_credentials()
            slack_token = credentials["slack_token"]
            if slack_token:
                return {"Authorization": f"Bearer {slack_token}"}
            raise

    def get_auth_provider(self) -> Optional[AuthenticationProvider]:
        r"""Get the authentication provider instance.

        Returns:
            Optional[AuthenticationProvider]: The authentication provider or None.
        """
        return self.auth_provider

    def get_auth_manager(self) -> AuthenticationManager:
        r"""Get the authentication manager instance.

        Returns:
            AuthenticationManager: The authentication manager.
        """
        return self.auth_manager

    def is_authenticated(self) -> bool:
        r"""Check if the application is currently authenticated.

        Returns:
            bool: True if authenticated, False otherwise.
        """
        return self._authenticated and self._client is not None

    def verify_webhook_signature(
        self, request_body: str, timestamp: str, signature: str
    ) -> bool:
        r"""Verify Slack webhook signature for security.

        Args:
            request_body (str): The raw request body.
            timestamp (str): The X-Slack-Request-Timestamp header value.
            signature (str): The X-Slack-Signature header value.

        Returns:
            bool: True if signature is valid, False otherwise.
        """
        credentials = self._get_credentials()
        signing_secret = credentials["signing_secret"]

        if not signing_secret:
            logger.warning(
                "No signing secret configured, skipping signature verification."
            )
            return True

        try:
            import hashlib
            import hmac

            # Create signature
            sig_basestring = f"v0:{timestamp}:{request_body}"
            computed_signature = (
                'v0='
                + hmac.new(
                    signing_secret.encode(),
                    sig_basestring.encode(),
                    hashlib.sha256,
                ).hexdigest()
            )

            # Compare signatures
            return hmac.compare_digest(computed_signature, signature)

        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False

    def validate_environment(self) -> Dict[str, Any]:
        r"""Validate the environment configuration for Slack.

        Returns:
            Dict[str, Any]: Validation results including missing variables and recommendations.
        """
        validation_result = {
            "valid": True,
            "missing_env_vars": [],
            "warnings": [],
            "auth_provider_status": None,
        }

        # Check auth provider validation
        if self.auth_provider:
            missing_vars = self.auth_provider.get_missing_env_vars()
            validation_result["missing_env_vars"] = missing_vars
            validation_result["auth_provider_status"] = (
                self.auth_provider.validate_environment()
            )

            if missing_vars:
                validation_result["valid"] = False

        # Check OAuth2 specific requirements
        if self.use_oauth2:
            oauth_vars = ["SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET"]
            for var in oauth_vars:
                if not os.environ.get(var):
                    validation_result["missing_env_vars"].append(var)
                    validation_result["valid"] = False

        # Check signing secret for webhook verification
        if (
            not os.environ.get("SLACK_SIGNING_SECRET")
            and not self.signing_secret
        ):
            validation_result["warnings"].append(
                "SLACK_SIGNING_SECRET not set - webhook signature verification disabled"
            )

        return validation_result

    @abstractmethod
    def get_tools(self) -> List[Any]:
        r"""Get the tools/functions provided by this Slack application.

        This method should be implemented by subclasses to return their specific
        tools, functions, or capabilities.

        Returns:
            List[Any]: List of tools/functions provided by the application.
        """
        pass
