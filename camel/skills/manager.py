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
from threading import RLock
from typing import List, Optional, Tuple

from camel.messages import BaseMessage
from camel.skills.model import SkillError, SkillLoadOutcome
from camel.skills.prompt import render_skills_overview
from camel.skills.provider import SkillProvider
from camel.skills.provider_fs import FilesystemSkillProvider


class SkillManager:
    def __init__(self, provider: Optional[SkillProvider] = None) -> None:
        self._provider = provider or FilesystemSkillProvider()
        self._cache: dict[Path, SkillLoadOutcome] = {}
        self._lock = RLock()

    def list(self, cwd: Path, force_reload: bool = False) -> SkillLoadOutcome:
        cwd = self._normalize_cwd(cwd)
        if not force_reload:
            cached = self._cache.get(cwd)
            if cached is not None:
                return cached

        outcome = self._provider.list(cwd)
        with self._lock:
            self._cache[cwd] = outcome
        return outcome

    def build_overview_messages(
        self, cwd: Path
    ) -> Tuple[List[BaseMessage], List[SkillError]]:
        outcome = self.list(cwd)
        if not outcome.skills:
            return [], outcome.errors

        content = render_skills_overview(outcome.skills)
        if not content:
            return [], outcome.errors

        return (
            [
                BaseMessage.make_user_message(
                    role_name="User",
                    content=content,
                    meta_dict={"skill": "true"},
                )
            ],
            outcome.errors,
        )

    def _normalize_cwd(self, cwd: Path) -> Path:
        try:
            return cwd.resolve()
        except OSError:
            return cwd.absolute()
