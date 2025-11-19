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
from typing import Any, Dict, Optional

from .base import (
    AuthenticationError,
    AuthenticationProvider,
    AuthenticationType,
)


class OAuth2Provider(AuthenticationProvider):
    """Authentication provider for OAuth2-based authentication.

    Supports various OAuth2 flows including:
    - Authorization code flow
    - Client credentials flow
    - Refresh token flow
    """

    def __init__(
        self,
        provider_name: str,
        client_id_env_var: str,
        client_secret_env_var: str,
        token_uri: str = "https://oauth2.googleapis.com/token",
        refresh_token_env_var: Optional[str] = None,
        scopes: Optional[list[str]] = None,
    ):
        """Initialize OAuth2 authentication provider.

        Args:
            provider_name (str): Name of the provider
            client_id_env_var (str): Environment variable for client ID
            client_secret_env_var (str): Environment variable for client secret
            token_uri (str): Token endpoint URI
            refresh_token_env_var (Optional[str]): Environment variable for refresh token
            scopes (Optional[list[str]]): OAuth2 scopes
        """
        required_env_vars = {
            "client_id": client_id_env_var,
            "client_secret": client_secret_env_var,
        }

        optional_env_vars = {}
        if refresh_token_env_var:
            optional_env_vars["refresh_token"] = refresh_token_env_var

        super().__init__(
            auth_type=AuthenticationType.OAUTH2,
            provider_name=provider_name,
            required_env_vars=required_env_vars,
            optional_env_vars=optional_env_vars,
        )

        self.client_id_env_var = client_id_env_var
        self.client_secret_env_var = client_secret_env_var
        self.refresh_token_env_var = refresh_token_env_var
        self.token_uri = token_uri
        self.scopes = scopes or []

    def authenticate(self, **kwargs) -> bool:
        """Authenticate using OAuth2 credentials.

        Args:
            **kwargs: OAuth2 parameters (client_id, client_secret, refresh_token, etc.)

        Returns:
            bool: True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            # Get required credentials
            client_id = kwargs.get("client_id") or os.environ.get(
                self.client_id_env_var
            )
            client_secret = kwargs.get("client_secret") or os.environ.get(
                self.client_secret_env_var
            )

            if not client_id or not client_secret:
                missing_vars = self.get_missing_env_vars()
                raise AuthenticationError(
                    f"OAuth2 credentials not found. Please set required environment "
                    f"variables: {list(self.required_env_vars.values())}. "
                    f"Missing: {missing_vars}",
                    provider_name=self.provider_name,
                    auth_type=self.auth_type,
                )

            # Get optional refresh token
            refresh_token = None
            if self.refresh_token_env_var:
                refresh_token = kwargs.get("refresh_token") or os.environ.get(
                    self.refresh_token_env_var
                )

            # Store credentials
            self._credentials = {
                "client_id": client_id.strip(),
                "client_secret": client_secret.strip(),
                "token_uri": self.token_uri,
                "scopes": self.scopes,
            }

            if refresh_token:
                self._credentials["refresh_token"] = refresh_token.strip()

            # If refresh token is available, try to get access token
            if refresh_token:
                success = self._refresh_access_token()
                if success:
                    self._is_authenticated = True
                    return True

            # Mark as authenticated with credentials (access token may be obtained later)
            self._is_authenticated = True
            return True

        except Exception as e:
            self._is_authenticated = False
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError(
                f"Failed to authenticate with OAuth2: {e!s}",
                provider_name=self.provider_name,
                auth_type=self.auth_type,
            )

    def _refresh_access_token(self) -> bool:
        """Refresh access token using refresh token.

        Returns:
            bool: True if refresh successful
        """
        if not self._credentials or "refresh_token" not in self._credentials:
            return False

        try:
            # This would typically use a library like google-auth or requests-oauthlib
            # For now, we'll store the refresh token and mark as ready for refresh
            self._credentials["access_token_refreshable"] = True
            return True
        except Exception:
            return False

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests.

        Returns:
            Dict[str, str]: Headers with access token

        Raises:
            AuthenticationError: If not authenticated or no access token
        """
        if not self._is_authenticated or not self._credentials:
            raise AuthenticationError(
                "Not authenticated. Call authenticate() first.",
                provider_name=self.provider_name,
                auth_type=self.auth_type,
            )

        # If we have an access token, use it
        if "access_token" in self._credentials:
            return {
                "Authorization": f"Bearer {self._credentials['access_token']}"
            }

        # Otherwise, this provider needs external token management
        raise AuthenticationError(
            "No access token available. OAuth2 flow needs to be completed.",
            provider_name=self.provider_name,
            auth_type=self.auth_type,
        )

    def get_credentials(self) -> Dict[str, Any]:
        """Get authentication credentials.

        Returns:
            Dict[str, Any]: OAuth2 credentials

        Raises:
            AuthenticationError: If not authenticated
        """
        if not self._is_authenticated or not self._credentials:
            raise AuthenticationError(
                "Not authenticated. Call authenticate() first.",
                provider_name=self.provider_name,
                auth_type=self.auth_type,
            )

        return self._credentials.copy()

    def refresh_credentials(self) -> bool:
        """Refresh OAuth2 access token.

        Returns:
            bool: True if refresh successful
        """
        if not self._is_authenticated:
            return False

        return self._refresh_access_token()

    def set_access_token(
        self, access_token: str, expires_in: Optional[int] = None
    ) -> None:
        """Set access token (used after completing OAuth2 flow).

        Args:
            access_token (str): The access token
            expires_in (Optional[int]): Token expiration in seconds
        """
        if not self._credentials:
            raise AuthenticationError(
                "OAuth2 credentials not initialized. Call authenticate() first.",
                provider_name=self.provider_name,
                auth_type=self.auth_type,
            )

        self._credentials["access_token"] = access_token
        if expires_in:
            import time

            self._credentials["expires_at"] = time.time() + expires_in

    def is_token_expired(self) -> bool:
        """Check if access token is expired.

        Returns:
            bool: True if token is expired or expiration unknown
        """
        if not self._credentials or "expires_at" not in self._credentials:
            return True

        import time

        return time.time() >= self._credentials["expires_at"]
