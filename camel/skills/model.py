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

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class SkillScope(str, Enum):
    REPO = "repo"
    USER = "user"
    SYSTEM = "system"
    EXTERNAL = "external"


@dataclass(frozen=True)
class SkillMetadata:
    name: str
    description: str
    short_description: Optional[str]
    scope: SkillScope
    source: str


@dataclass(frozen=True)
class SkillError:
    source: str
    message: str


@dataclass
class SkillLoadOutcome:
    skills: List[SkillMetadata] = field(default_factory=list)
    errors: List[SkillError] = field(default_factory=list)
