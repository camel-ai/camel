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

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from aiohttp import web

from camel.logger import get_logger
from camel.toolkits.slack_toolkit import SlackToolkit
from camel.triggers.adapters.slack_adapter import SlackAdapter
from camel.triggers.base_trigger import TriggerEvent, TriggerType
from camel.triggers.webhook_trigger import WebhookTrigger

logger = get_logger(__name__)


class SlackTrigger(WebhookTrigger):
    """Slack trigger that extends WebhookTrigger with Slack-specific processing.

    This trigger leverages the webhook infrastructure while adding Slack-specific
    functionality like authentication, event parsing, and integration with SlackToolkit.
    """

    def __init__(self, *args):
        super().__init__(*args)
        self.slack_adapter: Optional[SlackAdapter] = None
        self.slack_toolkit: Optional[SlackToolkit] = None
        self._slack_callbacks: List[
            Callable[[TriggerEvent, Dict[str, Any]], None]
        ] = []
        self._manual_mode = False

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate Slack trigger configuration"""
        # Allow manual mode without webhook
        manual_mode = config.get("manual_mode", False)
        if manual_mode:
            return True

        # For webhook mode, validate webhook config
        return super().validate_config(config)

    async def initialize(self) -> bool:
        """Initialize the Slack trigger with authentication and webhook setup"""
        if not self.validate_config(self.config):
            logger.error("Invalid Slack trigger configuration")
            return False

        # Initialize Slack adapter
        self.slack_adapter = SlackAdapter(
            slack_token=self.config.get("slack_token"),
            app_token=self.config.get("app_token"),
            signing_secret=self.config.get("signing_secret"),
        )

        # Authenticate with Slack
        if not await self.slack_adapter.authenticate():
            logger.error("Failed to authenticate with Slack")
            return False

        # Initialize Slack toolkit
        self.slack_toolkit = SlackToolkit(
            slack_token=self.config.get("slack_token"),
        )

        # Set manual mode flag
        self._manual_mode = self.config.get("manual_mode", False)

        # Initialize webhook if not in manual mode
        if not self._manual_mode:
            if not await super().initialize():
                logger.error("Failed to initialize webhook server")
                return False

        logger.info("Slack trigger initialized successfully")
        return True

    async def activate(self) -> bool:
        """Start listening for Slack events"""
        if not self.slack_adapter:
            if not await self.initialize():
                return False

        # Activate webhook server if not in manual mode
        if not self._manual_mode:
            return await super().activate()
        else:
            # Manual mode - just mark as active
            from camel.triggers.base_trigger import TriggerState

            self.state = TriggerState.ACTIVE
            logger.info("Slack trigger activated in manual mode")
            return True

    async def deactivate(self) -> bool:
        """Stop listening for Slack events"""
        if not self._manual_mode:
            return await super().deactivate()
        else:
            # Manual mode - just mark as inactive
            from camel.triggers.base_trigger import TriggerState

            self.state = TriggerState.INACTIVE
            logger.info("Slack trigger deactivated")
            return True

    async def test_connection(self) -> bool:
        """Test Slack API connection"""
        if not self.slack_adapter:
            return False

        # Test Slack connection
        slack_connected = self.slack_adapter.is_authenticated()

        # Test webhook connection if not in manual mode
        if not self._manual_mode:
            webhook_connected = await super().test_connection()
            return slack_connected and webhook_connected

        return slack_connected

    async def refresh_auth_token(self) -> bool:
        """Refresh Slack authentication token"""
        if not self.slack_adapter:
            logger.error("Slack adapter not initialized")
            return False

        logger.info("Refreshing Slack authentication token...")
        return await self.slack_adapter.refresh_auth_token()

    async def _handle_webhook(self, request: web.Request) -> web.Response:
        """Override webhook handler to add Slack-specific processing"""
        try:
            payload = await request.json()
            headers = dict(request.headers)

            # Parse Slack event using adapter
            parsed_event = None
            if self.slack_adapter:
                parsed_event = self.slack_adapter.parse_webhook_event(payload)

            # Handle URL verification challenge
            if parsed_event and parsed_event.get("type") == "url_verification":
                return web.json_response(
                    {"challenge": parsed_event["challenge"]}
                )

            # Process as standard webhook event with Slack-specific data
            event_data = {
                "payload": payload,
                "headers": headers,
                "method": request.method,
                "url": str(request.url),
                "parsed_event": parsed_event,
                "source": "slack_webhook",
            }

            event = await self.process_trigger_event(event_data)

            # Execute Slack-specific callbacks first
            await self._emit_slack_callbacks(event, parsed_event or {})

            # Then emit to standard callbacks
            await self._emit_trigger_event(event)

            return web.json_response({"status": "success"})
        except Exception as e:
            logger.error(f"Slack webhook error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def process_trigger_event(self, event_data: Any) -> TriggerEvent:
        """Process raw Slack data into standardized TriggerEvent"""
        payload = event_data.get("payload", {})
        parsed_event = event_data.get("parsed_event")

        # Extract meaningful information from Slack event
        metadata = {
            "source": event_data.get("source", "unknown"),
            "headers": event_data.get("headers", {}),
            "method": event_data.get("method"),
            "url": event_data.get("url"),
        }

        # Add Slack-specific metadata
        if parsed_event:
            metadata.update(
                {
                    "slack_event_type": parsed_event.get("type"),
                    "slack_event_subtype": parsed_event.get("event_type"),
                    "channel": parsed_event.get("channel"),
                    "user": parsed_event.get("user"),
                    "team_id": parsed_event.get("team_id"),
                    "trigger_id": parsed_event.get("trigger_id"),
                    "response_url": parsed_event.get("response_url"),
                }
            )

        # Generate correlation ID for tracking
        correlation_id = (
            f"slack_{self.trigger_id}_{datetime.now().timestamp()}"
        )

        return TriggerEvent(
            trigger_id=self.trigger_id,
            trigger_type=TriggerType.WEBHOOK,
            timestamp=datetime.now(),
            payload=payload,
            metadata=metadata,
            correlation_id=correlation_id,
        )

    # Slack-specific callback management
    def add_slack_callback(
        self, callback: Callable[[TriggerEvent, Dict[str, Any]], None]
    ):
        """Add Slack-specific callback that receives both TriggerEvent and parsed Slack event"""
        self._slack_callbacks.append(callback)

    def remove_slack_callback(
        self, callback: Callable[[TriggerEvent, Dict[str, Any]], None]
    ):
        """Remove Slack-specific callback"""
        if callback in self._slack_callbacks:
            self._slack_callbacks.remove(callback)

    async def _emit_slack_callbacks(
        self, event: TriggerEvent, parsed_slack_event: Dict[str, Any]
    ):
        """Emit events to Slack-specific callbacks"""
        for callback in self._slack_callbacks:
            try:
                if callable(callback):
                    if callable(callback):
                        await callback(event, parsed_slack_event)
                    else:
                        callback(event, parsed_slack_event)
            except Exception as e:
                logger.error(f"Error in Slack callback: {e}")

    # Slack-specific utility methods
    def get_adapter(self) -> Optional[SlackAdapter]:
        """Get the Slack adapter for direct access"""
        return self.slack_adapter

    async def execute_event(self, event_data: Optional[Dict[str, Any]] = None):
        """Execute manual event processing"""
        if event_data is None:
            # Get recent events and process them
            events = await self.get_events(limit=1)
            if not events:
                logger.info("No events to process")
                return
            event_data = events[0]

        try:
            # Process the event data
            processed_event = await self.process_trigger_event(
                {
                    "payload": event_data,
                    "source": "manual_execution",
                    "parsed_event": self.slack_adapter.parse_webhook_event(
                        event_data
                    )
                    if self.slack_adapter
                    else None,
                }
            )

            # Emit to callbacks
            await self._emit_trigger_event(processed_event)
            logger.info(
                f"Manual event processed: {processed_event.correlation_id}"
            )

        except Exception as e:
            logger.error(f"Error executing manual event: {e}")

    async def register_trigger_webhook(
        self, webhook_url: str
    ) -> Dict[str, Any]:
        """Register webhook URL with Slack (placeholder for future implementation)"""
        logger.info(f"Webhook URL for Slack configuration: {webhook_url}")
        return {
            "webhook_url": webhook_url,
            "status": "info_provided",
            "note": "Configure this URL in your Slack App's Event Subscriptions",
        }
