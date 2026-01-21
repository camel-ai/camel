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

from pathlib import Path
from typing import List, Optional

from camel.skills.loader import SkillLoader, SkillRoot
from camel.skills.model import SkillLoadOutcome, SkillScope
from camel.skills.provider import SkillProvider


class FilesystemSkillProvider(SkillProvider):
    def __init__(self, loader: Optional[SkillLoader] = None) -> None:
        self._loader = loader or SkillLoader()

    def list(self, cwd: Path) -> SkillLoadOutcome:
        roots = default_skill_roots(cwd)
        return self._loader.list(roots)

    def refresh(self, cwd: Path) -> None:
        return None


def default_skill_roots(cwd: Path) -> List[SkillRoot]:
    roots: List[SkillRoot] = []

    repo_root = find_repo_root(cwd)
    if repo_root is not None:
        roots.append(
            SkillRoot(
                path=repo_root / ".camel" / "skills",
                scope=SkillScope.REPO,
            )
        )

    roots.append(
        SkillRoot(
            path=Path.home() / ".camel" / "skills",
            scope=SkillScope.USER,
        )
    )
    roots.append(
        SkillRoot(
            path=Path("/etc/camel/skills"),
            scope=SkillScope.SYSTEM,
        )
    )

    return roots


def find_repo_root(cwd: Path) -> Optional[Path]:
    try:
        current = cwd.resolve()
    except OSError:
        current = cwd.absolute()

    for parent in [current, *current.parents]:
        git_path = parent / ".git"
        if git_path.is_dir() or git_path.is_file():
            return parent
    return None
