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
Skill Loader - Load skills from Claude Code Skills format.

This module reads skills from the skills/ directory and converts them
to a format compatible with the existing SkillsAgent system.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


def parse_skill_md(skill_md_path: Path) -> Dict[str, Any]:
    """Parse a SKILL.md file to extract frontmatter and content.

    Args:
        skill_md_path: Path to the SKILL.md file

    Returns:
        Dictionary with parsed frontmatter data
    """
    with open(skill_md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract YAML frontmatter (between --- markers)
    frontmatter_match = re.match(
        r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL
    )

    if not frontmatter_match:
        raise ValueError(f"No valid YAML frontmatter found in {skill_md_path}")

    frontmatter_text = frontmatter_match.group(1)

    # Parse YAML
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse YAML in {skill_md_path}: {e}")

    return frontmatter


def extract_skill_title(skill_md_path: Path) -> str:
    """Best-effort parse of the first markdown H1 after YAML frontmatter."""
    try:
        content = skill_md_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2]

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def load_actions_json(actions_json_path: Path) -> List[Dict[str, Any]]:
    """Load actions from actions.json file.

    Args:
        actions_json_path: Path to the actions.json file

    Returns:
        List of action dictionaries
    """
    with open(actions_json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def convert_skill_to_subtask(
    skill_dir: Path,
    skills_base_dir: Optional[Path] = None,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """Convert a skill directory to a subtask definition.

    Args:
        skill_dir: Path to the skill directory
        skills_base_dir: Base directory for resolving relative paths

    Returns:
        Tuple of (subtask definition, log_file path or None)
    """
    skill_md_path = skill_dir / "SKILL.md"
    actions_json_path = skill_dir / "actions.json"

    if not skill_md_path.exists():
        raise ValueError(f"SKILL.md not found in {skill_dir}")

    if not actions_json_path.exists():
        raise ValueError(f"actions.json not found in {skill_dir}")

    # Parse SKILL.md
    frontmatter = parse_skill_md(skill_md_path)
    title = extract_skill_title(skill_md_path)

    # Load actions
    actions = load_actions_json(actions_json_path)

    # Convert variables format
    variables = {}
    if frontmatter.get('variables'):
        for var_name, var_config in frontmatter['variables'].items():
            variables[var_name] = {
                'type': var_config.get('type', 'string'),
                'default_value': var_config.get('default_value', ''),
                'description': var_config.get('description', ''),
                'action_index': var_config.get('action_index'),
                'arg_position': var_config.get('arg_position'),
            }

    # Build subtask definition
    subtask = {
        'id': frontmatter.get('id'),
        'name': title or frontmatter.get('name', skill_dir.name),
        'description': frontmatter.get('description', ''),
        'start_index': frontmatter.get('start_index'),
        'end_index': frontmatter.get('end_index'),
        'url_start': frontmatter.get('url_start'),
        'url_end': frontmatter.get('url_end'),
        'variables': variables,
        'actions': actions,
        # Store original skill directory for reference
        '_skill_dir': str(skill_dir),
    }

    # Extract log_file from source info and resolve relative path
    log_file = None
    if frontmatter.get('source'):
        log_file_raw = frontmatter['source'].get('log_file')
        if log_file_raw:
            log_file_path = Path(log_file_raw)
            # If relative path and base dir provided, resolve to absolute
            if not log_file_path.is_absolute() and skills_base_dir:
                log_file = str((skills_base_dir / log_file_raw).resolve())
            else:
                log_file = log_file_raw

    return subtask, log_file


class SkillLoader:
    """Load skills from Claude Code Skills format directory."""

    def __init__(self, skills_dir: str):
        """Initialize the skill loader.

        Args:
            skills_dir: Directory containing skill folders
        """
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, Dict[str, Any]] = {}
        self.skill_log_files: Dict[str, str] = {}

    def load_all_skills(self) -> List[Dict[str, Any]]:
        """Load all skills from the skills directory.

        Returns:
            List of subtask definitions compatible with SkillsAgent
        """
        if not self.skills_dir.exists():
            print(f"Skills directory not found: {self.skills_dir}")
            return []

        # Find all skill directories (directories containing SKILL.md)
        skill_dirs = []
        for item in self.skills_dir.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                skill_dirs.append(item)

        skill_dirs = sorted(skill_dirs)

        if not skill_dirs:
            print(f"No skills found in: {self.skills_dir}")
            return []

        print(f"\nLoading {len(skill_dirs)} skill(s) from {self.skills_dir}")

        all_subtasks = []
        for skill_dir in skill_dirs:
            try:
                subtask, log_file = convert_skill_to_subtask(
                    skill_dir, skills_base_dir=self.skills_dir
                )
                skill_id = str(subtask['id'])

                self.skills[skill_id] = subtask
                if log_file:
                    self.skill_log_files[skill_id] = log_file

                all_subtasks.append(subtask)
                print(f"  Loaded: {skill_dir.name} (ID: {skill_id})")

            except Exception as e:
                print(f"  Failed to load {skill_dir.name}: {e}")

        print(f"  Total loaded: {len(all_subtasks)} skill(s)\n")
        return all_subtasks

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get a skill by its ID.

        Args:
            skill_id: The skill ID

        Returns:
            The skill definition or None if not found
        """
        return self.skills.get(str(skill_id))

    def get_log_file(self, skill_id: str) -> Optional[str]:
        """Get the log file path for a skill.

        Args:
            skill_id: The skill ID

        Returns:
            The log file path or None if not found
        """
        return self.skill_log_files.get(str(skill_id))

    def get_skills_as_configs(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Get skills formatted as config tuples for SkillsAgent.

        This method returns data in the format expected by SkillsAgent's
        _load_subtask_configs method: list of (log_file, config) tuples.

        Returns:
            List of (log_file, config) tuples
        """
        # Group skills by log_file
        log_file_groups: Dict[str, List[Dict[str, Any]]] = {}

        for skill_id, skill in self.skills.items():
            log_file = self.skill_log_files.get(skill_id, '')
            if log_file not in log_file_groups:
                log_file_groups[log_file] = []
            log_file_groups[log_file].append(skill)

        # Convert to config format
        configs = []
        for log_file, subtasks in log_file_groups.items():
            config = {
                'log_file': log_file,
                'task_description': '',  # Not needed for execution
                'subtasks': subtasks,
                'metadata': {
                    'total_subtasks': len(subtasks),
                    'created_from': 'skill_loader',
                },
            }
            configs.append((log_file, config))

        return configs

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of loaded skills.

        Returns:
            Dictionary with summary statistics
        """
        return {
            'total_skills': len(self.skills),
            'skills_dir': str(self.skills_dir),
            'skills': [
                {
                    'id': skill['id'],
                    'name': skill['name'],
                    'variables': list(skill.get('variables', {}).keys()),
                }
                for skill in self.skills.values()
            ],
        }


def main():
    """Test the skill loader."""
    import argparse

    parser = argparse.ArgumentParser(description="Test skill loader")
    parser.add_argument(
        "--skills-dir",
        type=str,
        default=None,
        help="Directory containing skills (default: ./skills)",
    )

    args = parser.parse_args()

    # Set default path relative to script location
    script_dir = Path(__file__).resolve().parent
    skills_dir = args.skills_dir or str(script_dir / "browser_skills")

    print("=" * 80)
    print("SKILL LOADER TEST")
    print("=" * 80)
    print(f"\nSkills directory: {skills_dir}\n")

    loader = SkillLoader(skills_dir)
    loader.load_all_skills()

    print("=" * 80)
    print("LOADED SKILLS SUMMARY")
    print("=" * 80)

    summary = loader.get_summary()
    print(f"\nTotal skills: {summary['total_skills']}")
    print("\nSkills:")
    for skill in summary['skills']:
        vars_str = (
            ", ".join(skill['variables']) if skill['variables'] else "none"
        )
        print(f"  [{skill['id']}] {skill['name']} (vars: {vars_str})")

    # Test getting configs format
    print("\n" + "=" * 80)
    print("CONFIG FORMAT OUTPUT")
    print("=" * 80)

    configs = loader.get_skills_as_configs()
    print(f"\nGenerated {len(configs)} config group(s)")
    for log_file, config in configs:
        subtask_count = len(config['subtasks'])
        log_name = Path(log_file).name if log_file else 'N/A'
        print(f"  Log: {log_name} ({subtask_count} subtasks)")


if __name__ == "__main__":
    main()
