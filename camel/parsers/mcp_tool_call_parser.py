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
r"""Utility functions for parsing MCP tool calls from model output."""

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
    r"""Extract tool call dictionaries from raw text output.

    Scans the text for fenced code blocks and bare JSON-like segments,
    parses each candidate, and collects every payload that carries a
    ``tool_name`` field.

    Args:
        content (str): The raw model output text to parse.

    Returns:
        List[Dict[str, Any]]: Tool call dictionaries found in the text,
            in the order encountered. Empty if nothing parses.
    """

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
    r"""Collect valid tool call dictionaries from parsed payloads.

    Appends ``payload`` when it is a dict with a non-null ``tool_name``;
    for lists, recurses into each item. Dicts without ``tool_name`` and
    their values are not traversed.

    Args:
        payload (Any): A parsed JSON-like value to inspect.
        accumulator (List[Dict[str, Any]]): The list that collected tool
            calls are appended to.

    Returns:
        None: Collected tool calls are appended to ``accumulator`` in
            place.
    """

    if isinstance(payload, dict):
        if payload.get("tool_name") is None:
            return
        accumulator.append(payload)
    elif isinstance(payload, list):
        for item in payload:
            _collect_tool_calls(item, accumulator)


def _try_parse_json_like(snippet: str) -> Optional[Any]:
    r"""Parse a JSON or JSON-like snippet into Python data.

    Tries strict JSON first, then YAML (when the optional ``yaml``
    dependency is installed), then Python literal evaluation.

    Args:
        snippet (str): The snippet to parse.

    Returns:
        Optional[Any]: The parsed object, or ``None`` when no parser
            accepts the snippet.
    """

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
    r"""Locate a balanced JSON-like segment starting at ``start_idx``.

    Tracks brace/bracket depth with a stack while skipping quoted
    strings, so a segment ends at the token that closes the opening
    bracket.

    Args:
        content (str): The full text being scanned.
        start_idx (int): Index of the opening ``{`` or ``[``.

    Returns:
        Optional[str]: The balanced segment, or ``None`` if the opening
            is not a brace/bracket or it never closes.
    """

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
    r"""Return a truncated representation suitable for logging.

    Collapses whitespace and shortens overly long snippets to ``limit``
    characters with an ellipsis.

    Args:
        snippet (str): The snippet to format.
        limit (int): Maximum length of the result. (default: :obj:`120`)

    Returns:
        str: The compacted, possibly truncated snippet.
    """

    compact = " ".join(snippet.strip().split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."
