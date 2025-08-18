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
from __future__ import annotations

from enum import Enum
from typing import Dict


class WorkforceStateManager:
    r"""Manager class for workforce state and snapshot functionality."""

    class WorkforceState(Enum):
        r"""Workforce execution state for human intervention support."""

        IDLE = "idle"
        RUNNING = "running"
        PAUSED = "paused"
        STOPPED = "stopped"

    def __init__(self):
        r"""Initialize the WorkforceStateManager."""
        pass

    def get_workforce_status(self, workforce_instance) -> Dict:
        r"""Get current workforce status for human review.

        Args:
            workforce_instance: The workforce instance to get status from.

        Returns:
            Dict: Dictionary containing current workforce status information.
        """
        return {
            "state": workforce_instance._state.value,
            "pending_tasks_count": len(workforce_instance._pending_tasks),
            "completed_tasks_count": len(workforce_instance._completed_tasks),
            "snapshots_count": len(workforce_instance._snapshots),
            "children_count": len(workforce_instance._children),
            "main_task_id": workforce_instance._task.id
            if workforce_instance._task
            else None,
        }


# Export the classes at module level for easier importing
WorkforceState = WorkforceStateManager.WorkforceState

__all__ = ['WorkforceStateManager', 'WorkforceState']
