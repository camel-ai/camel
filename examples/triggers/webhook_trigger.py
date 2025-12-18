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

"""
Simple Webhook Trigger Example

Creates a webhook that listens for HTTP POST requests and processes them.
Test with: curl -X POST http://localhost:8080/webhook \
    -H 'Content-Type: application/json' -d '{"task": "process data"}'
"""

import asyncio

from camel.logger import get_logger
from camel.societies.workforce.workforce import Workforce
from camel.triggers.base_trigger import TriggerEvent
from camel.triggers.trigger_manager import CallbackHandlerType, TriggerManager
from camel.triggers.webhook_trigger import WebhookTrigger

logger = get_logger(__name__)


async def handle_webhook(event: TriggerEvent):
    """Process incoming webhook data."""
    logger.info(f"Received webhook: {event.payload}")

    # Process the webhook payload
    if "task" in event.payload:
        task = event.payload["task"]
        logger.info(f"Processing task: {task}")


async def main():
    """Run a simple webhook trigger."""
    # Setup
    workforce = Workforce("Webhook Workforce")
    trigger_manager = TriggerManager(
        handler_type=CallbackHandlerType.WORKFORCE, workforce=workforce
    )

    # Create webhook trigger
    webhook = WebhookTrigger(
        trigger_id="simple_webhook",
        name="Simple Webhook",
        description="Processes incoming HTTP requests",
        port=8080,
        path="/webhook",
        host="localhost",
    )

    # Add handler and register
    webhook.add_callback(handle_webhook)
    await trigger_manager.register_trigger(webhook)

    logger.info("Webhook server started at http://localhost:8080/webhook")
    logger.info(
        "Test: curl -X POST http://localhost:8080/webhook "
        "-H 'Content-Type: application/json' -d '{\"task\": \"hello world\"}'"
    )
    logger.info("Press Ctrl+C to stop")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping webhook...")
        await trigger_manager.deactivate_all_triggers()
        logger.info("Done")


if __name__ == "__main__":
    asyncio.run(main())
