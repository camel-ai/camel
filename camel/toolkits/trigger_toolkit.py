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
r"""Toolkit that lets an agent CRUD its own triggers (schedules & webhooks).

Backed by a :class:`~camel.triggers.manager.TriggerManager`. Every tool
returns a JSON-serializable dict and converts validation problems into
readable error strings (rather than raising into the agent's step loop), so
the model can self-correct.
"""

from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool
from camel.triggers import TriggerManager, TriggerState
from camel.triggers.base import available_trigger_types

logger = get_logger(__name__)


class TriggerToolkit(BaseToolkit):
    r"""A toolkit for creating and managing agentic triggers.

    A *trigger* fires on some condition — a schedule (cron / interval /
    one-shot) or an incoming webhook — and injects its ``payload`` into the
    running session as a new task/message. This toolkit exposes CRUD over
    those triggers so the agent can manage its own automation at runtime.

    Args:
        manager (TriggerManager): The manager that owns the trigger store and
            runs the trigger sources. Typically supplied by the host runtime
            (e.g. a :class:`~camel.societies.workforce.workforce.Workforce`).
        timeout (Optional[float]): Per-method timeout. Defaults to ``None``.
    """

    def __init__(
        self,
        manager: TriggerManager,
        timeout: Optional[float] = None,
    ) -> None:
        super().__init__(timeout=timeout)
        self.manager = manager

    def create_trigger(
        self,
        name: str,
        type: str,
        payload: str,
        config: Dict[str, Any],
        max_runs: Optional[int] = None,
        until: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Create a new trigger that will inject ``payload`` when it fires.

        Args:
            name (str): A short human-readable label for the trigger.
            type (str): The trigger type. Use ``list_trigger_types`` to see
                what is available; built-ins are ``"schedule"`` and
                ``"webhook"``.
            payload (str): The instruction to run when the trigger fires. This
                becomes the content of a new task in the session, e.g.
                ``"Summarize my unread email and post it to Slack."``
            config (Dict[str, Any]): Type-specific settings. For ``schedule``:
                ``{"kind": "cron", "expr": "0 9 * * 1-5"}`` or
                ``{"kind": "interval", "seconds": 300}`` or
                ``{"kind": "once", "at": "2026-06-01T09:00:00+00:00"}``. For
                ``webhook``: ``{"path": "/hooks/ci", "method": "POST",
                "secret": "optional-hmac-secret"}``.
            max_runs (Optional[int]): Stop firing after this many times.
            until (Optional[str]): ISO-8601 datetime after which the trigger
                stops firing.

        Returns:
            Dict[str, Any]: The created trigger summary, or an ``error`` field
                describing why creation failed.
        """
        try:
            spec = self.manager.create(
                name=name,
                type=type,
                payload=payload,
                config=config,
                max_runs=max_runs,
                until=until,
            )
        except (ValueError, ImportError) as e:
            return {"error": str(e)}
        return {"created": True, **spec.summary()}

    def list_triggers(self, active_only: bool = False) -> List[Dict[str, Any]]:
        r"""List existing triggers.

        Args:
            active_only (bool): If True, only return triggers that are
                currently active (not paused or exhausted).

        Returns:
            List[Dict[str, Any]]: One compact summary per trigger.
        """
        return [
            s.summary() for s in self.manager.list(active_only=active_only)
        ]

    def get_trigger(self, trigger_id: str) -> Dict[str, Any]:
        r"""Get the full details of a single trigger.

        Args:
            trigger_id (str): The id of the trigger.

        Returns:
            Dict[str, Any]: The trigger details, or an ``error`` field if not
                found.
        """
        spec = self.manager.get(trigger_id)
        if spec is None:
            return {"error": f"Trigger '{trigger_id}' not found."}
        return spec.model_dump(mode="json")

    def update_trigger(
        self,
        trigger_id: str,
        name: Optional[str] = None,
        payload: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        max_runs: Optional[int] = None,
        until: Optional[str] = None,
    ) -> Dict[str, Any]:
        r"""Update an existing trigger's mutable fields.

        Only the provided fields are changed. Changing ``config`` re-validates
        and restarts the trigger source.

        Args:
            trigger_id (str): The id of the trigger to update.
            name (Optional[str]): New label.
            payload (Optional[str]): New instruction to inject on fire.
            config (Optional[Dict[str, Any]]): New type-specific settings.
            max_runs (Optional[int]): New max-runs limit.
            until (Optional[str]): New ISO-8601 stop time.

        Returns:
            Dict[str, Any]: The updated summary, or an ``error`` field.
        """
        fields: Dict[str, Any] = {}
        if name is not None:
            fields["name"] = name
        if payload is not None:
            fields["payload"] = payload
        if config is not None:
            fields["config"] = config
        if max_runs is not None:
            fields["max_runs"] = max_runs
        if until is not None:
            fields["until"] = until
        if not fields:
            return {"error": "No fields provided to update."}
        try:
            spec = self.manager.update(trigger_id, **fields)
        except (ValueError, ImportError) as e:
            return {"error": str(e)}
        if spec is None:
            return {"error": f"Trigger '{trigger_id}' not found."}
        return {"updated": True, **spec.summary()}

    def pause_trigger(self, trigger_id: str) -> Dict[str, Any]:
        r"""Pause a trigger so it stops firing (keeps its config).

        Args:
            trigger_id (str): The id of the trigger to pause.

        Returns:
            Dict[str, Any]: The trigger summary, or an ``error`` field.
        """
        spec = self.manager.set_state(trigger_id, TriggerState.PAUSED)
        if spec is None:
            return {"error": f"Trigger '{trigger_id}' not found."}
        return spec.summary()

    def resume_trigger(self, trigger_id: str) -> Dict[str, Any]:
        r"""Resume a previously paused trigger.

        Args:
            trigger_id (str): The id of the trigger to resume.

        Returns:
            Dict[str, Any]: The trigger summary, or an ``error`` field.
        """
        spec = self.manager.set_state(trigger_id, TriggerState.ACTIVE)
        if spec is None:
            return {"error": f"Trigger '{trigger_id}' not found."}
        return spec.summary()

    def cancel_trigger(self, trigger_id: str) -> Dict[str, Any]:
        r"""Delete a trigger permanently.

        Args:
            trigger_id (str): The id of the trigger to delete.

        Returns:
            Dict[str, Any]: ``{"deleted": True}`` on success, else an
                ``error`` field.
        """
        if not self.manager.delete(trigger_id):
            return {"error": f"Trigger '{trigger_id}' not found."}
        return {"deleted": True, "id": trigger_id}

    def list_trigger_types(self) -> List[str]:
        r"""List the available trigger type names that can be created.

        Returns:
            List[str]: Registered trigger type names (e.g. ``["schedule",
                "webhook"]``).
        """
        return sorted(available_trigger_types().keys())

    def get_tools(self) -> List[FunctionTool]:
        r"""Return the toolkit's tools as :class:`FunctionTool` objects."""
        return [
            FunctionTool(self.create_trigger),
            FunctionTool(self.list_triggers),
            FunctionTool(self.get_trigger),
            FunctionTool(self.update_trigger),
            FunctionTool(self.pause_trigger),
            FunctionTool(self.resume_trigger),
            FunctionTool(self.cancel_trigger),
            FunctionTool(self.list_trigger_types),
        ]
