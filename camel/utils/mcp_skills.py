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
MCP Skills Management

This module provides a system for managing reusable code skills that agents
develop over time. Skills can be saved, loaded, and shared across different
agent sessions.

Based on the Skills concept from:
https://www.anthropic.com/engineering/code-execution-with-mcp
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from camel.logger import get_logger

logger = get_logger(__name__)


class Skill(BaseModel):
    r"""A reusable code skill that an agent has developed.

    Attributes:
        name (str): Name of the skill (also used as filename).
        description (str): Description of what the skill does.
        code (str): The Python code implementing the skill.
        dependencies (List[str]): List of dependencies (import statements).
        tags (List[str]): Tags for categorizing the skill.
        created_at (datetime): When the skill was created.
        updated_at (datetime): When the skill was last updated.
        usage_count (int): Number of times this skill has been used.
        examples (List[str]): Example usage of the skill.
        metadata (Dict[str, Any]): Additional metadata.
    """

    name: str = Field(description="Name of the skill")
    description: str = Field(description="What the skill does")
    code: str = Field(description="The Python code")
    dependencies: List[str] = Field(
        default_factory=list, description="Required imports"
    )
    tags: List[str] = Field(
        default_factory=list, description="Categorization tags"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    usage_count: int = Field(default=0, description="Usage counter")
    examples: List[str] = Field(
        default_factory=list, description="Usage examples"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional info"
    )

    def to_file_content(self) -> str:
        r"""Convert the skill to Python file content.

        Returns:
            str: Python code with docstring and metadata.
        """
        # Build docstring
        docstring = f'"""\n{self.description}\n\n'
        if self.examples:
            docstring += "Examples:\n"
            for example in self.examples:
                docstring += f"    {example}\n"
        docstring += '\n"""'

        # Build imports
        imports = "\n".join(self.dependencies) if self.dependencies else ""

        # Combine everything
        content = f"# Skill: {self.name}\n"
        content += f"# Created: {self.created_at.isoformat()}\n"
        content += f"# Updated: {self.updated_at.isoformat()}\n"
        if self.tags:
            content += f"# Tags: {', '.join(self.tags)}\n"
        content += "\n"

        if imports:
            content += f"{imports}\n\n"

        content += f"{docstring}\n\n"
        content += f"{self.code}\n"

        return content

    def to_metadata_file(self) -> str:
        r"""Convert the skill metadata to SKILL.md format.

        Returns:
            str: Markdown content with skill metadata.
        """
        md = f"# {self.name}\n\n"
        md += f"{self.description}\n\n"

        md += "## Metadata\n\n"
        md += f"- **Created**: {self.created_at.isoformat()}\n"
        md += f"- **Updated**: {self.updated_at.isoformat()}\n"
        md += f"- **Usage Count**: {self.usage_count}\n"

        if self.tags:
            md += f"- **Tags**: {', '.join(self.tags)}\n"

        if self.dependencies:
            md += "\n## Dependencies\n\n"
            for dep in self.dependencies:
                md += f"- `{dep}`\n"

        if self.examples:
            md += "\n## Examples\n\n"
            for example in self.examples:
                md += f"```python\n{example}\n```\n\n"

        if self.metadata:
            md += "\n## Additional Information\n\n"
            md += "```json\n"
            md += json.dumps(self.metadata, indent=2)
            md += "\n```\n"

        return md


class SkillManager:
    r"""Manager for agent skills.

    This class handles saving, loading, searching, and managing reusable
    code skills that agents develop.

    Args:
        skills_dir (str): Directory where skills are stored.

    Attributes:
        skills_dir (Path): Path to the skills directory.
        skills (Dict[str, Skill]): Loaded skills indexed by name.

    Example:
        >>> manager = SkillManager("/path/to/workspace/skills")
        >>> skill = Skill(
        ...     name="csv_to_dict",
        ...     description="Convert CSV file to dictionary",
        ...     code="def csv_to_dict(filepath): ..."
        ... )
        >>> manager.save_skill(skill)
        >>> loaded = manager.load_skill("csv_to_dict")
    """

    def __init__(self, skills_dir: str) -> None:
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.skills: Dict[str, Skill] = {}

        # Load existing skills
        self._load_all_skills()

        logger.info(f"Initialized SkillManager with {len(self.skills)} skills")

    def _load_all_skills(self) -> None:
        r"""Load all skills from the skills directory."""
        for skill_file in self.skills_dir.glob("*.py"):
            if skill_file.stem not in ["__init__", "__pycache__"]:
                try:
                    skill = self._load_skill_from_file(skill_file)
                    if skill:
                        self.skills[skill.name] = skill
                except Exception as e:
                    logger.warning(f"Failed to load skill {skill_file}: {e}")

    def _load_skill_from_file(self, file_path: Path) -> Optional[Skill]:
        r"""Load a skill from a Python file.

        Args:
            file_path (Path): Path to the skill file.

        Returns:
            Optional[Skill]: The loaded skill, or None if loading fails.
        """
        try:
            code = file_path.read_text()

            # Try to load metadata from accompanying .md file
            md_file = file_path.with_suffix(".md")
            metadata: Dict[str, Any] = {}

            if md_file.exists():
                # Parse markdown metadata
                md_content = md_file.read_text()
                # Simple parsing - can be enhanced
                import re

                usage_match = re.search(
                    r"\*\*Usage Count\*\*: (\d+)", md_content
                )
                usage_count = int(usage_match.group(1)) if usage_match else 0

                tags_match = re.search(r"\*\*Tags\*\*: (.+)", md_content)
                tags = (
                    [t.strip() for t in tags_match.group(1).split(",")]
                    if tags_match
                    else []
                )

                metadata["usage_count"] = usage_count
                metadata["tags"] = tags

            # Extract basic info from code
            name = file_path.stem
            description = "No description"

            # Try to extract description from docstring
            import ast

            try:
                tree = ast.parse(code)
                if (
                    tree.body
                    and isinstance(tree.body[0], ast.Expr)
                    and isinstance(tree.body[0].value, ast.Constant)
                    and isinstance(tree.body[0].value.value, str)
                ):
                    description = tree.body[0].value.value.strip()
            except Exception:
                pass

            skill = Skill(
                name=name,
                description=description,
                code=code,
                usage_count=metadata.get("usage_count", 0),
                tags=metadata.get("tags", []),
            )

            return skill
        except Exception as e:
            logger.error(f"Error loading skill from {file_path}: {e}")
            return None

    def save_skill(self, skill: Skill, overwrite: bool = True) -> bool:
        r"""Save a skill to the skills directory.

        Args:
            skill (Skill): The skill to save.
            overwrite (bool): Whether to overwrite existing skill.
                (default: :obj:`True`)

        Returns:
            bool: True if saved successfully, False otherwise.
        """
        skill_file = self.skills_dir / f"{skill.name}.py"
        md_file = self.skills_dir / f"{skill.name}.md"

        # Check if exists and overwrite is False
        if skill_file.exists() and not overwrite:
            logger.warning(
                f"Skill {skill.name} already exists and overwrite=False"
            )
            return False

        try:
            # Update timestamp
            skill.updated_at = datetime.now()

            # Write Python file
            skill_file.write_text(skill.to_file_content())

            # Write metadata file
            md_file.write_text(skill.to_metadata_file())

            # Update in-memory cache
            self.skills[skill.name] = skill

            logger.info(f"Saved skill: {skill.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to save skill {skill.name}: {e}")
            return False

    def load_skill(self, name: str) -> Optional[Skill]:
        r"""Load a skill by name.

        Args:
            name (str): Name of the skill to load.

        Returns:
            Optional[Skill]: The loaded skill, or None if not found.
        """
        if name in self.skills:
            # Increment usage count
            skill = self.skills[name]
            skill.usage_count += 1
            skill.updated_at = datetime.now()
            self.save_skill(skill)
            return skill

        return None

    def search_skills(
        self, query: str = "", tags: Optional[List[str]] = None
    ) -> List[Skill]:
        r"""Search for skills by query or tags.

        Args:
            query (str): Search query for name or description.
            tags (Optional[List[str]]): Filter by tags.

        Returns:
            List[Skill]: List of matching skills.
        """
        results = []

        for skill in self.skills.values():
            # Check query match
            query_match = (
                not query
                or query.lower() in skill.name.lower()
                or query.lower() in skill.description.lower()
            )

            # Check tags match
            tags_match = not tags or any(tag in skill.tags for tag in tags)

            if query_match and tags_match:
                results.append(skill)

        # Sort by usage count
        results.sort(key=lambda s: s.usage_count, reverse=True)

        return results

    def list_skills(self) -> List[str]:
        r"""List all available skill names.

        Returns:
            List[str]: List of skill names.
        """
        return list(self.skills.keys())

    def delete_skill(self, name: str) -> bool:
        r"""Delete a skill.

        Args:
            name (str): Name of the skill to delete.

        Returns:
            bool: True if deleted successfully, False otherwise.
        """
        skill_file = self.skills_dir / f"{name}.py"
        md_file = self.skills_dir / f"{name}.md"

        try:
            if skill_file.exists():
                skill_file.unlink()
            if md_file.exists():
                md_file.unlink()

            if name in self.skills:
                del self.skills[name]

            logger.info(f"Deleted skill: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete skill {name}: {e}")
            return False

    def get_skills_summary(self) -> str:
        r"""Get a summary of all skills for display to agents.

        Returns:
            str: Formatted summary of available skills.
        """
        if not self.skills:
            return "No skills available yet."

        summary = "# Available Skills\n\n"

        # Sort by usage count
        sorted_skills = sorted(
            self.skills.values(), key=lambda s: s.usage_count, reverse=True
        )

        for skill in sorted_skills:
            summary += f"## {skill.name}\n"
            summary += f"{skill.description}\n"
            if skill.tags:
                summary += f"Tags: {', '.join(skill.tags)}\n"
            summary += f"Used {skill.usage_count} times\n\n"

        return summary

    def export_skills(self, export_path: str) -> bool:
        r"""Export all skills to a JSON file.

        Args:
            export_path (str): Path where to export the skills.

        Returns:
            bool: True if exported successfully, False otherwise.
        """
        try:
            skills_data = [
                skill.model_dump() for skill in self.skills.values()
            ]

            with open(export_path, "w") as f:
                json.dump(skills_data, f, indent=2, default=str)

            logger.info(f"Exported {len(skills_data)} skills to {export_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export skills: {e}")
            return False

    def import_skills(self, import_path: str, overwrite: bool = False) -> int:
        r"""Import skills from a JSON file.

        Args:
            import_path (str): Path to the JSON file with skills.
            overwrite (bool): Whether to overwrite existing skills.
                (default: :obj:`False`)

        Returns:
            int: Number of skills imported.
        """
        try:
            with open(import_path, "r") as f:
                skills_data = json.load(f)

            imported = 0
            for skill_dict in skills_data:
                skill = Skill(**skill_dict)
                if self.save_skill(skill, overwrite=overwrite):
                    imported += 1

            logger.info(f"Imported {imported} skills from {import_path}")
            return imported

        except Exception as e:
            logger.error(f"Failed to import skills: {e}")
            return 0
