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
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.triggers.base_trigger import TriggerState

logger = get_logger(__name__)


class DatabaseAdapter(ABC):
    """Extensible database interface for trigger execution storage"""

    @abstractmethod
    async def save_execution_record(self, record: Dict[str, Any]) -> str:
        """Save trigger execution record"""
        pass

    @abstractmethod
    async def get_execution_history(
        self, trigger_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get trigger execution history"""
        pass

    @abstractmethod
    async def update_execution_status(
        self,
        execution_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
    ):
        """Update execution status"""
        pass


class InMemoryDatabaseAdapter(DatabaseAdapter):
    """Simple in-memory implementation for testing"""

    def __init__(self):
        self.records: Dict[str, Dict[str, Any]] = {}

    async def save_execution_record(self, record: Dict[str, Any]) -> str:
        execution_id = str(uuid.uuid4())
        self.records[execution_id] = {
            **record,
            "execution_id": execution_id,
            "created_at": datetime.now(),
        }
        return execution_id

    async def get_execution_history(
        self, trigger_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        records = list(self.records.values())
        if trigger_id:
            records = [r for r in records if r.get("trigger_id") == trigger_id]
        return sorted(records, key=lambda x: x["created_at"], reverse=True)[
            :limit
        ]

    async def update_execution_status(
        self,
        execution_id: str,
        status: TriggerState,
        result: Optional[Dict[str, Any]] = None,
    ):
        if execution_id in self.records:
            self.records[execution_id]["status"] = status
            if result:
                self.records[execution_id]["result"] = result
