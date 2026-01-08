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
from typing import Any, Dict, List, Optional

from modeling import create_default_model

from camel.agents import ChatAgent
from camel.messages import BaseMessage


# === Model & Agent Creation ===
def create_chat_agent(
    role_name: str,
    system_content: str,
    model=None,
    tools: Optional[List] = None,
) -> ChatAgent:
    """
    Create standard ChatAgent with system message.

    Args:
        role_name: Role name for the agent
        system_content: System message content
        model: Model instance (default: creates GPT-4 with temp=0.0)
        tools: List of tools for the agent

    Returns:
        Configured ChatAgent
    """
    if model is None:
        model = create_default_model()

    system_message = BaseMessage.make_assistant_message(
        role_name=role_name, content=system_content
    )

    return ChatAgent(
        system_message=system_message, model=model, tools=tools or []
    )


# === Token Usage ===
def extract_token_usage(usage) -> Dict[str, int]:
    """
    Extract token usage from response usage object.

    Args:
        usage: Usage object or dict from model response

    Returns:
        Dict with 'prompt', 'completion', and 'total' token counts
    """
    if hasattr(usage, 'prompt_tokens') and hasattr(usage, 'completion_tokens'):
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
    elif isinstance(usage, dict):
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
    else:
        prompt_tokens = 0
        completion_tokens = 0

    return {
        'prompt': prompt_tokens,
        'completion': completion_tokens,
        'total': prompt_tokens + completion_tokens,
    }


# === File I/O ===
def load_json(file_path: str) -> Dict[str, Any]:
    """
    Load JSON file with standard encoding.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(file_path: str, data: Any, indent: int = 2):
    """
    Save JSON file with standard encoding.

    Args:
        file_path: Path to save JSON file
        data: Data to serialize
        indent: Indentation level (default: 2)
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


# === Formatting ===
def print_section(
    title: str,
    char: str = "=",
    width: int = 80,
    newline_before: bool = True,
):
    """
    Print section title with separator lines.

    Args:
        title: Section title
        char: Character for separator line
        width: Width of separator line
        newline_before: Add newline before section
    """
    if newline_before:
        print()
    print(char * width)
    print(title)
    print(char * width)


def print_separator(char: str = "=", width: int = 80):
    """
    Print separator line.

    Args:
        char: Character for separator line
        width: Width of separator line
    """
    print(char * width)


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


def resolve_website_skills_dir(skills_root: Path, website: str) -> Path:
    """Return `<skills_root>/<website_slug>` and ensure it exists."""
    website_dir = skills_root / website_slug(website)
    website_dir.mkdir(parents=True, exist_ok=True)
    return website_dir


def count_subtasks_in_dir(skills_dir: Path) -> int:
    """Count subtasks across all `*_subtasks.json` files under `skills_dir`."""
    total = 0
    for file_path in sorted(skills_dir.glob("*_subtasks.json")):
        try:
            data = load_json(str(file_path))
        except Exception:
            continue
        subtasks = data.get("subtasks", [])
        if isinstance(subtasks, list):
            total += len(subtasks)
    return total


