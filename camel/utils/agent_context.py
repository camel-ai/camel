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
r"""Async-safe agent context management.

This module provides a simple way to track the current agent ID
across the call stack without passing it explicitly.

Uses contextvars.ContextVar instead of threading.local() to ensure
correct behavior in asyncio environments where multiple coroutines
may run concurrently on the same thread.
"""

from contextvars import ContextVar
from typing import Optional

# ContextVar is async-safe and maintains separate values for each
# asyncio task/coroutine, unlike threading.local() which shares
# state across all coroutines on the same thread.
_agent_id_var: ContextVar[Optional[str]] = ContextVar(
    'agent_id', default=None
)


def set_current_agent_id(agent_id: str) -> None:
    r"""Set the current agent ID in context-local storage.

    This is safe to use in both sync and async contexts.
    In async contexts, each coroutine maintains its own value.

    Args:
        agent_id (str): The agent ID to set.
    """
    _agent_id_var.set(agent_id)


def get_current_agent_id() -> Optional[str]:
    r"""Get the current agent ID from context-local storage.

    This is safe to use in both sync and async contexts.
    In async contexts, returns the value for the current coroutine.

    Returns:
        Optional[str]: The agent ID if set, None otherwise.
    """
    return _agent_id_var.get()
