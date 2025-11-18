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
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

from pydantic import BaseModel

from camel.logger import get_logger

logger = get_logger(__name__)


class TriggerType(Enum):
    WEBHOOK = "webhook"
    SCHEDULE = "schedule"
    DATABASE = "database"
    CUSTOM = "custom"


class TriggerEvent(BaseModel):
    """Event data from trigger activation"""

    trigger_id: str
    trigger_type: TriggerType
    timestamp: datetime
    payload: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None


class TriggerState(Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    # PAUSED = "paused"
    # ERROR = "error"
    # DISABLED = "disabled"


class BaseTrigger(ABC):
    """Base trigger interface supporting extensibility"""

    def __init__(
        self,
        trigger_id: str,
        name: str,
        description: str,
        config: Dict[str, Any],
    ):
        self.trigger_id = trigger_id
        self.name = name
        self.description = description
        self.config = config
        self.state = TriggerState.INACTIVE
        self._callbacks: List[
            Union[
                Callable[[TriggerEvent], None],
                Callable[[TriggerEvent], Coroutine[Any, Any, Any]],
            ]
        ] = []
        self._execution_history: List[Dict[str, Any]] = []

        # Workforce integration attributes - set by TriggerManager
        self.workforce: Optional[Any] = None

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the trigger - setup connections, validate config"""
        pass

    @abstractmethod
    async def activate(self) -> bool:
        """Start listening for trigger events"""
        pass

    @abstractmethod
    async def deactivate(self) -> bool:
        """Stop listening for trigger events"""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if trigger can connect/function properly"""
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate trigger-specific configuration"""
        pass

    @abstractmethod
    async def process_trigger_event(self, event_data: Any) -> TriggerEvent:
        """Process raw trigger data into standardized TriggerEvent"""
        pass

    def add_callback(
        self,
        callback: Union[
            Callable[[TriggerEvent], None],
            Callable[[TriggerEvent], Coroutine[Any, Any, Any]],
        ],
    ):
        """Add callback for trigger events

        Args:
            callback: Synchronous or asynchronous callback function
        """
        self._callbacks.append(callback)

    def remove_callback(
        self,
        callback: Union[
            Callable[[TriggerEvent], None],
            Callable[[TriggerEvent], Coroutine[Any, Any, Any]],
        ],
    ):
        """Remove callback for trigger events

        Args:
            callback: Synchronous or asynchronous callback function to remove
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def _emit_trigger_event(self, event: TriggerEvent):
        """Emit trigger event to all callbacks"""

        # Execute callbacks
        for callback in self._callbacks:
            try:
                await callback(event) if asyncio.iscoroutinefunction(
                    callback
                ) else callback(event)

                # Save to execution history
                self._execution_history.append(
                    {
                        "timestamp": event.timestamp,
                        "trigger_id": event.trigger_id,
                        "payload_size": len(str(event.payload)),
                        "callback": callback.__name__,
                        "success": True,
                    }
                )
            except Exception as e:
                logger.error(f"Error in trigger callback: {e}")

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """Get trigger execution history"""
        return self._execution_history.copy()