# === Session Metrics ===
def _parse_json_objects_log(log_path: Path) -> List[Dict[str, Any]]:
    """
    Parse a log file that contains one JSON object per entry, concatenated.

    This matches the format used by `complete_browser_log.log`.
    """
    if not log_path.exists():
        return []

    content = log_path.read_text(encoding="utf-8", errors="ignore")
    actions: List[Dict[str, Any]] = []

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
    skills_dir: Optional[Path] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute a structured summary for a single session directory.

    Uses existing artifacts produced by SubtaskAgent:
      - complete_browser_log.log
      - non_subtask_actions.json (if available)
      - agent_communication_log.json
    """
    session_dir = session_dir.resolve()
    complete_log = session_dir / "complete_browser_log.log"
    non_subtask_path = session_dir / "non_subtask_actions.json"
    agent_comm_path = session_dir / "agent_communication_log.json"

    main_actions = _parse_json_objects_log(complete_log)
    actions_total = len(main_actions)

    actions_in_subtasks: Optional[int] = None
    reuse_ratio_actions: Optional[float] = None
    if non_subtask_path.exists() and actions_total:
        try:
            non_subtask_actions = load_json(str(non_subtask_path))
            if isinstance(non_subtask_actions, list):
                actions_in_subtasks = actions_total - len(non_subtask_actions)
                reuse_ratio_actions = actions_in_subtasks / actions_total
        except Exception:
            pass

    comm_summary: Dict[str, Any] = {}
    subtask_calls = 0
    browser_tool_calls = 0
    reuse_ratio_calls: Optional[float] = None
    per_subtask: Dict[str, Any] = {}

    if agent_comm_path.exists():
        try:
            comm_data = load_json(str(agent_comm_path))
            comm_summary = comm_data.get("summary", {}) if isinstance(comm_data, dict) else {}
            communications = comm_data.get("communications", []) if isinstance(comm_data, dict) else []

            if isinstance(comm_summary, dict):
                subtask_calls = int(comm_summary.get("subtask_calls", 0) or 0)
                browser_tool_calls = int(comm_summary.get("browser_tool_calls", 0) or 0)

            denom = subtask_calls + browser_tool_calls
            reuse_ratio_calls = (subtask_calls / denom) if denom else 0.0

            if isinstance(communications, list):
                for entry in communications:
                    if not isinstance(entry, dict):
                        continue
                    if entry.get("type") != "subtask_call":
                        continue

                    subtask_id = str(entry.get("subtask_id", "unknown"))
                    subtask_name = entry.get("subtask_name", "")
                    result = entry.get("result", {}) if isinstance(entry.get("result", {}), dict) else {}
                    status = str(result.get("status", "unknown"))

                    stats = per_subtask.setdefault(
                        subtask_id,
                        {
                            "subtask_id": subtask_id,
                            "subtask_name": subtask_name,
                            "calls_total": 0,
                            "success": 0,
                            "partial_success": 0,
                            "error": 0,
                            "other": 0,
                        },
                    )
                    stats["calls_total"] += 1
                    if status in ("success", "partial_success", "error"):
                        stats[status] += 1
                    else:
                        stats["other"] += 1
        except Exception:
            pass

    for stats in per_subtask.values():
        calls_total = stats.get("calls_total", 0) or 0
        if calls_total:
            stats["success_rate"] = stats.get("success", 0) / calls_total
            stats["failure_rate"] = (
                (stats.get("partial_success", 0) + stats.get("error", 0))
                / calls_total
            )
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0

    subtasks_available = (
        count_subtasks_in_dir(skills_dir) if skills_dir is not None else None
    )

    return {
        "task_id": task_id,
        "session_dir": str(session_dir),
        "skills_dir": str(skills_dir.resolve()) if skills_dir is not None else None,
        "subtasks_available": subtasks_available,
        "reuse": {
            "actions_total": actions_total,
            "actions_in_subtasks": actions_in_subtasks,
            "reuse_ratio_actions": reuse_ratio_actions,
            "subtask_calls": subtask_calls,
            "browser_tool_calls": browser_tool_calls,
            "reuse_ratio_calls": reuse_ratio_calls,
        },
        "subtask_stats": sorted(
            per_subtask.values(), key=lambda d: (d.get("calls_total", 0) * -1, d.get("subtask_id", ""))
        ),
        "agent_comm_summary": comm_summary,
    }


def update_cumulative_subtask_stats(
    *,
    stats_path: Path,
    website: str,
    session_subtask_stats: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Update a cumulative per-subtask success/failure tracker on disk.

    `session_subtask_stats` should be `compute_session_summary()["subtask_stats"]`.
    """
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    data: Dict[str, Any] = {}
    if stats_path.exists():
        try:
            data = json.loads(stats_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    subtasks = data.get("subtasks", {})
    if not isinstance(subtasks, dict):
        subtasks = {}

    for s in session_subtask_stats:
        if not isinstance(s, dict):
            continue
        subtask_id = str(s.get("subtask_id", "unknown"))
        entry = subtasks.setdefault(
            subtask_id,
            {
                "subtask_id": subtask_id,
                "subtask_name": s.get("subtask_name", ""),
                "calls_total": 0,
                "success": 0,
                "partial_success": 0,
                "error": 0,
                "other": 0,
            },
        )
        entry["subtask_name"] = s.get("subtask_name", entry.get("subtask_name", ""))
        for key in ("calls_total", "success", "partial_success", "error", "other"):
            entry[key] = int(entry.get(key, 0) or 0) + int(s.get(key, 0) or 0)

    # Recompute derived rates
    for entry in subtasks.values():
        calls_total = int(entry.get("calls_total", 0) or 0)
        if calls_total:
            entry["success_rate"] = int(entry.get("success", 0) or 0) / calls_total
            entry["failure_rate"] = (
                int(entry.get("partial_success", 0) or 0)
                + int(entry.get("error", 0) or 0)
            ) / calls_total
        else:
            entry["success_rate"] = 0.0
            entry["failure_rate"] = 0.0

    data["website"] = website
    data["updated_at"] = get_timestamp_iso()
    data["subtasks"] = subtasks

    stats_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return data
