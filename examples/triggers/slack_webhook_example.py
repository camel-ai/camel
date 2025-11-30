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
"""Example demonstrating Slack webhook integration with CAMEL triggers.

This example shows how to create a webhook trigger that can handle Slack
events with proper authentication and payload processing.
"""

import asyncio
import os
from typing import Any, Dict

from camel.auth.slack_auth import SlackAuth
from camel.logger import get_logger
from camel.triggers.base_trigger import TriggerEvent
from camel.triggers.trigger_manager import CallbackHandlerType, TriggerManager
from camel.triggers.webhook_trigger import (
    HttpMethod,
    WebhookConfig,
    WebhookTrigger,
)

logger = get_logger(__name__)


class SlackEventHandler:
    """Handler for Slack webhook events."""

    def __init__(self):
        self.received_events = []
        self.response_text = None  # Store response text for webhook response

    async def handle_event(self, event_data: TriggerEvent) -> None:
        """Handle incoming Slack event."""
        payload = event_data.payload
        event_type = payload.get('type', 'unknown')

        logger.info(f"Received Slack event: {event_type}")

        # Handle different Slack event types
        if event_type == 'url_verification':
            logger.info("Slack URL verification challenge received")
        elif event_type == 'event_callback':
            self._handle_event_callback(payload)
        elif event_type == 'message':
            self._handle_message_event(payload)

        self.received_events.append(event_data)

    def _handle_event_callback(self, payload: Dict[str, Any]) -> None:
        """Handle Slack Event API callbacks."""
        event = payload.get('event', {})
        event_type = event.get('type')

        if event_type == 'message':
            user = event.get('user', 'unknown')
            text = event.get('text', '')
            channel = event.get('channel', 'unknown')
            logger.info(f"Message from {user} in {channel}: {text}")
        elif event_type == 'app_mention':
            user = event.get('user', 'unknown')
            text = event.get('text', '')
            logger.info(f"App mentioned by {user}: {text}")

    def _handle_message_event(self, payload: Dict[str, Any]) -> None:
        """Handle direct message events."""
        user = payload.get('user_id', 'unknown')
        text = payload.get('text', '')
        logger.info(f"Direct message from {user}: {text}")


async def main():
    """Main example function."""
    # Get Slack signing secret from environment variable
    signing_secret = os.getenv('SLACK_SIGNING_SECRET')

    if not signing_secret:
        logger.warning(
            "SLACK_SIGNING_SECRET not set. "
            "Running without signature verification."
        )

    # Create Slack authentication handler
    slack_auth = SlackAuth(signing_secret=signing_secret)

    # Create webhook configuration
    webhook_config = WebhookConfig(
        allowed_methods=[HttpMethod.POST],
        max_payload_size=2 * 1024 * 1024,  # 2MB for Slack payloads
    )

    # Create Slack webhook trigger using factory method
    slack_trigger = WebhookTrigger(
        trigger_id="slack-webhook-example",
        name="Slack Events Handler",
        description="Handle incoming Slack webhook events with custom "
        "responses",
        port=8080,
        path="/slack/events",
        host="localhost",
        auth_handler=slack_auth,
        webhook_config=webhook_config,
    )

    # Create event handler
    event_handler = SlackEventHandler()
    slack_trigger.add_callback(event_handler.handle_event)

    # Trigger Manager
    trigger_manager = TriggerManager(
        handler_type=CallbackHandlerType.CHATAGENT
    )

    try:
        # Initialize and activate the trigger
        trigger_manager.register_trigger(slack_trigger)

        logger.info(
            "Slack webhook server running on http://localhost:8080/slack/events"
        )
        logger.info("Configure your Slack app to send events to this URL")

        if signing_secret:
            logger.info("Signature verification is ENABLED")
        else:
            logger.info("Signature verification is DISABLED")

        # Keep the server running
        logger.info("Server running. Press Ctrl+C to stop...")
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Clean up
        await trigger_manager.deactivate_all_triggers()
        logger.info(f"Processed {len(event_handler.received_events)} events")


if __name__ == "__main__":
    # Run the webhook example
    asyncio.run(main())
