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

"""Navi-Bench evaluator hook helpers.

This module intentionally does NOT expose any JS execution tool to the agent.
Instead, it provides a Page-like adapter that calls the WebSocket wrapper via
"quiet" APIs so evaluator JS does not pollute action logs or mined skills.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from camel.logger import get_logger
from camel.toolkits.hybrid_browser_toolkit.ws_wrapper import (
    WebSocketBrowserWrapper,
)

logger = get_logger(__name__)


@dataclass
class NaviBenchEvalStats:
    """Lightweight evaluator runtime stats for debugging + reporting.

    Note: Many Navi-Bench evaluators are fully programmatic (0 LLM tokens). We
    still record timing and JS eval calls to help debug flaky sites.
    """

    reset_calls: int = 0
    update_calls: int = 0
    compute_calls: int = 0

    reset_time_s: float = 0.0
    update_time_s: float = 0.0
    compute_time_s: float = 0.0

    js_evaluate_calls: int = 0
    js_evaluate_time_s: float = 0.0
    js_code_chars_total: int = 0
    js_code_chars_max: int = 0

    last_error: str = ""
    llm_usage: Optional[Dict[str, Any]] = None


def _extract_token_usage(value: Any) -> Optional[Dict[str, Any]]:
    """Best-effort extraction of token usage from evaluator/result structures."""

    def _merge(dst: Dict[str, Any], src: Dict[str, Any]) -> None:
        for k, v in src.items():
            if k not in dst:
                dst[k] = v

    def _walk(obj: Any) -> Dict[str, Any]:
        out: Dict[str, Any] = {}

        if obj is None:
            return out

        if isinstance(obj, dict):
            usage = obj.get("usage")
            if isinstance(usage, dict):
                _merge(out, usage)

            for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
                if isinstance(obj.get(k), (int, float)):
                    out[k] = obj[k]

            for k in ("input_tokens", "output_tokens"):
                if isinstance(obj.get(k), (int, float)):
                    out[k] = obj[k]

            for v in obj.values():
                _merge(out, _walk(v))
            return out

        if isinstance(obj, (list, tuple)):
            for v in obj:
                _merge(out, _walk(v))
            return out

        if hasattr(obj, "model_dump"):
            try:
                return _walk(obj.model_dump())
            except Exception:
                return out
        if hasattr(obj, "dict"):
            try:
                return _walk(obj.dict())
            except Exception:
                return out

        for attr in ("usage", "token_usage", "llm_usage"):
            if hasattr(obj, attr):
                try:
                    _merge(out, _walk(getattr(obj, attr)))
                except Exception:
                    pass

        return out

    extracted = _walk(value)
    return extracted or None


def _parse_console_exec_result(response: Any) -> Any:
    """Best-effort parse for ws_wrapper console_exec(_quiet) responses."""
    if not isinstance(response, dict):
        return None

    result = response.get("result")
    if not isinstance(result, str):
        return None

    prefix = "Console execution result:"
    if result.startswith(prefix):
        payload = result[len(prefix) :].strip()
        try:
            return json.loads(payload)
        except Exception:
            # Some pages might return non-JSON-serializable values; fall back.
            return payload

    if result.startswith("Console execution failed:"):
        return None

    # Unknown format (future changes); return the string to preserve signal.
    return result


class WsPageAdapter:
    """A minimal Page-like object that supports `await page.evaluate(js)`."""

    def __init__(
        self,
        ws_wrapper: WebSocketBrowserWrapper,
        *,
        stats: Optional[NaviBenchEvalStats] = None,
    ):
        self._ws = ws_wrapper
        self._stats = stats

    async def evaluate(self, script: str) -> Any:
        # Navi-Bench evaluators typically pass a JS string that returns JSON-like
        # data. We execute via a "quiet" call to avoid polluting logs/skills.
        t0 = time.time()
        if self._stats is not None:
            self._stats.js_evaluate_calls += 1
            self._stats.js_code_chars_total += len(script or "")
            self._stats.js_code_chars_max = max(
                self._stats.js_code_chars_max, len(script or "")
            )
        try:
            resp: Dict[str, Any] = await self._ws.console_exec_quiet(script)
        except Exception as e:
            logger.warning(
                f"console_exec_quiet failed: {type(e).__name__}: {e}"
            )
            if self._stats is not None:
                self._stats.last_error = (
                    f"WsPageAdapter.evaluate: {type(e).__name__}: {e}"
                )
            return None
        if self._stats is not None:
            self._stats.js_evaluate_time_s += time.time() - t0
        return _parse_console_exec_result(resp)


async def navi_bench_on_action_update(
    *,
    evaluator: Any,
    ws_wrapper: WebSocketBrowserWrapper,
    event: Dict[str, Any],
    stats: Optional[NaviBenchEvalStats] = None,
) -> None:
    """Default ws_wrapper action hook for Navi-Bench evaluators."""
    url = event.get("current_url")
    if not isinstance(url, str):
        url = ""

    page = WsPageAdapter(ws_wrapper, stats=stats)

    # Be permissive about evaluator.update signatures.
    t0 = time.time()
    try:
        await evaluator.update(url=url, page=page)
    except TypeError:
        try:
            await evaluator.update(url=url)
        except TypeError:
            await evaluator.update(page=page)
    if stats is not None:
        stats.update_calls += 1
        stats.update_time_s += time.time() - t0
        # Some evaluators might expose usage as they run.
        if stats.llm_usage is None:
            stats.llm_usage = _extract_token_usage(evaluator)
