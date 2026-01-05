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
r"""Thread-local agent context management.

This module provides a simple way to track the current agent ID
across the call stack without passing it explicitly.
"""

import threading
from typing import Optional

_local = threading.local()


def set_current_agent_id(agent_id: str) -> None:
    r"""Set the current agent ID in thread-local storage.

    Args:
        agent_id (str): The agent ID to set.
    """
    _local.agent_id = agent_id


def get_current_agent_id() -> Optional[str]:
    r"""Get the current agent ID from thread-local storage.

    Returns:
        Optional[str]: The agent ID if set, None otherwise.
    """
    return getattr(_local, 'agent_id', None)
