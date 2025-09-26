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
    r"```(?:json)?\s*([\s\S]+?)\s*```",
    re.IGNORECASE,
)

logger = logging.getLogger(__name__)


def extract_tool_calls_from_text(content: str) -> List[Dict[str, Any]]:
    """Extract tool call dictionaries from raw text output."""

    if not content:
        return []

    tool_calls: List[Dict[str, Any]] = []
    candidates: List[Any] = []
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

        candidates.append(parsed)
        seen_ranges.append((match.start(1), match.end(1)))

    decoder = json.JSONDecoder()
    idx = 0
    text_length = len(content)
    while idx < text_length:
        char = content[idx]
        if char not in "{[":
            idx += 1
            continue

        try:
            parsed, end = decoder.raw_decode(content, idx)
        except json.JSONDecodeError:
            segment = _extract_enclosed_segment(content, idx)
            if segment is None:
                idx += 1
                continue

            if any(start <= idx < stop for start, stop in seen_ranges):
                idx += len(segment)
                continue

            parsed = _try_parse_json_like(segment)
            if parsed is None:
                idx += 1
                continue

            end = idx + len(segment)

        if any(start <= idx < stop for start, stop in seen_ranges):
            idx = end
            continue

        candidates.append(parsed)
        idx = end

    for candidate in candidates:
        _collect_tool_calls(candidate, tool_calls)

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
    except json.JSONDecodeError:
        pass

    if yaml is not None:
        try:
            return yaml.safe_load(snippet)
        except yaml.YAMLError:
            pass

    try:
        return ast.literal_eval(snippet)
    except (ValueError, SyntaxError):
        return None


def _extract_enclosed_segment(content: str, start: int) -> Optional[str]:
    """Extract a substring with balanced braces or brackets."""

    if content[start] not in "{[":
        return None

    opening = content[start]
    closing = "}" if opening == "{" else "]"
    stack = [closing]
    quote_char: Optional[str] = None
    escape = False

    for idx in range(start + 1, len(content)):
        char = content[idx]

        if quote_char is not None:
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == quote_char:
                quote_char = None
            continue

        if char in {'"', "'"}:
            quote_char = char
            continue

        if char in "{[":
            stack.append("}" if char == "{" else "]")
            continue

        if char in "}]":
            if not stack:
                return None
            expected = stack.pop()
            if char != expected:
                return None
            if not stack:
                return content[start : idx + 1]

    return None
