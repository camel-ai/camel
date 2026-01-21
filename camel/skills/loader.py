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

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from camel.skills.model import (
    SkillError,
    SkillLoadOutcome,
    SkillMetadata,
    SkillScope,
)
from camel.skills.spec import (
    SKILL_FILENAME,
    SkillSpecError,
    parse_skill_metadata,
)


@dataclass(frozen=True)
class SkillRoot:
    path: Path
    scope: SkillScope


class SkillLoader:
    def list(self, roots: Iterable[SkillRoot]) -> SkillLoadOutcome:
        outcome = SkillLoadOutcome()
        for root in roots:
            self._discover_skills(root, outcome)

        outcome.skills = self._dedupe_and_sort(outcome.skills)
        return outcome

    def _discover_skills(
        self,
        root: SkillRoot,
        outcome: SkillLoadOutcome,
    ) -> None:
        if not root.path.is_dir():
            return

        queue = deque([root.path])
        while queue:
            current = queue.popleft()
            try:
                entries = list(current.iterdir())
            except OSError as exc:
                if root.scope != SkillScope.SYSTEM:
                    outcome.errors.append(
                        SkillError(source=str(current), message=str(exc))
                    )
                continue

            for entry in entries:
                name = entry.name
                if name.startswith("."):
                    continue
                if entry.is_symlink():
                    continue
                if entry.is_dir():
                    queue.append(entry)
                    continue
                if entry.is_file() and name == SKILL_FILENAME:
                    self._load_skill(entry, root.scope, outcome)

    def _load_skill(
        self,
        path: Path,
        scope: SkillScope,
        outcome: SkillLoadOutcome,
    ) -> None:
        try:
            contents = path.read_text(encoding="utf-8")
            source = str(path.resolve())
            skill = parse_skill_metadata(contents, source=source, scope=scope)
            outcome.skills.append(skill)
        except (OSError, SkillSpecError) as exc:
            if scope != SkillScope.SYSTEM:
                outcome.errors.append(
                    SkillError(source=str(path), message=str(exc))
                )

    def _dedupe_and_sort(
        self, skills: List[SkillMetadata]
    ) -> List[SkillMetadata]:
        def scope_rank(scope: SkillScope) -> int:
            priority = {
                SkillScope.REPO: 0,
                SkillScope.USER: 1,
                SkillScope.SYSTEM: 2,
                SkillScope.EXTERNAL: 3,
            }
            return priority.get(scope, 99)

        skills.sort(key=lambda s: (scope_rank(s.scope), s.name, s.source))
        seen = set()
        deduped: List[SkillMetadata] = []
        for skill in skills:
            if skill.name in seen:
                continue
            seen.add(skill.name)
            deduped.append(skill)
        return deduped
