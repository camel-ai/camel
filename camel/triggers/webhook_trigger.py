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
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from aiohttp import web
from pydantic import BaseModel, Field

from camel.logger import get_logger
from camel.triggers.base_trigger import (
    BaseTrigger,
    TriggerEvent,
    TriggerState,
    TriggerType,
)

logger = get_logger(__name__)


class HttpMethod(Enum):
    """Supported HTTP methods for webhook endpoints."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class WebhookConfig(BaseModel):
    """Configuration for webhook-specific parameters."""

    allowed_methods: List[HttpMethod] = [HttpMethod.POST]
    max_payload_size: int = Field(
        default=1024 * 1024, ge=1, le=10 * 1024 * 1024
    )  # 1MB default, max 10MB
    custom_headers: Optional[Dict[str, str]] = None


class WebhookAuth(ABC):
    """Interface for webhook authentication handlers."""

    @abstractmethod
    def verify_webhook_request(self, request: Any, raw_body: bytes) -> bool:
        """Verify the webhook request.

        Args:
            request (Any): The request object.
            raw_body (bytes): The raw request body.

        Returns:
            bool: True if valid, False otherwise.
        """
        pass

    def get_verification_response(
        self, request: Any, raw_body: bytes
    ) -> Optional[Dict[str, Any]]:
        """Get the response for a verification request if applicable.

        Args:
            request (Any): The request object.
            raw_body (bytes): The raw request body.

        Returns:
            Optional[Dict[str, Any]]: The response dictionary if a verification
                response is needed, None otherwise.
        """
        return None


class WebhookTrigger(BaseTrigger):
    """Webhook trigger for handling external HTTP events.

    This trigger creates an HTTP server endpoint that listens for incoming
    webhook requests and processes them as trigger events. Supports JSON
    payloads and provides comprehensive request metadata in trigger events.
    """

    def __init__(
        self,
        trigger_id: str,
        name: str,
        description: str,
        port: int,
        path: str,
        host: str = "localhost",
        webhook_config: Optional[WebhookConfig] = None,
        auth_handler: Optional[WebhookAuth] = None,
    ) -> None:
        """
        Initialize WebhookTrigger with HTTP server configuration.

        Args:
            trigger_id (str): Unique identifier for the trigger instance.
                Must be unique across all triggers in the system.
            name (str): Human-readable name for the trigger.
                Used for display and logging purposes.
            description (str): Detailed description of the trigger's purpose.
                Should explain what events this webhook handles.
            port (int): Port number for the webhook server (1-65535).
                Must be available and not in use by other services.
            path (str): URL path for webhook endpoint (e.g., "/webhook").
                Must start with '/' and be a valid URL path.
            host (str, optional): Host interface to bind to.
                Use "localhost" for local only, "0.0.0.0" for all interfaces.
                Defaults to "localhost".
            webhook_config (Optional[WebhookConfig], optional): Advanced
                webhook configuration including payload limits and custom
                headers. Defaults to None (uses default WebhookConfig).
            auth_handler (Optional[WebhookAuth], optional): Custom
                authentication handler implementing WebhookAuth interface.
                Defaults to None.

        Raises:
            ValueError: If port is not in valid range (1-65535) or path doesn't
                start with '/'.

        Example:
            >>> trigger = WebhookTrigger(
            ...     trigger_id="github-webhook",
            ...     name="GitHub Events",
            ...     description="Handle GitHub webhook notifications",
            ...     port=8080,
            ...     path="/github-webhook",
            ...     host="0.0.0.0"
            ... )
        """
        if not (1 <= port <= 65535):
            raise ValueError("Port must be in range 1-65535")
        if not path.startswith("/"):
            raise ValueError("Path must start with '/'")

        # Use default webhook config if none provided
        if webhook_config is None:
            webhook_config = WebhookConfig()

        # Create config dictionary for base class
        config_dict = {
            "port": port,
            "path": path,
            "host": host,
            "webhook_config": webhook_config.dict(),
        }

        super().__init__(
            trigger_id=trigger_id,
            name=name,
            description=description,
            config=config_dict,
        )

        # Store typed attributes for easy access
        self.port: int = port
        self.path: str = path
        self.host: str = host
        self.webhook_config: WebhookConfig = webhook_config
        self.auth_handler: Optional[WebhookAuth] = auth_handler
        self.server: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate webhook configuration parameters.

        Args:
            config (Dict[str, Any]): Configuration dictionary to validate.
                Must contain:
                - port (int): Valid port number (1-65535)
                - path (str): URL path starting with '/'
                - host (str): Host interface identifier
                Optional:
                - webhook_config (dict): Webhook-specific configuration

        Returns:
            bool: True if all required fields present and valid, False
                otherwise.

        Note:
            Validates presence of required fields and basic format
                requirements.
            Port range and path format validation is performed in __init__.
        """
        required_fields: List[str] = ["port", "path", "host"]
        if not all(field in config for field in required_fields):
            return False

        port = config.get("port")
        path = config.get("path")

        if not isinstance(port, int) or not (1 <= port <= 65535):
            return False

        if not isinstance(path, str) or not path.startswith("/"):
            return False

        return True

    async def initialize(self) -> bool:
        """Initialize the webhook HTTP server and routing.

        Returns:
            bool: True if initialization successful, False if config
                validation fails.

        Side Effects:
            - Creates aiohttp Application instance
            - Configures POST route for webhook endpoint
            - Sets up request handler for the specified path

        Note:
            Server is created but not started. Call activate() to begin
            listening for requests.
        """
        if not self.validate_config(self.config):
            return False

        self.server = web.Application()
        # Add routes for all allowed HTTP methods
        for method in self.webhook_config.allowed_methods:
            if method == HttpMethod.GET:
                self.server.router.add_get(self.path, self._handle_webhook)
            elif method == HttpMethod.POST:
                self.server.router.add_post(self.path, self._handle_webhook)
            elif method == HttpMethod.PUT:
                self.server.router.add_put(self.path, self._handle_webhook)
            elif method == HttpMethod.PATCH:
                self.server.router.add_patch(self.path, self._handle_webhook)
            elif method == HttpMethod.DELETE:
                self.server.router.add_delete(self.path, self._handle_webhook)
        return True

    async def activate(self) -> bool:
        """Activate the webhook server and start listening for requests.

        Returns:
            bool: True when server is successfully started and listening.

        Side Effects:
            - Initializes server if not already done
            - Creates and starts AppRunner for the application
            - Binds TCPSite to configured host and port
            - Sets state to TriggerState.ACTIVE

        Raises:
            OSError: If port is already in use or binding fails.

        Note:
            Server will accept POST requests at the configured path.
            Use deactivate() to stop the server gracefully.
        """
        if not self.server:
            await self.initialize()

        self.runner = web.AppRunner(self.server)
        await self.runner.setup()

        self.site = web.TCPSite(
            self.runner,
            self.host,
            self.port,
        )
        await self.site.start()
        self.state = TriggerState.ACTIVE
        return True

    async def deactivate(self) -> bool:
        """Deactivate the webhook server and stop listening for requests.

        Returns:
            bool: True when server is successfully stopped.

        Side Effects:
            - Stops the TCP site to cease accepting new connections
            - Cleans up the AppRunner and associated resources
            - Sets state to TriggerState.INACTIVE

        Note:
            Performs graceful shutdown, allowing in-flight requests to
                complete.
            Server resources are properly cleaned up to prevent memory leaks.
        """
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        self.state = TriggerState.INACTIVE
        return True

    async def test_connection(self) -> bool:
        """Test webhook server connectivity and port availability.

        Returns:
            bool: True if port is available and server can bind, False
                otherwise.

        Note:
            Creates a temporary test server on the configured port to verify
            availability. The test server is immediately shut down after
                the check.
            This validates that the webhook can be activated without conflicts.
        """
        # Test if port is available
        try:
            test_app = web.Application()
            test_runner = web.AppRunner(test_app)
            await test_runner.setup()
            test_site = web.TCPSite(test_runner, self.host, self.port)
            await test_site.start()
            await test_site.stop()
            await test_runner.cleanup()
            return True
        except Exception as e:
            logger.debug(f"Connection test failed: {e}")
            return False

    async def _handle_webhook(self, request: web.Request) -> web.Response:
        """Handle incoming webhook HTTP requests.

        Args:
            request (web.Request): The incoming HTTP request from aiohttp.
                Expected to contain JSON or form-encoded payload.

        Returns:
            web.Response: JSON response with success status or error details.
                Success: {"status": "success"} with 200 status code
                Error: {"error": "error_message"} with appropriate status code

        Side Effects:
            - Authenticates request if configured
            - Parses payload according to content type
            - Processes payload according to configuration
            - Creates and emits TriggerEvent
            - Logs errors if processing fails

        Note:
            Supports multiple content types and configurable authentication.
        """
        try:
            # Get raw body for authentication
            raw_body = await request.read()

            # Check payload size limit
            if len(raw_body) > self.webhook_config.max_payload_size:
                logger.warning(
                    f"Payload size {len(raw_body)} exceeds limit "
                    f"{self.webhook_config.max_payload_size}"
                )
                return web.json_response(
                    {"error": "Payload too large"},
                    status=413,
                    headers=self.webhook_config.custom_headers or {},
                )

            headers: Dict[str, str] = dict(request.headers)

            # Authenticate request if required
            if (
                self.auth_handler
                and not self.auth_handler.verify_webhook_request(
                    request, raw_body
                )
            ):
                logger.warning("Webhook authentication failed")
                return web.json_response(
                    {"error": "Authentication failed"},
                    status=403,
                    headers=self.webhook_config.custom_headers or {},
                )

            if self.auth_handler:
                verification_resp = (
                    self.auth_handler.get_verification_response(
                        request, raw_body
                    )
                )
                if verification_resp is not None:
                    return web.json_response(verification_resp)

            # Parse payload based on content type
            content_type = request.headers.get(
                'content-type', 'application/json'
            )
            if 'application/json' in content_type:
                try:
                    payload = await request.json()
                except Exception:
                    logger.error("Failed to parse JSON payload")
                    return web.json_response(
                        {"error": "Invalid JSON payload"},
                        status=400,
                        headers=self.webhook_config.custom_headers or {},
                    )
            elif 'application/x-www-form-urlencoded' in content_type:
                form_data = await request.post()
                payload = dict(form_data)
            else:
                payload = {
                    "raw_body": raw_body.decode('utf-8', errors='ignore')
                }

            # Use payload as-is without provider-specific processing
            processed_payload = payload

            event_data: Dict[str, Any] = {
                "payload": processed_payload,
                "headers": headers,
                "method": request.method,
                "url": str(request.url),
                "raw_payload": payload,
            }

            event: TriggerEvent = await self.process_trigger_event(event_data)
            await self._emit_trigger_event(event)

            # Return default success response
            return web.json_response(
                {"status": "success"},
                status=200,
                headers=self.webhook_config.custom_headers or {},
            )

        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return web.json_response(
                {"error": str(e)},
                status=500,
                headers=self.webhook_config.custom_headers or {},
            )

    async def process_trigger_event(
        self, event_data: Dict[str, Any]
    ) -> TriggerEvent:
        """Process webhook request data into standardized TriggerEvent.

        Args:
            event_data (Dict[str, Any]): Raw webhook request data containing:
                - payload (Dict[str, Any]): Processed payload from request body
                - headers (Dict[str, str]): HTTP headers from the request
                - method (str): HTTP method (typically "POST")
                - url (str): Full request URL including query parameters
                - raw_payload (Dict[str, Any]): Original unprocessed payload

        Returns:
            TriggerEvent: Standardized trigger event with webhook-specific
                metadata.

        Note:
            Separates the main payload from HTTP metadata for cleaner event
                processing.
            The payload becomes the primary event data, while HTTP details are
            preserved in metadata for debugging and routing purposes.
        """
        return TriggerEvent(
            trigger_id=self.trigger_id,
            trigger_type=TriggerType.WEBHOOK,
            timestamp=datetime.now(),
            payload=event_data["payload"],
            metadata={
                "headers": event_data["headers"],
                "method": event_data["method"],
                "url": event_data["url"],
                "raw_payload": event_data.get("raw_payload"),
            },
        )

    def get_webhook_config(self) -> WebhookConfig:
        """Get the structured webhook configuration.

        Returns:
            WebhookConfig: The webhook configuration object.
        """
        return self.webhook_config
