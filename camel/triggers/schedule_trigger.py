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
r"""Time-based trigger: cron, fixed interval, or one-shot."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from camel.logger import get_logger

from .base import BaseTrigger, EmitFn, register_trigger

logger = get_logger(__name__)

# Guard against runaway recurrences from an over-eager agent.
MIN_INTERVAL_SECONDS = 1.0
# Max time the source sleeps in one hop, so state changes are noticed.
_MAX_SLEEP_SECONDS = 60.0


def _require_croniter():
    try:
        from croniter import croniter

        return croniter
    except ImportError as e:
        raise ImportError(
            "Cron schedules require the 'croniter' package. Install the "
            "trigger extra: pip install 'camel-ai[triggers]'."
        ) from e


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@register_trigger("schedule")
class ScheduleTrigger(BaseTrigger):
    r"""A trigger that fires on a time schedule.

    Config shape (``TriggerSpec.config``), discriminated by ``kind``:

    - cron: ``{"kind": "cron", "expr": "0 9 * * 1-5"}`` (croniter syntax)
    - interval: ``{"kind": "interval", "seconds": 300}``
    - once: ``{"kind": "once", "at": "2026-06-01T09:00:00+00:00"}``

    The source sleeps until the next due time (capped per hop so config edits
    are picked up promptly) and emits a single event per due slot. Missed
    slots while the process was down are coalesced into one fire on resume.
    """

    @classmethod
    def validate_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        kind = config.get("kind")
        if kind == "cron":
            expr = config.get("expr")
            if not isinstance(expr, str) or not expr.strip():
                raise ValueError("cron schedule requires a string 'expr'.")
            croniter = _require_croniter()
            if not croniter.is_valid(expr):
                raise ValueError(f"Invalid cron expression: '{expr}'.")
            return {"kind": "cron", "expr": expr.strip()}
        if kind == "interval":
            seconds = config.get("seconds")
            if not isinstance(seconds, (int, float)) or isinstance(
                seconds, bool
            ):
                raise ValueError(
                    "interval schedule requires numeric 'seconds'."
                )
            if seconds < MIN_INTERVAL_SECONDS:
                raise ValueError(
                    f"interval 'seconds' must be >= {MIN_INTERVAL_SECONDS}."
                )
            return {"kind": "interval", "seconds": float(seconds)}
        if kind == "once":
            at = config.get("at")
            if not isinstance(at, str):
                raise ValueError(
                    "once schedule requires an ISO-8601 'at' datetime string."
                )
            try:
                when = _parse_dt(at)
            except ValueError as e:
                raise ValueError(f"Invalid 'at' datetime: {e}") from e
            if when <= datetime.now(timezone.utc):
                raise ValueError("once schedule 'at' must be in the future.")
            return {"kind": "once", "at": when.isoformat()}
        raise ValueError(
            "schedule config 'kind' must be one of: cron, interval, once."
        )

    def _next_run(self, after: datetime) -> Optional[datetime]:
        r"""Compute the next fire time strictly after ``after`` (UTC)."""
        cfg = self.spec.config
        kind = cfg["kind"]
        if kind == "cron":
            croniter = _require_croniter()
            itr = croniter(cfg["expr"], after)
            return itr.get_next(datetime).astimezone(timezone.utc)
        if kind == "interval":
            base = self.spec.last_run or self.spec.created_at
            base = base.astimezone(timezone.utc)
            seconds = cfg["seconds"]
            # Advance in whole steps past `after` (coalesces missed slots).
            elapsed = (after - base).total_seconds()
            steps = max(1, int(elapsed // seconds) + 1)
            from datetime import timedelta

            return base + timedelta(seconds=seconds * steps)
        if kind == "once":
            when = _parse_dt(cfg["at"])
            return when if self.spec.run_count == 0 else None
        return None

    async def run(self, emit: EmitFn) -> None:
        while True:
            if not self.spec.enabled or self._is_exhausted():
                # Park briefly; manager flips state via the shared spec.
                await asyncio.sleep(min(_MAX_SLEEP_SECONDS, 5.0))
                continue

            now = datetime.now(timezone.utc)
            nxt = self._next_run(now)
            if nxt is None:
                # 'once' already fired; nothing more to do.
                return

            wait = (nxt - now).total_seconds()
            if wait > 0:
                await asyncio.sleep(min(wait, _MAX_SLEEP_SECONDS))
                # Loop back: re-check state and whether we're now due.
                if datetime.now(timezone.utc) < nxt:
                    continue

            event = self._build_event(slot_key=nxt.isoformat())
            await emit(event)
