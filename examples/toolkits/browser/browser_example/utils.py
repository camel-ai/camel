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
"""Common utility functions for subtask toolkit."""

import datetime
import json
import re
from pathlib import Path
from typing import Any


# === Timestamps ===
def get_timestamp_iso() -> str:
    """
    Get ISO format timestamp.

    Returns:
        Current timestamp in ISO format
    """
    return datetime.datetime.now().isoformat()


def get_timestamp_filename() -> str:
    """
    Get filename-safe timestamp.

    Returns:
        Current timestamp in YYYYMMDD_HHMMSS format
    """
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')


# === File I/O ===
def load_json(file_path: str) -> dict[str, Any]:
    """
    Load JSON file with standard encoding.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# === Website-scoped Skills Directories ===
_WEBSITE_SLUG_RE = re.compile(r"[^a-z0-9]+")


def website_slug(website: str) -> str:
    """
    Normalize a website name into a filesystem-friendly directory slug.

    Examples:
        "Google Flights" -> "google_flights"
        "BBC News" -> "bbc_news"
    """
    normalized = (website or "").strip().lower()
    normalized = _WEBSITE_SLUG_RE.sub("_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "unknown_website"


# === Session Metrics ===
def _parse_json_objects_log(log_path: Path) -> list[dict[str, Any]]:
    """
    Parse a log file that contains one JSON object per entry, concatenated.

    This matches the format used by `complete_browser_log.log`.
    """
    if not log_path.exists():
        return []

    content = log_path.read_text(encoding="utf-8", errors="ignore")
    actions: list[dict[str, Any]] = []

    current_obj = ""
    brace_count = 0
    in_string = False
    escape_next = False

    for char in content:
        if escape_next:
            current_obj += char
            escape_next = False
            continue

        if char == "\\" and in_string:
            current_obj += char
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string

        if not in_string:
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1

        current_obj += char

        if brace_count == 0 and current_obj.strip():
            try:
                actions.append(json.loads(current_obj.strip()))
            except Exception:
                pass
            current_obj = ""

    return actions


def compute_session_summary(
    *,
    session_dir: Path,
    task_id: str | None = None,
) -> dict[str, Any]:
    """
    Compute a structured summary for a single session directory.

    Uses existing artifacts produced by SkillsAgent:
      - complete_browser_log.log
      - agent_communication_log.json
    """
    session_dir = session_dir.resolve()
    complete_log = session_dir / "complete_browser_log.log"
    agent_comm_path = session_dir / "agent_communication_log.json"

    main_actions = _parse_json_objects_log(complete_log)
    actions_total = len(main_actions)

    comm_summary: dict[str, Any] = {}
    browser_tool_calls = 0

    if agent_comm_path.exists():
        try:
            comm_data = load_json(str(agent_comm_path))
            comm_summary = (
                comm_data.get("summary", {})
                if isinstance(comm_data, dict)
                else {}
            )
            if isinstance(comm_summary, dict):
                browser_tool_calls = int(
                    comm_summary.get("browser_tool_calls", 0) or 0
                )
        except Exception:
            pass

    return {
        "task_id": task_id,
        "session_dir": str(session_dir),
        "reuse": {
            "actions_total": actions_total,
            "browser_tool_calls": browser_tool_calls,
        },
        "agent_comm_summary": comm_summary,
    }
