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

import time
from collections import deque
from enum import Enum
from typing import Deque, Dict, List, Optional

from camel.tasks.task import Task


class WorkforceStateManager:
    r"""Manager class for workforce state and snapshot functionality."""

    class WorkforceState(Enum):
        r"""Workforce execution state for human intervention support."""

        IDLE = "idle"
        RUNNING = "running"
        PAUSED = "paused"
        STOPPED = "stopped"

    class WorkforceSnapshot:
        r"""Snapshot of workforce state for resuming execution."""

        def __init__(
            self,
            main_task: Optional[Task] = None,
            pending_tasks: Optional[Deque[Task]] = None,
            completed_tasks: Optional[List[Task]] = None,
            task_dependencies: Optional[Dict[str, List[str]]] = None,
            assignees: Optional[Dict[str, str]] = None,
            current_task_index: int = 0,
            description: str = "",
        ):
            self.main_task = main_task
            self.pending_tasks = (
                pending_tasks.copy() if pending_tasks else deque()
            )
            self.completed_tasks = (
                completed_tasks.copy() if completed_tasks else []
            )
            self.task_dependencies = (
                task_dependencies.copy() if task_dependencies else {}
            )
            self.assignees = assignees.copy() if assignees else {}
            self.current_task_index = current_task_index
            self.description = description
            self.timestamp = time.time()

    def __init__(self):
        """Initialize the WorkforceStateManager."""
        pass


# Export the classes at module level for easier importing
WorkforceState = WorkforceStateManager.WorkforceState
WorkforceSnapshot = WorkforceStateManager.WorkforceSnapshot

__all__ = ['WorkforceStateManager', 'WorkforceState', 'WorkforceSnapshot']
