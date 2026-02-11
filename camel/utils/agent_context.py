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
from contextvars import ContextVar
from typing import Optional

_agent_id_var: ContextVar[Optional[str]] = ContextVar('agent_id', default=None)
_agent_role_name_var: ContextVar[Optional[str]] = ContextVar(
    'agent_role_name', default=None
)
_agent_role_type_var: ContextVar[Optional[str]] = ContextVar(
    'agent_role_type', default=None
)


def set_current_agent_id(agent_id: str) -> None:
    r"""Set the current agent ID in context-local storage.

    This is safe to use in both sync and async contexts.
    In async contexts, each coroutine maintains its own value.

    Args:
        agent_id (str): The agent ID to set.
    """
    _agent_id_var.set(agent_id)


def set_current_agent_context(
    agent_id: str,
    role_name: Optional[str] = None,
    role_type: Optional[str] = None,
) -> None:
    r"""Set current agent context in context-local storage."""
    normalized_role_name = (
        role_name.strip().lower() if isinstance(role_name, str) else role_name
    )
    normalized_role_type = None
    if role_type is not None:
        normalized_role_type = str(role_type).strip().lower()
        if normalized_role_type.startswith("roletype."):
            normalized_role_type = normalized_role_type.split(".", 1)[1]

    _agent_id_var.set(agent_id)
    _agent_role_name_var.set(normalized_role_name)
    _agent_role_type_var.set(normalized_role_type)


def get_current_agent_id() -> Optional[str]:
    r"""Get the current agent ID from context-local storage.

    This is safe to use in both sync and async contexts.
    In async contexts, returns the value for the current coroutine.

    Returns:
        Optional[str]: The agent ID if set, None otherwise.
    """
    return _agent_id_var.get()


def get_current_agent_role_name() -> Optional[str]:
    r"""Get current agent role name from context-local storage."""
    return _agent_role_name_var.get()


def get_current_agent_role_type() -> Optional[str]:
    r"""Get current agent role type from context-local storage."""
    return _agent_role_type_var.get()
