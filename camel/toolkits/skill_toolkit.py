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

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import yaml

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
        if not skills:
            return (
                "Load a skill to get detailed instructions for a specific "
                "task. No skills are currently available."
            )
        # Build skill summary lines
        summary_lines = [
            "Load a skill to get detailed instructions for a specific task.",
            "Skills provide specialized knowledge and step-by-step guidance.",
            "Use this when a task matches an available skill's description.",
            "Only the skills listed here are available:",
            "<available_skills>",
        ]
        for skill in skills.values():
            extra_files = self._list_skill_entries(Path(skill["path"]).parent)
            files_text = ", ".join(extra_files) if extra_files else "(none)"
            summary_lines.extend(
                [
                    "  <skill>",
                    f"    <name>{skill['name']}</name>",
                    f"    <description>{skill['description']}</description>",
                    f"    <path>{skill['path']}</path>",
                    f"    <files>{files_text}</files>",
                    "  </skill>",
                ]
            )
        summary_lines.append("</available_skills>")
        # Build markdown list for display
        available = ""
        for skill in skills.values():
            extra_files = self._list_skill_entries(Path(skill["path"]).parent)
            files_text = ", ".join(extra_files) if extra_files else "(none)"
            available += (
                f"- {skill['name']}: {skill['description']} "
                f"({skill['path']})\n"
                f"  - extra files: {files_text}\n"
            )
        return (
            "## Skills\n"
            "A skill is a set of local instructions to follow that is stored "
            "in a `SKILL.md` file. Below is the list of skills that can be "
            "used. Each entry includes a name, description, and file path so "
            "you can open the source for full instructions when using a "
            "specific skill. It also includes additional files in each skill "
            "folder so other files can be loaded on demand. This function can "
            "be used to load Skill.md content, for additional files you can "
            "use other tools to load\n"
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
            "  3) If `scripts/` exist, use available execution tools "
            "(terminal, code runner) to run them instead of rewriting code.\n"
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
            "\n" + "\n".join(summary_lines)
        )

    def _get_skills(self) -> Dict[str, Dict[str, str]]:
        if self._skills_cache is None:
            self._skills_cache = self._scan_skills()
        return self._skills_cache

    def clear_cache(self) -> None:
        r"""Clear the cached skills to force rescanning on next access."""
        self._skills_cache = None

    def _scan_skills(self) -> Dict[str, Dict[str, str]]:
        r"""Scan all skill roots and collect skill metadata.

        Skills are discovered from roots in priority order:
        repo > user > system. If multiple skills have the same name,
        the first one found takes priority.

        Returns:
            Dict[str, Dict[str, str]]: Mapping of skill name to metadata.
        """
        skills: Dict[str, Dict[str, str]] = {}
        for scope, root in self._skill_roots():
            if not root.is_dir():
                continue
            for path in root.rglob("SKILL.md"):
                if self._is_hidden_path(path, root):
                    continue
                skill = self._parse_skill(path)
                if not skill:
                    continue
                name = skill["name"]
                # First skill with this name wins (earlier scope has priority)
                if name in skills:
                    continue
                skills[name] = {
                    "name": name,
                    "description": skill["description"],
                    "path": str(path),
                    "scope": scope,
                }
        return skills

    def _skill_roots(self) -> List[Tuple[str, Path]]:
        r"""Return skill root directories with their scope.

        Scopes are checked in order: repo -> user -> system.
        Earlier scopes take priority when skills have the same name.

        Returns:
            List[Tuple[str, Path]]: List of (scope, path) tuples.
        """
        # Skills are discovered in priority order:
        # 1. repo scope: project-specific skills in working directory
        # 2. user scope: user-level skills in home directory
        # 3. system scope: system-wide skills in /etc
        roots: List[Tuple[str, Path]] = [
            # Repo scope - project-specific skills
            ("repo", self.working_directory / ".camel" / "skills"),
            ("repo", self.working_directory / ".agents" / "skills"),
            # User scope - user-level skills
            ("user", Path.home() / ".camel" / "skills"),
            ("user", Path.home() / ".config" / "camel" / "skills"),
            # System scope - system-wide skills
            ("system", Path("/etc/camel/skills")),
        ]
        return roots

    def _is_hidden_path(self, path: Path, root: Path) -> bool:
        r"""Check if a path contains hidden directories (starting with dot).

        Args:
            path (Path): The path to check.
            root (Path): The root directory to compute relative path from.

        Returns:
            bool: True if the path contains hidden directories.
        """
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        return any(part.startswith(".") for part in rel.parts)

    def _parse_skill(self, path: Path) -> Optional[Dict[str, str]]:
        r"""Parse a SKILL.md file and extract metadata.

        Args:
            path (Path): Path to the SKILL.md file.

        Returns:
            Optional[Dict[str, str]]: Parsed skill data with name,
                description, and body. Returns None if parsing fails.
        """
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
        r"""Split YAML frontmatter from the body of a SKILL.md file.

        Args:
            contents (str): The full contents of the file.

        Returns:
            Tuple[Optional[str], str]: A tuple of (frontmatter, body).
                frontmatter is None if no valid frontmatter delimiter is found.
        """
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
            List[Dict[str, str]]: Skill metadata entries including name,
                description, path, and scope.
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

    def list_skill_files(self, name: str) -> str:
        r"""List files and directories in a skill folder.

        Args:
            name (str): The skill identifier.

        Returns:
            str: Formatted list of files/directories, or error message.
        """
        skills = self._get_skills()
        skill = skills.get(name)
        if not skill:
            available = ", ".join(sorted(skills.keys())) or "none"
            return f"Error: Skill \"{name}\" not found. Available: {available}"

        skill_dir = Path(skill["path"]).parent
        lines = [f"Files in {name}:"]
        for entry in self._list_skill_entries(
            skill_dir, include_skill_md=True
        ):
            lines.append(f"  - {entry}")
        return "\n".join(lines)

    def _list_skill_entries(
        self, skill_dir: Path, include_skill_md: bool = False
    ) -> List[str]:
        r"""List direct child entries in a skill directory.

        Args:
            skill_dir (Path): The skill directory to inspect.
            include_skill_md (bool): Whether to include ``SKILL.md``.

        Returns:
            List[str]: Sorted entry names. Directories end with ``/``.
        """
        entries: List[str] = []
        for item in sorted(skill_dir.iterdir()):
            if not include_skill_md and item.name == "SKILL.md":
                continue
            entries.append(f"{item.name}/" if item.is_dir() else item.name)
        return entries

    def _load_single_skill(self, name: str) -> str:
        r"""Load a single skill by name.

        Args:
            name (str): The skill identifier.

        Returns:
            str: The skill content, or error message if not found.
        """
        skills = self._get_skills()
        skill = skills.get(name)
        if not skill:
            available = ", ".join(sorted(skills.keys())) or "none"
            return f"Error: Skill \"{name}\" not found. Available: {available}"

        path = Path(skill["path"])
        parsed = self._parse_skill(path)
        if not parsed:
            return f"Error: Failed to load skill from {path}"

        base_dir = path.parent
        body = parsed.get("body", "").strip()

        # List files in skill directory
        files_info = [
            f"  - {entry}" for entry in self._list_skill_entries(base_dir)
        ]

        output_lines = [
            f"## Skill: {parsed['name']}",
            "",
            f"**Base directory**: {base_dir}",
        ]

        if files_info:
            output_lines.append("")
            output_lines.append("**Available files**:")
            output_lines.extend(files_info)

        output_lines.append("")
        output_lines.append(body)

        return "\n".join(output_lines).strip()

    def load_skill(self, name: Union[str, List[str]]) -> str:
        r"""Load one or more skills by name.

        Args:
            name (Union[str, List[str]]): A single skill name or list of names.

        Returns:
            str: The skill content(s), or error message if not found.
        """
        if isinstance(name, str):
            return self._load_single_skill(name)

        # Load multiple skills
        results = []
        for skill_name in name:
            results.append(self._load_single_skill(skill_name))

        return "\n\n---\n\n".join(results)

    def get_tools(self) -> List[FunctionTool]:
        r"""Return the skill tools with injected available skills."""
        list_tool = FunctionTool(self.list_skills)
        load_tool = FunctionTool(self.load_skill)
        schema = load_tool.get_openai_tool_schema()
        schema["function"]["description"] = self._build_description()
        load_tool.set_openai_tool_schema(schema)
        return [list_tool, load_tool]
