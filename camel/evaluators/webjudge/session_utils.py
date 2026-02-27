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

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def truncate_middle(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    keep_head = max_chars // 2
    keep_tail = max_chars - keep_head - len("\n...[truncated]...\n")
    if keep_tail < 0:
        keep_tail = 0
    return (
        text[:keep_head]
        + "\n...[truncated]...\n"
        + (text[-keep_tail:] if keep_tail else "")
    )


def extract_json_object(text: str) -> Dict[str, Any]:
    candidate = text.strip()
    fenced = re.search(r"```json\s*(.*?)\s*```", candidate, re.DOTALL)
    if fenced:
        candidate = fenced.group(1).strip()

    try:
        loaded = json.loads(candidate)
        if isinstance(loaded, dict):
            return loaded
    except Exception:
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start >= 0 and end > start:
        try:
            loaded = json.loads(candidate[start : end + 1])
            if isinstance(loaded, dict):
                return loaded
        except Exception:
            pass

    raise ValueError("Failed to parse JSON object from model output")


def parse_json_objects_log(log_path: Path) -> List[Dict[str, Any]]:
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
                parsed = json.loads(current_obj.strip())
                if isinstance(parsed, dict):
                    actions.append(parsed)
            except Exception:
                pass
            current_obj = ""

    return actions


def get_current_url_from_tab_info(action: Dict[str, Any]) -> Optional[str]:
    if action.get("action") != "get_tab_info":
        return None
    outputs = action.get("outputs", [])
    if not isinstance(outputs, list):
        return None
    for tab in outputs:
        if isinstance(tab, dict) and tab.get("is_current"):
            url = tab.get("url")
            return url if isinstance(url, str) and url else None
    return None


def get_url_before_after(
    actions: List[Dict[str, Any]], action_index: int
) -> Tuple[Optional[str], Optional[str]]:
    url_before = None
    url_after = None

    for i in range(action_index - 1, -1, -1):
        if actions[i].get("action") == "get_tab_info":
            url_before = get_current_url_from_tab_info(actions[i])
            break

    for i in range(action_index + 1, len(actions)):
        if actions[i].get("action") == "get_tab_info":
            url_after = get_current_url_from_tab_info(actions[i])
            break

    return url_before, url_after


def split_line(line: str) -> Tuple[str, str]:
    """Split a line into leading spaces and the rest of the line."""
    # Find the index of the first non-whitespace character
    index = len(line) - len(line.lstrip())
    # Split the line into leading spaces and the rest
    leading_spaces = line[:index] if index > 0 else ""
    rest_of_line = line[index:].lstrip()  # Remove leading spaces from the rest
    return leading_spaces, rest_of_line


def clean_lines(content: str) -> str:
    """Keep only the meaningful web content for judging.

    Args:
        content: The raw web snapshot content from browser toolkit.
    """
    if not content:
        return ""
    result = []
    for line in content.splitlines():
        leading_spaces, line = split_line(line)
        # Remove everything in square brackets, including the brackets
        line = re.sub(r"\[.*?\]", "", line)

        # Handle "- img" lines separately (no colon required)
        img_match = re.match(r"^-\s*img\s*(.*)", line)
        if img_match:
            content_text = img_match.group(1).strip()
            # Skip if no meaningful content after "- img"
            if not content_text or content_text.lower() == ":":
                continue
            result.append(leading_spaces + f"img: {content_text}")
            continue
        link_match = re.match(r"^-\s*link\s+(.*)", line)
        if link_match:
            content_text = link_match.group(1).strip()
            # Skip if no meaningful content after "- link"
            if not content_text:
                continue
            result.append(leading_spaces + f"link: {content_text}")
            continue
        
        # Handle other lines with "- label: content" pattern
        match = re.match(r"^-\s*([^:\s]+)\s*:\s*(.*)", line)
        if not match:
            continue
        
        label = match.group(1).strip()
        content_text = match.group(2).strip()
        
        # Skip if label is "url"
        if label.lower() == "url":
            continue
        
        # Skip if label is "generic"
        if (label.lower() == "generic") and (not content_text):
            continue
        
        # Keep the line with label and content
        if content_text:
            result.append(leading_spaces + f"{label}: {content_text}")
        else:
            result.append(leading_spaces + f"{label}:")
    
    return "\n".join(result)
