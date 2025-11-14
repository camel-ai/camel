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
# Example usage
import asyncio

from camel.societies.workforce.workforce import Workforce

# from camel.triggers.schedule_trigger import ScheduleTrigger
from camel.triggers.schedule_trigger import ScheduleTrigger, TimeUnit
from camel.triggers.trigger_manager import TriggerManager
from camel.triggers.webhook_trigger import WebhookTrigger


async def say_hello(event):
    print(f"Hello! In {event.timestamp} with payload: {event.payload}")


async def setup_trigger_system():
    workforce = Workforce("Triggered Workforce")
    trigger_manager = TriggerManager(workforce=workforce)

    # Setup webhook trigger
    webhook_trigger = WebhookTrigger(
        trigger_id="webhook_001",
        name="External API Webhook",
        description="Receives data from external system",
        config={"port": 8085, "path": "/webhook/external", "host": "0.0.0.0"},
    )

    webhook_trigger.add_callback(say_hello)

    # Create an interval trigger (every 30 seconds)
    schedule_trigger = ScheduleTrigger.create_interval_trigger(
        trigger_id="interval_001",
        name="30 Second Interval",
        description="Triggers every 30 seconds",
        unit=TimeUnit.SECONDS,
        value=30,
    )
    schedule_trigger.add_callback(say_hello)

    # Register triggers
    await trigger_manager.register_trigger(webhook_trigger)
    await trigger_manager.register_trigger(schedule_trigger)

    # keep alive
    while True:
        await asyncio.sleep(1)

    return workforce, trigger_manager


def main():
    workforce, trigger_manager = asyncio.run(setup_trigger_system())


main()
