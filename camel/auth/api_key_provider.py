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


class ApiKeyProvider(AuthenticationProvider):
    """Authentication provider for API key-based authentication.

    Supports various API key formats:
    - Simple API key in header
    - API key with prefix (e.g., "Bearer", "Token")
    - API key in query parameters
    - Multiple API keys for different services
    """

    def __init__(
        self,
        provider_name: str,
        api_key_env_var: str,
        header_name: str = "Authorization",
        key_prefix: Optional[str] = None,
        additional_keys: Optional[Dict[str, str]] = None,
    ):
        """Initialize API key authentication provider.

        Args:
            provider_name (str): Name of the provider
            api_key_env_var (str): Environment variable containing the API key
            header_name (str): HTTP header name for the API key
            key_prefix (Optional[str]): Prefix for the API key (e.g., "Bearer")
            additional_keys (Optional[Dict[str, str]]): Additional API keys
                mapping parameter names to environment variable names
        """
        required_env_vars = {"api_key": api_key_env_var}
        optional_env_vars = additional_keys or {}

        super().__init__(
            auth_type=AuthenticationType.API_KEY,
            provider_name=provider_name,
            required_env_vars=required_env_vars,
            optional_env_vars=optional_env_vars,
        )

        self.header_name = header_name
        self.key_prefix = key_prefix
        self.api_key_env_var = api_key_env_var
        self.additional_keys = additional_keys or {}

    def authenticate(self, **kwargs) -> bool:
        """Authenticate using API key from environment variables or kwargs.

        Args:
            **kwargs: Optional API key parameters

        Returns:
            bool: True if authentication successful

        Raises:
            AuthenticationError: If API key is missing or invalid
        """
        try:
            # Get main API key
            api_key = kwargs.get("api_key") or os.environ.get(
                self.api_key_env_var
            )

            if not api_key or not api_key.strip():
                missing_vars = self.get_missing_env_vars()
                raise AuthenticationError(
                    f"API key not found. Please set {self.api_key_env_var} "
                    f"environment variable or pass 'api_key' parameter. "
                    f"Missing environment variables: {missing_vars}",
                    provider_name=self.provider_name,
                    auth_type=self.auth_type,
                )

            # Store credentials
            self._credentials = {"api_key": api_key.strip()}

            # Get additional keys if specified
            for param_name, env_var in self.additional_keys.items():
                additional_key = kwargs.get(param_name) or os.environ.get(
                    env_var
                )
                if additional_key:
                    self._credentials[param_name] = additional_key.strip()

            self._is_authenticated = True
            return True

        except Exception as e:
            self._is_authenticated = False
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError(
                f"Failed to authenticate with API key: {e!s}",
                provider_name=self.provider_name,
                auth_type=self.auth_type,
            )

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests.

        Returns:
            Dict[str, str]: Headers with API key

        Raises:
            AuthenticationError: If not authenticated
        """
        if not self._is_authenticated or not self._credentials:
            raise AuthenticationError(
                "Not authenticated. Call authenticate() first.",
                provider_name=self.provider_name,
                auth_type=self.auth_type,
            )

        api_key = self._credentials["api_key"]

        if self.key_prefix:
            header_value = f"{self.key_prefix} {api_key}"
        else:
            header_value = api_key

        return {self.header_name: header_value}

    def get_credentials(self) -> Dict[str, Any]:
        """Get authentication credentials.

        Returns:
            Dict[str, Any]: API key credentials

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

    def get_api_key(self) -> str:
        """Get the main API key.

        Returns:
            str: The API key

        Raises:
            AuthenticationError: If not authenticated
        """
        credentials = self.get_credentials()
        return credentials["api_key"]
