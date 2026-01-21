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
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import yaml

from camel.skills.model import SkillMetadata, SkillScope


class SkillSpecError(ValueError):
    pass


@dataclass(frozen=True)
class SkillFrontmatter:
    name: str
    description: str
    short_description: Optional[str]


SKILL_FILENAME = "SKILL.md"
MAX_NAME_LEN = 64
MAX_DESCRIPTION_LEN = 1024
MAX_SHORT_DESCRIPTION_LEN = 1024


def split_frontmatter(contents: str) -> Tuple[str, str]:
    lines = contents.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillSpecError("missing YAML frontmatter delimited by ---")

    frontmatter_lines: list[str] = []
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            frontmatter = "\n".join(frontmatter_lines)
            body = "\n".join(lines[i + 1 :])
            if not frontmatter.strip():
                raise SkillSpecError("frontmatter is empty")
            return frontmatter, body
        frontmatter_lines.append(lines[i])

    raise SkillSpecError("missing closing --- for frontmatter")


def parse_frontmatter(contents: str) -> SkillFrontmatter:
    frontmatter_text, _ = split_frontmatter(contents)
    data = yaml.safe_load(frontmatter_text) or {}
    if not isinstance(data, dict):
        raise SkillSpecError("frontmatter must be a mapping")

    name = _sanitize_single_line(_get_required_field(data, "name"))
    description = _sanitize_single_line(
        _get_required_field(data, "description")
    )

    short_description: Optional[str] = None
    metadata = data.get("metadata")
    if isinstance(metadata, dict):
        short_description_value = metadata.get("short-description")
        if isinstance(short_description_value, str):
            short_description = _sanitize_single_line(short_description_value)

    _validate_field(name, MAX_NAME_LEN, "name")
    _validate_field(description, MAX_DESCRIPTION_LEN, "description")
    if short_description is not None:
        _validate_field(
            short_description,
            MAX_SHORT_DESCRIPTION_LEN,
            "metadata.short-description",
        )

    return SkillFrontmatter(
        name=name,
        description=description,
        short_description=short_description,
    )


def parse_skill_metadata(
    contents: str, *, source: str, scope: SkillScope
) -> SkillMetadata:
    frontmatter = parse_frontmatter(contents)
    return SkillMetadata(
        name=frontmatter.name,
        description=frontmatter.description,
        short_description=frontmatter.short_description,
        scope=scope,
        source=source,
    )


def _get_required_field(data: dict, field_name: str) -> str:
    value = data.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise SkillSpecError(f"missing field `{field_name}`")
    return value


def _sanitize_single_line(raw: str) -> str:
    return " ".join(raw.split())


def _validate_field(value: str, max_len: int, field_name: str) -> None:
    if not value:
        raise SkillSpecError(f"missing field `{field_name}`")
    if len(value) > max_len:
        raise SkillSpecError(
            f"invalid {field_name}: exceeds maximum "
            f"length of {max_len} characters"
        )
