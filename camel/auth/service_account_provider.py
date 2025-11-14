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

import json
import os
from typing import Any, Dict, Optional

from .base import (
    AuthenticationError,
    AuthenticationProvider,
    AuthenticationType,
)


class ServiceAccountProvider(AuthenticationProvider):
    """Authentication provider for service account-based authentication.

    Supports service account key files (JSON) and environment-based service account setup.
    Commonly used for Google Cloud Platform and other cloud services.
    """

    def __init__(
        self,
        provider_name: str,
        service_account_file_env_var: Optional[str] = None,
        service_account_info_env_var: Optional[str] = None,
        scopes: Optional[list[str]] = None,
    ):
        """Initialize service account authentication provider.

        Args:
            provider_name (str): Name of the provider
            service_account_file_env_var (Optional[str]): Environment variable
                containing path to service account JSON file
            service_account_info_env_var (Optional[str]): Environment variable
                containing service account JSON string
            scopes (Optional[list[str]]): Required scopes for authentication
        """
        required_env_vars = {}
        if service_account_file_env_var:
            required_env_vars["service_account_file"] = (
                service_account_file_env_var
            )
        if service_account_info_env_var:
            required_env_vars["service_account_info"] = (
                service_account_info_env_var
            )

        if not required_env_vars:
            # Default to looking for common service account environment variables
            required_env_vars["service_account_file"] = (
                "GOOGLE_APPLICATION_CREDENTIALS"
            )

        super().__init__(
            auth_type=AuthenticationType.SERVICE_ACCOUNT,
            provider_name=provider_name,
            required_env_vars=required_env_vars,
        )

        self.service_account_file_env_var = service_account_file_env_var
        self.service_account_info_env_var = service_account_info_env_var
        self.scopes = scopes or []

    def authenticate(self, **kwargs) -> bool:
        """Authenticate using service account credentials.

        Args:
            **kwargs: Service account parameters (service_account_file,
                     service_account_info, etc.)

        Returns:
            bool: True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        try:
            service_account_info = None

            # Try to get service account from file
            if self.service_account_file_env_var:
                service_account_file = kwargs.get(
                    "service_account_file"
                ) or os.environ.get(self.service_account_file_env_var)

                if service_account_file and os.path.exists(
                    service_account_file
                ):
                    with open(service_account_file, 'r') as f:
                        service_account_info = json.load(f)

            # Try to get service account from environment variable (JSON string)
            if not service_account_info and self.service_account_info_env_var:
                service_account_json = kwargs.get(
                    "service_account_info"
                ) or os.environ.get(self.service_account_info_env_var)

                if service_account_json:
                    service_account_info = json.loads(service_account_json)

            # Try default Google Application Credentials
            if not service_account_info:
                default_creds_file = os.environ.get(
                    "GOOGLE_APPLICATION_CREDENTIALS"
                )
                if default_creds_file and os.path.exists(default_creds_file):
                    with open(default_creds_file, 'r') as f:
                        service_account_info = json.load(f)

            if not service_account_info:
                missing_vars = self.get_missing_env_vars()
                raise AuthenticationError(
                    f"Service account credentials not found. Please set one of: "
                    f"{list(self.required_env_vars.values())} or provide "
                    f"service_account_file/service_account_info parameters. "
                    f"Missing: {missing_vars}",
                    provider_name=self.provider_name,
                    auth_type=self.auth_type,
                )

            # Validate service account info structure
            required_fields = [
                "type",
                "project_id",
                "private_key_id",
                "private_key",
                "client_email",
            ]
            for field in required_fields:
                if field not in service_account_info:
                    raise AuthenticationError(
                        f"Invalid service account file. Missing field: {field}",
                        provider_name=self.provider_name,
                        auth_type=self.auth_type,
                    )

            # Store credentials
            self._credentials = {
                "service_account_info": service_account_info,
                "scopes": self.scopes,
                "project_id": service_account_info.get("project_id"),
                "client_email": service_account_info.get("client_email"),
            }

            self._is_authenticated = True
            return True

        except json.JSONDecodeError as e:
            self._is_authenticated = False
            raise AuthenticationError(
                f"Invalid JSON in service account credentials: {e!s}",
                provider_name=self.provider_name,
                auth_type=self.auth_type,
            )
        except Exception as e:
            self._is_authenticated = False
            if isinstance(e, AuthenticationError):
                raise
            raise AuthenticationError(
                f"Failed to authenticate with service account: {e!s}",
                provider_name=self.provider_name,
                auth_type=self.auth_type,
            )

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests.

        Note: Service account authentication typically uses libraries like
        google-auth which handle token generation automatically.

        Returns:
            Dict[str, str]: Empty dict (service account auth is library-managed)

        Raises:
            AuthenticationError: If not authenticated
        """
        if not self._is_authenticated or not self._credentials:
            raise AuthenticationError(
                "Not authenticated. Call authenticate() first.",
                provider_name=self.provider_name,
                auth_type=self.auth_type,
            )

        # Service account authentication is typically handled by libraries
        # that automatically generate and refresh access tokens
        return {}

    def get_credentials(self) -> Dict[str, Any]:
        """Get authentication credentials.

        Returns:
            Dict[str, Any]: Service account credentials (without private key)

        Raises:
            AuthenticationError: If not authenticated
        """
        if not self._is_authenticated or not self._credentials:
            raise AuthenticationError(
                "Not authenticated. Call authenticate() first.",
                provider_name=self.provider_name,
                auth_type=self.auth_type,
            )

        # Return credentials without exposing private key
        safe_credentials = self._credentials.copy()
        if "service_account_info" in safe_credentials:
            service_account_info = safe_credentials[
                "service_account_info"
            ].copy()
            # Remove sensitive information from returned credentials
            service_account_info.pop("private_key", None)
            service_account_info.pop("private_key_id", None)
            safe_credentials["service_account_info"] = service_account_info

        return safe_credentials

    def get_service_account_info(self) -> Dict[str, Any]:
        """Get full service account information (including private key).

        Returns:
            Dict[str, Any]: Complete service account info

        Raises:
            AuthenticationError: If not authenticated
        """
        if not self._is_authenticated or not self._credentials:
            raise AuthenticationError(
                "Not authenticated. Call authenticate() first.",
                provider_name=self.provider_name,
                auth_type=self.auth_type,
            )

        return self._credentials["service_account_info"].copy()

    def refresh_credentials(self) -> bool:
        """Refresh credentials (re-read service account file).

        Returns:
            bool: True if refresh successful
        """
        try:
            return self.authenticate()
        except AuthenticationError:
            return False

    def get_project_id(self) -> str:
        """Get the project ID from service account.

        Returns:
            str: The project ID

        Raises:
            AuthenticationError: If not authenticated
        """
        credentials = self.get_credentials()
        return credentials["project_id"]

    def get_client_email(self) -> str:
        """Get the client email from service account.

        Returns:
            str: The client email

        Raises:
            AuthenticationError: If not authenticated
        """
        credentials = self.get_credentials()
        return credentials["client_email"]
