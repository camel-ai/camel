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

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional


class AuthenticationType(Enum):
    """Enumeration of supported authentication types."""

    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    TOKEN = "token"
    SERVICE_ACCOUNT = "service_account"
    BASIC_AUTH = "basic_auth"
    BEARER_TOKEN = "bearer_token"
    CUSTOM = "custom"


class AuthenticationProvider(ABC):
    """Abstract base class for authentication providers.

    All toolkit authentication mechanisms must extend this interface to provide
    a centralized authentication system across all toolkits.

    This interface supports various authentication methods including:
    - API Keys
    - OAuth2 flows
    - Bearer tokens
    - Service account credentials
    - Basic authentication
    - Custom authentication schemes
    """

    def __init__(
        self,
        auth_type: AuthenticationType,
        provider_name: str,
        required_env_vars: Optional[Dict[str, str]] = None,
        optional_env_vars: Optional[Dict[str, str]] = None,
    ):
        """Initialize the authentication provider.

        Args:
            auth_type (AuthenticationType): The type of authentication
            provider_name (str): Name of the provider
            (e.g., 'github', 'google')
            required_env_vars (Optional[Dict[str, str]]): Required environment
                variables mapping parameter names to env var names
            optional_env_vars (Optional[Dict[str, str]]): Optional environment
                variables mapping parameter names to env var names
        """
        self.auth_type = auth_type
        self.provider_name = provider_name
        self.required_env_vars = required_env_vars or {}
        self.optional_env_vars = optional_env_vars or {}
        self._credentials: Optional[Dict[str, Any]] = None
        self._is_authenticated = False

    @abstractmethod
    def authenticate(self, **kwargs) -> bool:
        """Authenticate using the provider's authentication method.

        Args:
            **kwargs: Provider-specific authentication parameters

        Returns:
            bool: True if authentication successful, False otherwise

        Raises:
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests.

        Returns:
            Dict[str, str]: Headers to include in authenticated requests

        Raises:
            AuthenticationError: If not authenticated
        """
        pass

    @abstractmethod
    def get_credentials(self) -> Dict[str, Any]:
        """Get authentication credentials.

        Returns:
            Dict[str, Any]: Authentication credentials

        Raises:
            AuthenticationError: If not authenticated
        """
        pass

    @abstractmethod
    def refresh_credentials(self) -> bool:
        """Refresh expired credentials if supported.

        Returns:
            bool: True if refresh successful, False otherwise
        """
        pass

    def is_authenticated(self) -> bool:
        """Check if provider is currently authenticated.

        Returns:
            bool: True if authenticated, False otherwise
        """
        return self._is_authenticated

    def get_required_env_vars(self) -> Dict[str, str]:
        """Get required environment variables for this provider.

        Returns:
            Dict[str, str]: Mapping of parameter names to env var names
        """
        return self.required_env_vars.copy()

    def get_optional_env_vars(self) -> Dict[str, str]:
        """Get optional environment variables for this provider.

        Returns:
            Dict[str, str]: Mapping of parameter names to env var names
        """
        return self.optional_env_vars.copy()

    def validate_environment(self) -> Dict[str, bool]:
        """Validate that required environment variables are set.

        Returns:
            Dict[str, bool]: Mapping of env var names to their presence
        """
        import os

        validation_result = {}

        # Check required environment variables
        for _param_name, env_var in self.required_env_vars.items():
            value = os.environ.get(env_var)
            validation_result[env_var] = bool(value and value.strip())

        # Check optional environment variables
        for _param_name, env_var in self.optional_env_vars.items():
            value = os.environ.get(env_var)
            validation_result[env_var] = bool(value and value.strip())

        return validation_result

    def get_missing_env_vars(self) -> list[str]:
        """Get list of missing required environment variables.

        Returns:
            list[str]: List of missing required environment variable names
        """
        validation = self.validate_environment()
        missing = []

        for env_var in self.required_env_vars.values():
            if not validation.get(env_var, False):
                missing.append(env_var)

        return missing

    def __repr__(self) -> str:
        """String representation of the authentication provider."""
        return (
            f"{self.__class__.__name__}("
            f"auth_type={self.auth_type.value}, "
            f"provider_name='{self.provider_name}', "
            f"authenticated={self._is_authenticated})"
        )


class AuthenticationError(Exception):
    """Exception raised for authentication-related errors."""

    def __init__(
        self,
        message: str,
        provider_name: Optional[str] = None,
        auth_type: Optional[AuthenticationType] = None,
    ):
        """Initialize authentication error.

        Args:
            message (str): Error message
            provider_name (Optional[str]): Name of the provider that failed
            auth_type (Optional[AuthenticationType]): Type of authentication
        """
        self.provider_name = provider_name
        self.auth_type = auth_type

        if provider_name and auth_type:
            full_message = f"[{provider_name}:{auth_type.value}] {message}"
        elif provider_name:
            full_message = f"[{provider_name}] {message}"
        else:
            full_message = message

        super().__init__(full_message)
