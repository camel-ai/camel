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

from typing import Any, Dict, List, Optional, Type

from .api_key_provider import ApiKeyProvider
from .base import (
    AuthenticationError,
    AuthenticationProvider,
    AuthenticationType,
)
from .oauth2_provider import OAuth2Provider
from .service_account_provider import ServiceAccountProvider
from .token_provider import TokenProvider


class AuthenticationManager:
    """Centralized manager for handling multiple authentication providers.

    This class provides a unified interface for managing authentication across
    different toolkits and services. It supports provider registration,
    credential validation, and authentication status management.
    """

    def __init__(self):
        """Initialize the authentication manager."""
        self._providers: Dict[str, AuthenticationProvider] = {}
        self._provider_registry: Dict[
            AuthenticationType, Type[AuthenticationProvider]
        ] = {
            AuthenticationType.API_KEY: ApiKeyProvider,
            AuthenticationType.TOKEN: TokenProvider,
            AuthenticationType.OAUTH2: OAuth2Provider,
            AuthenticationType.SERVICE_ACCOUNT: ServiceAccountProvider,
        }

    def register_provider(
        self, provider_name: str, provider: AuthenticationProvider
    ) -> None:
        """Register an authentication provider.

        Args:
            provider_name (str): Unique name for the provider
            provider (AuthenticationProvider): The authentication provider

        Raises:
            ValueError: If provider name already exists
        """
        if provider_name in self._providers:
            raise ValueError(f"Provider '{provider_name}' already registered")

        self._providers[provider_name] = provider

    def create_provider(
        self, provider_name: str, auth_type: AuthenticationType, **config
    ) -> AuthenticationProvider:
        """Create and register a new authentication provider.

        Args:
            provider_name (str): Unique name for the provider
            auth_type (AuthenticationType): Type of authentication
            **config: Provider-specific configuration

        Returns:
            AuthenticationProvider: The created provider

        Raises:
            ValueError: If auth_type is not supported
        """
        if auth_type not in self._provider_registry:
            raise ValueError(f"Unsupported authentication type: {auth_type}")

        provider_class = self._provider_registry[auth_type]
        provider = provider_class(provider_name=provider_name, **config)

        self.register_provider(provider_name, provider)
        return provider

    def get_provider(self, provider_name: str) -> AuthenticationProvider:
        """Get a registered authentication provider.

        Args:
            provider_name (str): Name of the provider

        Returns:
            AuthenticationProvider: The authentication provider

        Raises:
            ValueError: If provider not found
        """
        if provider_name not in self._providers:
            raise ValueError(f"Provider '{provider_name}' not found")

        return self._providers[provider_name]

    def authenticate_provider(self, provider_name: str, **kwargs) -> bool:
        """Authenticate a specific provider.

        Args:
            provider_name (str): Name of the provider to authenticate
            **kwargs: Authentication parameters

        Returns:
            bool: True if authentication successful

        Raises:
            ValueError: If provider not found
            AuthenticationError: If authentication fails
        """
        provider = self.get_provider(provider_name)
        return provider.authenticate(**kwargs)

    def authenticate_all(self, **kwargs) -> Dict[str, bool]:
        """Authenticate all registered providers.

        Args:
            **kwargs: Authentication parameters (will be passed to all providers)

        Returns:
            Dict[str, bool]: Authentication results for each provider
        """
        results = {}

        for provider_name, provider in self._providers.items():
            try:
                results[provider_name] = provider.authenticate(**kwargs)
            except AuthenticationError:
                results[provider_name] = False

        return results

    def is_provider_authenticated(self, provider_name: str) -> bool:
        """Check if a provider is authenticated.

        Args:
            provider_name (str): Name of the provider

        Returns:
            bool: True if provider is authenticated

        Raises:
            ValueError: If provider not found
        """
        provider = self.get_provider(provider_name)
        return provider.is_authenticated()

    def get_authentication_status(self) -> Dict[str, bool]:
        """Get authentication status for all providers.

        Returns:
            Dict[str, bool]: Authentication status for each provider
        """
        return {
            name: provider.is_authenticated()
            for name, provider in self._providers.items()
        }

    def get_auth_headers(self, provider_name: str) -> Dict[str, str]:
        """Get authentication headers for a specific provider.

        Args:
            provider_name (str): Name of the provider

        Returns:
            Dict[str, str]: Authentication headers

        Raises:
            ValueError: If provider not found
            AuthenticationError: If provider not authenticated
        """
        provider = self.get_provider(provider_name)
        return provider.get_auth_headers()

    def get_credentials(self, provider_name: str) -> Dict[str, Any]:
        """Get credentials for a specific provider.

        Args:
            provider_name (str): Name of the provider

        Returns:
            Dict[str, Any]: Provider credentials

        Raises:
            ValueError: If provider not found
            AuthenticationError: If provider not authenticated
        """
        provider = self.get_provider(provider_name)
        return provider.get_credentials()

    def refresh_provider(self, provider_name: str) -> bool:
        """Refresh credentials for a specific provider.

        Args:
            provider_name (str): Name of the provider

        Returns:
            bool: True if refresh successful

        Raises:
            ValueError: If provider not found
        """
        provider = self.get_provider(provider_name)
        return provider.refresh_credentials()

    def refresh_all(self) -> Dict[str, bool]:
        """Refresh credentials for all providers.

        Returns:
            Dict[str, bool]: Refresh results for each provider
        """
        results = {}

        for provider_name, provider in self._providers.items():
            results[provider_name] = provider.refresh_credentials()

        return results

    def validate_environment(self) -> Dict[str, Dict[str, bool]]:
        """Validate environment variables for all providers.

        Returns:
            Dict[str, Dict[str, bool]]: Environment validation for each provider
        """
        results = {}

        for provider_name, provider in self._providers.items():
            results[provider_name] = provider.validate_environment()

        return results

    def get_missing_env_vars(self) -> Dict[str, List[str]]:
        """Get missing environment variables for all providers.

        Returns:
            Dict[str, List[str]]: Missing env vars for each provider
        """
        results = {}

        for provider_name, provider in self._providers.items():
            missing = provider.get_missing_env_vars()
            if missing:
                results[provider_name] = missing

        return results

    def list_providers(self) -> List[str]:
        """List all registered provider names.

        Returns:
            List[str]: Names of all registered providers
        """
        return list(self._providers.keys())

    def get_provider_info(self, provider_name: str) -> Dict[str, Any]:
        """Get information about a specific provider.

        Args:
            provider_name (str): Name of the provider

        Returns:
            Dict[str, Any]: Provider information

        Raises:
            ValueError: If provider not found
        """
        provider = self.get_provider(provider_name)

        return {
            "name": provider_name,
            "auth_type": provider.auth_type.value,
            "provider_name": provider.provider_name,
            "authenticated": provider.is_authenticated(),
            "required_env_vars": provider.get_required_env_vars(),
            "optional_env_vars": provider.get_optional_env_vars(),
            "missing_env_vars": provider.get_missing_env_vars(),
        }

    def remove_provider(self, provider_name: str) -> None:
        """Remove a registered provider.

        Args:
            provider_name (str): Name of the provider to remove

        Raises:
            ValueError: If provider not found
        """
        if provider_name not in self._providers:
            raise ValueError(f"Provider '{provider_name}' not found")

        del self._providers[provider_name]

    def clear_all(self) -> None:
        """Remove all registered providers."""
        self._providers.clear()


# Global authentication manager instance
_global_auth_manager: Optional[AuthenticationManager] = None


def get_auth_manager() -> AuthenticationManager:
    """Get the global authentication manager instance.

    Returns:
        AuthenticationManager: The global authentication manager
    """
    global _global_auth_manager
    if _global_auth_manager is None:
        _global_auth_manager = AuthenticationManager()
    return _global_auth_manager


def register_auth_provider(
    provider_name: str, auth_type: AuthenticationType, **config
) -> AuthenticationProvider:
    """Convenience function to register an authentication provider globally.

    Args:
        provider_name (str): Unique name for the provider
        auth_type (AuthenticationType): Type of authentication
        **config: Provider-specific configuration

    Returns:
        AuthenticationProvider: The created provider
    """
    manager = get_auth_manager()
    return manager.create_provider(provider_name, auth_type, **config)
