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

"""
Workforce Split Module

This module contains the refactored workforce components split into specialized
manager classes for better maintainability and separation of concerns.

The main class is WorkforceCore, which orchestrates all the specialized
managers:
- TaskAssignmentManager: Handles task assignment and coordination
- WorkerManagement: Manages worker creation and lifecycle
- ChannelCommunication: Handles inter-node communication
- WorkforceFailureDispatch: Manages failure handling and recovery
- WorkforceIntervention: Provides pause/resume functionality
- TaskManager: Manages task lifecycle and operations
- WorkforceSnapshotManager: Handles state snapshots and restoration
- SharedMemoryManager: Manages shared memory across agents
- IntrospectionHelper: Provides introspection and debugging capabilities
- WorkforceLoggerWrapper: Handles logging and metrics
- InFlightTaskTracker: Tracks in-flight tasks
- FailureAnalyzer: Analyzes failures and suggests recovery strategies
- DependencyManager: Manages task dependencies
"""

# Main class
# Manager classes
from .assignment import TaskAssignmentManager
from .channel_communication import ChannelCommunication
from .complete_failure_dispatch import WorkforceFailureDispatch
from .core import WorkforceCore
from .dependencies import DependencyManager
from .failure import FailureAnalyzer
from .in_flight_tracking import InFlightTaskTracker
from .intervention import WorkforceIntervention
from .introspection import IntrospectionHelper
from .logger import WorkforceLoggerWrapper
from .memory import SharedMemoryManager
from .snapshots import WorkforceSnapshotManager
from .state import WorkforceStateManager
from .task_management import TaskManager
from .worker_management import WorkerManagement

__all__ = [
    # Main class
    "WorkforceCore",
    # Manager classes
    "TaskAssignmentManager",
    "WorkerManagement",
    "ChannelCommunication",
    "WorkforceFailureDispatch",
    "WorkforceIntervention",
    "TaskManager",
    "WorkforceSnapshotManager",
    "SharedMemoryManager",
    "IntrospectionHelper",
    "WorkforceLoggerWrapper",
    "InFlightTaskTracker",
    "FailureAnalyzer",
    "DependencyManager",
    "WorkforceStateManager",
]
