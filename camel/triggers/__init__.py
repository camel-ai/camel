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
r"""Agentic triggers: a versatile framework for event sources that an agent
can CRUD at runtime and that notify the running session when they fire.

Built-in trigger types: ``schedule`` (cron / interval / once) and ``webhook``
(incoming HTTP). New types register via
:func:`~camel.triggers.base.register_trigger`.
"""

from .base import (
    BaseTrigger,
    available_trigger_types,
    get_trigger_class,
    register_trigger,
)
from .manager import TriggerManager
from .models import TriggerEvent, TriggerSpec, TriggerState
from .schedule_trigger import ScheduleTrigger
from .store import (
    BaseTriggerStore,
    InMemoryTriggerStore,
    JsonFileTriggerStore,
)
from .webhook_server import WebhookServer
from .webhook_trigger import WebhookTrigger

__all__ = [
    "BaseTrigger",
    "register_trigger",
    "get_trigger_class",
    "available_trigger_types",
    "TriggerManager",
    "TriggerSpec",
    "TriggerEvent",
    "TriggerState",
    "ScheduleTrigger",
    "WebhookTrigger",
    "WebhookServer",
    "BaseTriggerStore",
    "InMemoryTriggerStore",
    "JsonFileTriggerStore",
]
