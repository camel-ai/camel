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
from typing import Any

from camel.triggers.base_trigger import TriggerEvent


class TriggerEventHandler(ABC):
    """Abstract base class for trigger event handlers.
    This protocol defines the interface that all trigger event handlers
    must implement. Users can create custom handlers by subclassing this
    class and implementing the `handle` method.
    Example:
        Creating a custom handler::
            class LoggingHandler(TriggerEventHandler):
                async def handle(self, event: TriggerEvent) -> Any:
                    logger.info(f"Event received: {event}")
                    return {"logged": True}
            class WebhookForwardHandler(TriggerEventHandler):
                def __init__(self, webhook_url: str):
                    self.webhook_url = webhook_url
                async def handle(self, event: TriggerEvent) -> Any:
                    async with aiohttp.ClientSession() as session:
                        await session.post(
                            self.webhook_url,
                            json=event.dict()
                        )
                    return {"forwarded": True}
    """

    @abstractmethod
    async def handle(self, event: TriggerEvent) -> Any:
        """Handle a trigger event.
        Args:
            event (TriggerEvent): The trigger event to process.
        Returns:
            Any: The result of processing the event. The return type
                depends on the specific handler implementation.
        """
        pass
