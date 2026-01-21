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

from camel.skills.model import SkillMetadata


def render_skills_overview(skills: list[SkillMetadata]) -> str:
    if not skills:
        return ""

    available_lines = [
        f"- {skill.name}: {skill.description} "
        f"(file: {skill.source.replace('\\\\', '/')})"
        for skill in skills
    ]
    available = "\n".join(available_lines)

    return (
        "## Skills\n"
        "A skill is a set of local instructions to follow that is stored in a "
        "`SKILL.md` file. Below is the list of skills that can be used. Each "
        "entry includes a name, description, and file path so you can open "
        "the source for full instructions when using a specific skill.\n"
        "### Available skills\n"
        f"{available}\n"
        "### How to use skills\n"
        "- Discovery: The list above is the skills available in this session "
        "(name + description + file path). Skill bodies live on disk at the "
        "listed paths.\n"
        "- Trigger rules: If the user names a skill or the task clearly "
        "matches a skill's description shown above, you should use that "
        "skill for this turn.\n"
        "- Missing/blocked: If a named skill isn't in the list or the path "
        "can't be read, say so briefly and continue with the best fallback.\n"
        "- How to use a skill (progressive disclosure):\n"
        "  1) After deciding to use a skill, open its `SKILL.md` with the "
        "terminal toolkit. Read only enough to follow the workflow.\n"
        "  2) If `SKILL.md` points to extra folders such as `references/`, "
        "load only the specific files needed for the request; don't bulk-load "
        "everything.\n"
        "  3) If `scripts/` exist, prefer running or patching them instead of "
        "rewriting large code blocks.\n"
        "  4) If `assets/` or templates exist, reuse them instead of "
        "recreating from scratch.\n"
        "- Coordination and sequencing:\n"
        "  - If multiple skills apply, choose the minimal set that covers the "
        "request and state the order you'll use them.\n"
        "  - Announce which skill(s) you're using and why (one short line). "
        "If you skip an obvious skill, say why.\n"
        "- Context hygiene:\n"
        "  - Keep context small: summarize long sections instead of pasting "
        "them; only load extra files when needed.\n"
        "  - Avoid deep reference-chasing: prefer opening only files directly "
        "linked from `SKILL.md` unless you're blocked.\n"
        "  - When variants exist (frameworks, providers, domains), pick only "
        "the relevant reference file(s) and note that choice.\n"
        "- Safety and fallback: If a skill can't be applied cleanly (missing "
        "files, unclear instructions), state the issue, pick the next-best "
        "approach, and continue."
    )
