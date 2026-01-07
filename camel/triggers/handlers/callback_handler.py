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

from typing import Any, Callable

from camel.triggers.base_trigger import TriggerEvent
from camel.triggers.handlers.trigger_event_handler import TriggerEventHandler


class CallbackHandler(TriggerEventHandler):
    """Handler that wraps a simple callback function.

    This handler allows users to provide a simple async callback function
    for processing events without creating a full handler class.

    Args:
        callback (Callable[[TriggerEvent], Any]): An async function that
            takes a TriggerEvent and returns any result.

    Example:
        Using a callback function::

            async def my_callback(event: TriggerEvent) -> dict:
                return {"processed": True, "id": event.trigger_id}

            handler = CallbackHandler(callback=my_callback)
            manager = TriggerManager(handler=handler)
    """

    def __init__(
        self,
        callback: Callable[[TriggerEvent], Any],
    ):
        self.callback = callback

    async def handle(self, event: TriggerEvent) -> Any:
        """Handle trigger event by calling the callback function.

        Args:
            event (TriggerEvent): The trigger event to process.

        Returns:
            Any: The result from the callback function.
        """
        result = self.callback(event)
        # Handle both sync and async callbacks
        if hasattr(result, "__await__"):
            return await result
        return result
