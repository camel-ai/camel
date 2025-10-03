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
"""Utility functions for parsing MCP tool calls from model output."""

import ast
import json
import logging
import re
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - optional dependency
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


CODE_BLOCK_PATTERN = re.compile(
    r"```(?:[a-z0-9_-]+)?\s*([\s\S]+?)\s*```",
    re.IGNORECASE,
)

JSON_START_PATTERN = re.compile(r"[{\[]")
JSON_TOKEN_PATTERN = re.compile(
    r"""
    (?P<double>"(?:\\.|[^"\\])*")
    |
    (?P<single>'(?:\\.|[^'\\])*')
    |
    (?P<brace>[{}\[\]])
    """,
    re.VERBOSE,
)

logger = logging.getLogger(__name__)


def extract_tool_calls_from_text(content: str) -> List[Dict[str, Any]]:
    """Extract tool call dictionaries from raw text output."""

    if not content:
        return []

    tool_calls: List[Dict[str, Any]] = []
    seen_ranges: List[tuple[int, int]] = []

    for match in CODE_BLOCK_PATTERN.finditer(content):
        snippet = match.group(1).strip()
        if not snippet:
            continue

        parsed = _try_parse_json_like(snippet)
        if parsed is None:
            logger.warning(
                "Failed to parse JSON payload from fenced block: %s",
                snippet,
            )
            continue

        _collect_tool_calls(parsed, tool_calls)
        seen_ranges.append((match.start(1), match.end(1)))

    for start_match in JSON_START_PATTERN.finditer(content):
        start_idx = start_match.start()

        if any(start <= start_idx < stop for start, stop in seen_ranges):
            continue

        segment = _find_json_candidate(content, start_idx)
        if segment is None:
            continue

        end_idx = start_idx + len(segment)
        if any(start <= start_idx < stop for start, stop in seen_ranges):
            continue

        parsed = _try_parse_json_like(segment)
        if parsed is None:
            logger.debug(
                "Unable to parse JSON-like candidate: %s",
                _truncate_snippet(segment),
            )
            continue

        _collect_tool_calls(parsed, tool_calls)
        seen_ranges.append((start_idx, end_idx))

    return tool_calls


def _collect_tool_calls(
    payload: Any, accumulator: List[Dict[str, Any]]
) -> None:
    """Collect valid tool call dictionaries from parsed payloads."""

    if isinstance(payload, dict):
        if payload.get("tool_name") is None:
            return
        accumulator.append(payload)
    elif isinstance(payload, list):
        for item in payload:
            _collect_tool_calls(item, accumulator)


def _try_parse_json_like(snippet: str) -> Optional[Any]:
    """Parse a JSON or JSON-like snippet into Python data."""

    try:
        return json.loads(snippet)
    except json.JSONDecodeError as exc:
        logger.debug(
            "json.loads failed: %s | snippet=%s",
            exc,
            _truncate_snippet(snippet),
        )

    if yaml is not None:
        try:
            return yaml.safe_load(snippet)
        except yaml.YAMLError:
            pass

    try:
        return ast.literal_eval(snippet)
    except (ValueError, SyntaxError):
        return None


def _find_json_candidate(content: str, start_idx: int) -> Optional[str]:
    """Locate a balanced JSON-like segment starting at ``start_idx``."""

    opening = content[start_idx]
    if opening not in "{[":
        return None

    stack = ["}" if opening == "{" else "]"]

    for token in JSON_TOKEN_PATTERN.finditer(content, start_idx + 1):
        if token.lastgroup in {"double", "single"}:
            continue

        brace = token.group("brace")
        if brace in "{[":
            stack.append("}" if brace == "{" else "]")
            continue

        if not stack:
            return None

        expected = stack.pop()
        if brace != expected:
            return None

        if not stack:
            return content[start_idx : token.end()]

    return None


def _truncate_snippet(snippet: str, limit: int = 120) -> str:
    """Return a truncated representation suitable for logging."""

    compact = " ".join(snippet.strip().split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."
