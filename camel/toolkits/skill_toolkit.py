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

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit
from camel.toolkits.function_tool import FunctionTool

logger = get_logger(__name__)


class SkillToolkit(BaseToolkit):
    r"""Toolkit for loading SKILL.md content.

    Skills are discovered from filesystem roots and loaded on-demand.
    """

    def __init__(
        self,
        working_directory: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        super().__init__(timeout=timeout)
        self.working_directory = (
            Path(working_directory).resolve()
            if working_directory
            else Path.cwd().resolve()
        )
        self._skills_cache: Optional[Dict[str, Dict[str, str]]] = None

    def _build_description(self) -> str:
        skills = self._get_skills()
        lines = [
            "Load a skill to get detailed instructions for a specific task.",
            "Skills provide specialized knowledge and step-by-step guidance.",
            "Use this when a task matches an available skill's description.",
            "Only the skills listed here are available:",
            "<available_skills>",
        ]
        available = ""
        for skill in skills.values():
            lines.extend(
                [
                    "  <skill>",
                    f"    <name>{skill['name']}</name>",
                    f"    <description>{skill['description']}</description>",
                    f"    <path>{skill['path']}</path>",
                    "  </skill>",
                ]
            )
            available += (
                f"- {skill['name']}: {skill['description']} "
                f"({skill['path']})\n"
            )
        lines.append("</available_skills>")
        if not skills:
            return (
                "Load a skill to get detailed instructions for a specific "
                "task. No skills are currently available."
            )
        return (
            "## Skills\n"
            "A skill is a set of local instructions to follow that is stored "
            "in a `SKILL.md` file. Below is the list of skills that can be "
            "used. Each entry includes a name, description, and file path so "
            "you can open the source for full instructions when using a "
            "specific skill.\n"
            "### Available skills\n"
            f"{available}\n"
            "### How to use skills\n"
            "- Discovery: The list above is the skills available in this "
            "session (name + description + file path). Skill bodies live on "
            "disk at the listed paths.\n"
            "- Trigger rules: If the user names a skill or the task clearly "
            "matches a skill's description shown above, you should use that "
            "skill for this turn.\n"
            "- Missing/blocked: If a named skill isn't in the list or the "
            "path can't be read, say so briefly and continue with the best "
            "fallback.\n"
            "- How to use a skill (progressive disclosure):\n"
            "  1) After deciding to use a skill, open its `SKILL.md` from the "
            "filesystem. Read only enough to follow the workflow.\n"
            "  2) If `SKILL.md` points to extra folders such as `references/` "
            ", load only the specific files needed for the request; don't "
            "bulk-load everything.\n"
            "  3) If `scripts/` exist, prefer running or patching them "
            "instead of rewriting large code blocks.\n"
            "  4) If `assets/` or templates exist, reuse them instead of "
            "recreating from scratch.\n"
            "- Coordination and sequencing:\n"
            "  - If multiple skills apply, choose the minimal set that covers "
            "the request and state the order you'll use them.\n"
            "  - Announce which skill(s) you're using and why "
            "(one short line). If you skip an obvious skill, say why.\n"
            "- Context hygiene:\n"
            "  - Keep context small: summarize long sections instead of "
            "pasting them; only load extra files when needed.\n"
            "  - Avoid deep reference-chasing: prefer opening only files "
            "directly linked from `SKILL.md` unless you're blocked.\n"
            "  - When variants exist (frameworks, providers, domains), pick "
            "only the relevant reference file(s) and note that choice.\n"
            "- Safety and fallback: If a skill can't be applied cleanly "
            "(missing files, unclear instructions), state the issue, pick the "
            "next-best approach, and continue.\n"
            "\n" + " ".join(lines)
        )

    def _get_skills(self) -> Dict[str, Dict[str, str]]:
        self._skills_cache = self._scan_skills()
        return self._skills_cache

    def _scan_skills(self) -> Dict[str, Dict[str, str]]:
        skills: Dict[str, Dict[str, str]] = {}
        for scope, root in self._skill_roots():
            if not root.is_dir():
                continue
            for path in root.rglob("SKILL.md"):
                if self._is_hidden_path(path, root):
                    continue
                info = self._parse_skill(path)
                if not info:
                    continue
                name = info["name"]
                if name in skills:
                    continue
                skills[name] = {
                    "name": name,
                    "description": info["description"],
                    "path": str(path),
                    "scope": scope,
                }
        return skills

    def _skill_roots(self) -> List[Tuple[str, Path]]:
        repo_root = self._find_repo_root()
        codex_home = os.environ.get("CODEX_HOME")
        codex_home_path = Path(codex_home).expanduser() if codex_home else None
        roots: List[Tuple[str, Path]] = [
            ("repo", repo_root / ".camel" / "skills"),
            ("repo", repo_root / ".codex" / "skills"),
            ("repo", repo_root / ".agents" / "skills"),
            ("user", Path.home() / ".camel" / "skills"),
            ("user", Path.home() / ".config" / "agents" / "skills"),
            ("user", Path.home() / ".codex" / "skills"),
            ("system", Path("/etc/camel/skills")),
            ("system", Path("/etc/codex/skills")),
        ]
        if codex_home_path:
            roots.append(("user", codex_home_path / "skills"))
            roots.append(("system", codex_home_path / "skills" / ".system"))
        return roots

    def _find_repo_root(self) -> Path:
        for parent in (
            self.working_directory,
            *self.working_directory.parents,
        ):
            if (parent / ".git").exists():
                return parent
        return self.working_directory

    def _is_hidden_path(self, path: Path, root: Path) -> bool:
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        return any(part.startswith(".") for part in rel.parts)

    def _parse_skill(self, path: Path) -> Optional[Dict[str, str]]:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError:
            logger.warning("PyYAML is not available; skipping skills")
            return None

        try:
            contents = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to read skill %s: %s", path, exc)
            return None

        frontmatter_text, body = self._split_frontmatter(contents)
        if frontmatter_text is None:
            logger.warning("Missing YAML frontmatter in %s", path)
            return None

        try:
            data = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError as exc:
            logger.warning("Invalid YAML frontmatter in %s: %s", path, exc)
            return None

        if not isinstance(data, dict):
            logger.warning("Frontmatter must be a mapping in %s", path)
            return None

        name = data.get("name")
        description = data.get("description")
        if not isinstance(name, str) or not isinstance(description, str):
            logger.warning("Skill missing name/description in %s", path)
            return None

        return {
            "name": name.strip(),
            "description": description.strip(),
            "body": body,
        }

    def _split_frontmatter(self, contents: str) -> Tuple[Optional[str], str]:
        lines = contents.splitlines()
        if not lines or lines[0].strip() != "---":
            return None, contents
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                frontmatter = "\n".join(lines[1:i])
                body = "\n".join(lines[i + 1 :])
                return frontmatter, body
        return None, contents

    def list_skills(self) -> List[Dict[str, str]]:
        r"""List available skills without loading their full content.

        Returns:
            List[Dict[str, str]]: Skill metadata entries.
        """
        skills = self._get_skills()
        return [
            {
                "name": skill["name"],
                "description": skill["description"],
                "path": skill["path"],
                "scope": skill["scope"],
            }
            for skill in skills.values()
        ]

    def get_skill(self, name: str) -> str:
        r"""Load a skill by name.

        Args:
            name (str): The skill identifier from available_skills.

        Returns:
            str: The skill content along with its base directory.
        """
        skills = self._get_skills()
        skill = skills.get(name)
        if not skill:
            available = ", ".join(sorted(skills.keys())) or "none"
            raise ValueError(
                f"Skill \"{name}\" not found. Available skills: {available}"
            )

        path = Path(skill["path"])
        parsed = self._parse_skill(path)
        if not parsed:
            raise ValueError(f"Failed to load skill from {path}")

        base_dir = str(path.parent)
        body = parsed.get("body", "").strip()
        output = "\n".join(
            [
                f"## Skill: {parsed['name']}",
                "",
                f"**Base directory**: {base_dir}",
                "",
                body,
            ]
        ).strip()
        return output

    def get_tools(self) -> List[FunctionTool]:
        r"""Return the skill tools with injected available skills."""
        list_tool = FunctionTool(self.list_skills)
        get_tool = FunctionTool(self.get_skill)
        schema = get_tool.get_openai_tool_schema()
        schema["function"]["description"] = self._build_description()
        get_tool.set_openai_tool_schema(schema)
        return [list_tool, get_tool]
