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
r"""Extensibility surface for the trigger framework.

To add a new trigger kind you implement :class:`BaseTrigger` and register it
with :func:`register_trigger`. Everything else — the CRUD toolkit, the
persistence store, and the manager loop — works unchanged.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Optional,
    Type,
)

from camel.logger import get_logger

from .models import TriggerEvent, TriggerSpec

logger = get_logger(__name__)

# A sink receives fired events. Implementations live in sinks.py; the manager
# only depends on this callable shape, keeping it agnostic to the runtime
# (Workforce, ChatAgent, ...).
EmitFn = Callable[[TriggerEvent], Awaitable[None]]


class BaseTrigger(ABC):
    r"""Abstract base class for a trigger source.

    A trigger owns a :class:`TriggerSpec` and knows how to (a) validate its
    own ``config``, and (b) run as a long-lived async source that calls
    ``emit`` whenever it fires. The manager supplies ``emit``; the trigger
    must not import or know about any agent/runtime.

    Subclasses implement :meth:`validate_config` and :meth:`run`. They should
    cooperate with cancellation (i.e. ``await`` on cancellable primitives) so
    the manager can stop them cleanly.
    """

    #: Registered type name; set by the ``@register_trigger`` decorator.
    type_name: str = ""

    def __init__(self, spec: TriggerSpec) -> None:
        self.spec = spec

    @classmethod
    @abstractmethod
    def validate_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        r"""Validate and normalize a config dict for this trigger type.

        Args:
            config (Dict[str, Any]): Raw, agent-supplied config.

        Returns:
            Dict[str, Any]: The normalized config to persist.

        Raises:
            ValueError: If the config is invalid (the toolkit converts this
                into a readable error string for the model).
        """

    @abstractmethod
    async def run(self, emit: EmitFn) -> None:
        r"""Run the trigger source until cancelled.

        Implementations loop (or await external input) and call ``await
        emit(event)`` on each fire. They should honor
        :attr:`TriggerSpec.state` and stop firing when not ``ACTIVE``.

        Args:
            emit (EmitFn): Coroutine to deliver a :class:`TriggerEvent`.
        """

    # -- helpers shared by concrete triggers --------------------------------

    def _build_event(
        self,
        slot_key: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> TriggerEvent:
        r"""Construct a :class:`TriggerEvent` for the next fire.

        Args:
            slot_key (str): A value unique to this fire (e.g. the scheduled
                time, or a delivery id) used to build the idempotency key.
            data (Optional[Dict[str, Any]]): Optional structured payload.
        """
        return TriggerEvent(
            trigger_id=self.spec.id,
            trigger_name=self.spec.name,
            trigger_type=self.spec.type,
            payload=self.spec.payload,
            data=data or {},
            fired_at=datetime.now(timezone.utc),
            run_count=self.spec.run_count + 1,
            idempotency_key=f"{self.spec.id}:{slot_key}",
        )

    def _is_exhausted(self) -> bool:
        r"""Whether max_runs / until limits have been reached."""
        if (
            self.spec.max_runs is not None
            and self.spec.run_count >= self.spec.max_runs
        ):
            return True
        if (
            self.spec.until is not None
            and datetime.now(timezone.utc) >= self.spec.until
        ):
            return True
        return False


# --- trigger type registry -------------------------------------------------

_TRIGGER_REGISTRY: Dict[str, Type[BaseTrigger]] = {}


def register_trigger(
    name: str,
) -> Callable[[Type[BaseTrigger]], Type[BaseTrigger]]:
    r"""Class decorator to register a :class:`BaseTrigger` subclass.

    Args:
        name (str): The type name used in :attr:`TriggerSpec.type` and exposed
            to the agent via the toolkit.

    Returns:
        Callable: The decorator.
    """

    def deco(cls: Type[BaseTrigger]) -> Type[BaseTrigger]:
        cls.type_name = name
        _TRIGGER_REGISTRY[name] = cls
        logger.debug(f"Registered trigger type '{name}' -> {cls.__name__}")
        return cls

    return deco


def get_trigger_class(name: str) -> Type[BaseTrigger]:
    r"""Look up a registered trigger class by type name.

    Raises:
        ValueError: If no trigger type is registered under ``name``.
    """
    if name not in _TRIGGER_REGISTRY:
        available = ", ".join(sorted(_TRIGGER_REGISTRY)) or "(none)"
        raise ValueError(
            f"Unknown trigger type '{name}'. Available types: {available}."
        )
    return _TRIGGER_REGISTRY[name]


def available_trigger_types() -> Dict[str, Type[BaseTrigger]]:
    r"""Return a copy of the trigger type registry."""
    return dict(_TRIGGER_REGISTRY)


def new_idempotency_suffix() -> str:
    r"""A random suffix for triggers whose fires have no natural slot key."""
    return uuid.uuid4().hex[:12]
