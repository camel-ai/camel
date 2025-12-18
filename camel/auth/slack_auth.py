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

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

from camel.auth.base import (
    AuthenticationError,
    AuthenticationProvider,
    AuthenticationType,
)
from camel.logger import get_logger
from camel.triggers.webhook_trigger import WebhookAuth

logger = get_logger(__name__)


class SlackAuth(AuthenticationProvider, WebhookAuth):
    """Slack authentication provider with integrated webhook support.

    Provides comprehensive Slack authentication including API access and
    webhook signature verification. Inherits from AuthenticationProvider
    for consistent authentication interface across all toolkits.
    """

    def __init__(
        self,
        signing_secret: Optional[str] = None,
        api_token: Optional[str] = None,
        bot_token: Optional[str] = None,
    ):
        """Initialize Slack authentication.

        Args:
            signing_secret (Optional[str]): Slack signing secret for webhook
            verification.
              If not provided, attempts to retrieve from SLACK_SIGNING_SECRET.
            api_token (Optional[str]): Slack API token for API access.
                If not provided, attempts to retrieve from SLACK_API_TOKEN.
            bot_token (Optional[str]): Slack bot token for bot API access.
                If not provided, attempts to retrieve from SLACK_BOT_TOKEN.
        """
        super().__init__(
            auth_type=AuthenticationType.TOKEN,
            provider_name="slack",
            required_env_vars={
                "signing_secret": "SLACK_SIGNING_SECRET",
            },
            optional_env_vars={
                "api_token": "SLACK_API_TOKEN",
                "bot_token": "SLACK_BOT_TOKEN",
            },
        )

        self.signing_secret = signing_secret or os.environ.get(
            "SLACK_SIGNING_SECRET"
        )
        self.api_token = api_token or os.environ.get("SLACK_API_TOKEN")
        self.bot_token = bot_token or os.environ.get("SLACK_BOT_TOKEN")

        # Mark as authenticated if we have any credentials
        self._is_authenticated = bool(
            self.signing_secret or self.api_token or self.bot_token
        )

    def authenticate(
        self, request_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Authenticate Slack webhook request or API access.

        Args:
            request_data (Optional[Dict[str, Any]]): Request data for webhook
            authentication.
                If None, performs general authentication check.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        if request_data is None:
            # General authentication check
            return self._is_authenticated

        # For webhook authentication, verify signature
        headers = request_data.get("headers", {})
        body = request_data.get("raw_body")

        if body is None:
            logger.warning("No raw body provided for authentication")
            return False

        if isinstance(body, str):
            body = body.encode("utf-8")

        return self.verify_signature(body, headers)

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests.

        Returns:
            Dict[str, str]: Headers to include in authenticated requests

        Raises:
            AuthenticationError: If not authenticated
        """
        if not self._is_authenticated:
            raise AuthenticationError(
                "Not authenticated",
                provider_name=self.provider_name,
                auth_type=self.auth_type,
            )

        headers = {}
        if self.bot_token:
            headers["Authorization"] = f"Bearer {self.bot_token}"
        elif self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        return headers

    def get_credentials(self) -> Dict[str, Any]:
        """Get authentication credentials.

        Returns:
            Dict[str, Any]: Authentication credentials

        Raises:
            AuthenticationError: If not authenticated
        """
        if not self._is_authenticated:
            raise AuthenticationError(
                "Not authenticated",
                provider_name=self.provider_name,
                auth_type=self.auth_type,
            )

        return {
            "signing_secret": self.signing_secret,
            "api_token": self.api_token,
            "bot_token": self.bot_token,
        }

    def refresh_credentials(self) -> bool:
        """Refresh expired credentials if supported.

        Returns:
            bool: True if refresh successful, False otherwise
        """
        # Slack tokens don't have automatic refresh mechanism
        # Would need to implement OAuth2 flow for proper token refresh
        logger.info("Slack tokens do not support automatic refresh")
        return False

    def verify_signature(
        self, request_body: bytes, headers: Dict[str, str]
    ) -> bool:
        """Verify Slack webhook signature.

        Args:
            request_body (bytes): Raw request body
            headers (Dict[str, str]): Request headers

        Returns:
            bool: True if signature is valid, False otherwise
        """
        if not self.signing_secret:
            logger.warning(
                "No Slack signing secret configured, skipping verification"
            )
            return True

        try:
            # Get required headers (case-insensitive lookup)
            headers_lower = {k.lower(): v for k, v in headers.items()}
            timestamp = headers_lower.get("x-slack-request-timestamp")
            signature = headers_lower.get("x-slack-signature")

            if not timestamp or not signature:
                logger.warning("Missing required Slack signature headers")
                return False

            # Verify timestamp freshness (prevent replay attacks)
            if abs(time.time() - int(timestamp)) > 300:  # 5 minutes
                logger.warning("Slack request timestamp expired")
                return False

            # Create signature
            body_str = request_body.decode("utf-8")
            sig_basestring = f"v0:{timestamp}:{body_str}"
            computed_signature = (
                'v0='
                + hmac.new(
                    self.signing_secret.encode(),
                    sig_basestring.encode(),
                    hashlib.sha256,
                ).hexdigest()
            )

            # Compare signatures
            return hmac.compare_digest(computed_signature, signature)

        except Exception as e:
            logger.error(f"Error verifying Slack webhook signature: {e}")
            return False

    def verify_webhook_request(self, request: Any, raw_body: bytes) -> bool:
        """Verify the webhook request signature (compatibility method).

        Args:
            request (Any): The request object containing headers
            raw_body (bytes): The raw request body

        Returns:
            bool: True if the signature is valid, False otherwise
        """
        try:
            headers = {}
            if hasattr(request, 'headers'):
                headers = dict(request.headers)

            return self.verify_signature(raw_body, headers)
        except Exception as e:
            logger.error(f"Error verifying Slack webhook: {e}")
            return False

    def get_verification_response(
        self, request: Any, raw_body: bytes
    ) -> Optional[Dict[str, Any]]:
        """Check for URL verification request and return challenge response.

        Args:
            request (Any): The request object.
            raw_body (bytes): The raw request body.

        Returns:
            Optional[Dict[str, Any]]: Challenge response if it's a verification
                request, None otherwise.
        """
        try:
            body_str = raw_body.decode("utf-8")
            payload = json.loads(body_str)
            if payload.get("type") == "url_verification":
                return {"challenge": payload.get("challenge")}
        except Exception:
            pass
        return None
