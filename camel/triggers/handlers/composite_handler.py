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

from typing import Any, Dict, List

from camel.triggers.base_trigger import TriggerEvent
from camel.triggers.handlers.trigger_event_handler import TriggerEventHandler


class CompositeHandler(TriggerEventHandler):
    """Handler that chains multiple handlers together.

    This handler allows composing multiple handlers for complex processing
    pipelines where events need to be processed by several handlers in
    sequence.

    Args:
        handlers (List[TriggerEventHandler]): List of handlers to execute
            in order.

    Example:
        Chaining a logging handler with a processing handler::

            from camel.triggers.handlers import (
                CompositeHandler,
                CallbackHandler,
                ChatAgentHandler,
            )

            async def log_event(event: TriggerEvent) -> dict:
                print(f"Event received: {event.trigger_id}")
                return {"logged": True}

            composite = CompositeHandler(handlers=[
                CallbackHandler(callback=log_event),
                ChatAgentHandler(chat_agent=my_agent),
            ])

            manager = TriggerManager(handler=composite)
    """

    def __init__(self, handlers: List[TriggerEventHandler]):
        """Initialize with list of handlers to chain.

        Args:
            handlers: List of handlers to execute in order.
        """
        self.handlers = handlers

    async def handle(self, event: TriggerEvent) -> Dict[str, Any]:
        """Execute all handlers in sequence.

        Args:
            event: The trigger event to process.

        Returns:
            Dict containing aggregated results from all handlers.
        """
        results = {}
        for i, handler in enumerate(self.handlers):
            handler_name = handler.__class__.__name__
            try:
                result = await handler.handle(event)
                results[f"{i}_{handler_name}"] = result
            except Exception as e:
                results[f"{i}_{handler_name}"] = {"error": str(e)}

        return {
            "composite_results": results,
            "handlers_executed": len(results),
        }
