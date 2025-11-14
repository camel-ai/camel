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
from typing import Any, Dict

from .base import (
    AuthenticationError,
    AuthenticationProvider,
    AuthenticationType,
)


class TokenProvider(AuthenticationProvider):
    """Authentication provider for token-based authentication.

    Supports bearer tokens, access tokens, and other token-based schemes.
    Similar to API key but specifically for token authentication patterns.
    """

    def __init__(
        self,
        provider_name: str,
        token_env_var: str,
        token_type: str = "Bearer",
        header_name: str = "Authorization",
    ):
        """Initialize token authentication provider.

        Args:
            provider_name (str): Name of the provider
            token_env_var (str): Environment variable containing the token
            token_type (str): Type of token (e.g., "Bearer", "Token")
            header_name (str): HTTP header name for the token
        """
        required_env_vars = {"token": token_env_var}

        super().__init__(
            auth_type=AuthenticationType.TOKEN,
            provider_name=provider_name,
            required_env_vars=required_env_vars,
        )

        self.token_env_var = token_env_var
        self.token_type = token_type
        self.header_name = header_name

    def authenticate(self, **kwargs) -> bool:
        """Authenticate using token from environment variables or kwargs.

        Args:
            **kwargs: Optional token parameters

        Returns:
            bool: True if authentication successful

        Raises:
            AuthenticationError: If token is missing or invalid
        """
        try:
            # Get token from kwargs or environment
            token = kwargs.get("token") or os.environ.get(self.token_env_var)

            if not token or not token.strip():
                missing_vars = self.get_missing_env_vars()
                raise AuthenticationError(
                    f"Token not found. Please set {self.token_env_var} "
                    f"environment variable or pass 'token' parameter. "
                    f"Missing environment variables: {missing_vars}",
                    provider_name=self.provider_name,
                    auth_type=self.auth_type,
                )

            # Store credentials
            self._credentials = {
                "token": token.strip(),
                "token_type": self.token_type,
            }

            self._is_authenticated = True
            return True

        except Exception as e:
            self._is_authenticated = False
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError(
                f"Failed to authenticate with token: {e!s}",
                provider_name=self.provider_name,
                auth_type=self.auth_type,
            )

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests.

        Returns:
            Dict[str, str]: Headers with token

        Raises:
            AuthenticationError: If not authenticated
        """
        if not self._is_authenticated or not self._credentials:
            raise AuthenticationError(
                "Not authenticated. Call authenticate() first.",
                provider_name=self.provider_name,
                auth_type=self.auth_type,
            )

        token = self._credentials["token"]
        token_type = self._credentials["token_type"]

        return {self.header_name: f"{token_type} {token}"}

    def get_credentials(self) -> Dict[str, Any]:
        """Get authentication credentials.

        Returns:
            Dict[str, Any]: Token credentials

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
        """Refresh credentials (re-read from environment).

        Returns:
            bool: True if refresh successful
        """
        try:
            return self.authenticate()
        except AuthenticationError:
            return False

    def get_token(self) -> str:
        """Get the access token.

        Returns:
            str: The access token

        Raises:
            AuthenticationError: If not authenticated
        """
        credentials = self.get_credentials()
        return credentials["token"]
