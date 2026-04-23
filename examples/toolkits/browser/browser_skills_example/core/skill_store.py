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
"""
SkillStore - persist extracted subtasks directly as Skills folders.

Creates one folder per skill:
  - SKILL.md (YAML frontmatter + markdown)
  - actions.json
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from .skill_loader import parse_skill_md
from .subtask_to_skill_converter import (
    generate_actions_json,
    generate_skill_md,
    slugify,
)


def _iter_skill_dirs(skills_dir: Path) -> Iterable[Path]:
    if not skills_dir.exists():
        return []
    dirs: List[Path] = []
    for item in skills_dir.iterdir():
        if not item.is_dir():
            continue
        if (item / "SKILL.md").exists():
            dirs.append(item)
    return sorted(dirs)


def _parse_numeric_id(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
        # Handle strings like "06_filter_by_stops"
        import re

        m = re.match(r"^(\d+)", stripped)
        if m:
            return int(m.group(1))
    return None


class SkillStore:
    """Write extracted subtasks directly into a Skills directory."""

    def __init__(self, skills_dir: str | Path):
        self.skills_dir = Path(skills_dir).expanduser().resolve()
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def load_existing_index(self) -> Tuple[Set[int], Set[str]]:
        """Return (ids, slugs) seen in existing SKILL.md files."""
        ids: Set[int] = set()
        slugs: Set[str] = set()
        for skill_dir in _iter_skill_dirs(self.skills_dir):
            try:
                fm = parse_skill_md(skill_dir / "SKILL.md")
            except Exception:
                continue
            num_id = _parse_numeric_id(fm.get("id"))
            if num_id is not None:
                ids.add(num_id)
            name = fm.get("name")
            if isinstance(name, str) and name.strip():
                slugs.add(name.strip())
        return ids, slugs

    def next_id(self) -> int:
        ids, _ = self.load_existing_index()
        return (max(ids) + 1) if ids else 1

    def _format_id_prefix(self, num_id: int) -> str:
        # Keep directories naturally sorted for typical sizes.
        return str(num_id).zfill(3)

    def write_skill(
        self,
        *,
        subtask: Dict[str, Any],
        source_info: Dict[str, Any],
        overwrite: bool = False,
    ) -> Path:
        """Write a single skill folder and return its path."""
        if "id" not in subtask:
            raise ValueError("subtask is missing required field: id")
        if "name" not in subtask or "description" not in subtask:
            raise ValueError(
                "subtask is missing required fields: name/description"
            )
        if "actions" not in subtask or not isinstance(
            subtask["actions"], list
        ):
            raise ValueError(
                "subtask is missing required field: actions (list)"
            )

        slug = slugify(str(subtask["name"]))
        prefix = self._format_id_prefix(int(subtask["id"]))
        skill_dir = self.skills_dir / f"{prefix}-{slug}"

        if skill_dir.exists() and not overwrite:
            return skill_dir

        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_md = generate_skill_md(subtask, source_info)
        (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

        actions = generate_actions_json(subtask)
        (skill_dir / "actions.json").write_text(
            __import__("json").dumps(actions, indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
        return skill_dir

    def write_subtasks(
        self,
        *,
        subtasks: List[Dict[str, Any]],
        source_info: Dict[str, Any],
        overwrite: bool = False,
        skip_if_slug_exists: bool = True,
    ) -> Dict[str, Any]:
        """Assign IDs and write multiple skills. Returns a summary dict."""
        existing_ids, existing_slugs = self.load_existing_index()
        next_id = (max(existing_ids) + 1) if existing_ids else 1

        created: List[str] = []
        skipped: List[str] = []
        errors: List[str] = []

        for subtask in subtasks:
            try:
                slug = slugify(str(subtask.get("name", "")))
                if skip_if_slug_exists and slug in existing_slugs:
                    skipped.append(str(subtask.get("name", slug)))
                    continue

                subtask = dict(subtask)
                subtask["id"] = next_id
                next_id += 1

                path = self.write_skill(
                    subtask=subtask,
                    source_info=source_info,
                    overwrite=overwrite,
                )
                created.append(str(path))
                existing_slugs.add(slug)
            except Exception as e:
                errors.append(f"{subtask.get('name', 'unknown')}: {e}")

        return {
            "created": created,
            "skipped": skipped,
            "errors": errors,
            "skills_dir": str(self.skills_dir),
        }
