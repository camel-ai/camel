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
Convert subtask JSON configs to Claude Code Skills format.

This script reads subtask configurations from subtask_configs/*.json
and converts them to the standard Skills format with:
- One folder per skill
- SKILL.md with YAML frontmatter + description
- actions.json with the action sequence
"""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List


def slugify(name: str) -> str:
    """Convert a name to a URL-friendly slug.

    Args:
        name: The name to convert

    Returns:
        A lowercase, hyphenated slug
    """
    # Convert to lowercase
    slug = name.lower()
    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)
    # Remove non-alphanumeric characters except hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    return slug


def escape_yaml_string(s: str) -> str:
    """Escape a string for YAML.

    Args:
        s: The string to escape

    Returns:
        Properly escaped/quoted YAML string
    """
    if not s:
        return '""'
    # If string contains special characters, wrap in quotes
    if (
        ':' in s
        or '\n' in s
        or '"' in s
        or "'" in s
        or s.startswith('-')
        or s.startswith('#')
    ):
        # Escape double quotes and wrap in double quotes
        escaped = s.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    return s


def generate_skill_md(
    subtask: Dict[str, Any], source_info: Dict[str, Any]
) -> str:
    """Generate SKILL.md content for a subtask.

    Args:
        subtask: The subtask definition
        source_info: Source information (log_file, task_description)

    Returns:
        The SKILL.md content as a string
    """
    # Build YAML frontmatter
    yaml_lines = [
        "---",
        f"name: {slugify(subtask['name'])}",
        f"id: {subtask['id']}",
        f"description: {escape_yaml_string(subtask['description'])}",
    ]

    # Add index info for replay
    if 'start_index' in subtask:
        yaml_lines.append(f"start_index: {subtask['start_index']}")
    if 'end_index' in subtask:
        yaml_lines.append(f"end_index: {subtask['end_index']}")

    # Add URL info if available (URLs contain colons, so quote them)
    if subtask.get('url_start'):
        yaml_lines.append(f"url_start: \"{subtask['url_start']}\"")
    if subtask.get('url_end'):
        yaml_lines.append(f"url_end: \"{subtask['url_end']}\"")

    # Add variables if any
    if subtask.get('variables'):
        yaml_lines.append("variables:")
        for var_name, var_config in subtask['variables'].items():
            yaml_lines.append(f"  {var_name}:")
            yaml_lines.append(f"    type: {var_config.get('type', 'string')}")
            default_val = str(var_config.get('default_value', '')).replace(
                '"', '\\"'
            )
            yaml_lines.append(f"    default_value: \"{default_val}\"")
            desc_val = str(var_config.get('description', '')).replace(
                '"', '\\"'
            )
            yaml_lines.append(f"    description: \"{desc_val}\"")
            if 'action_index' in var_config:
                yaml_lines.append(
                    f"    action_index: {var_config['action_index']}"
                )
            if 'arg_position' in var_config:
                yaml_lines.append(
                    f"    arg_position: {var_config['arg_position']}"
                )

    # Add source info
    yaml_lines.append("source:")
    if source_info.get('log_file'):
        # Store log_file path - will be converted to relative path by caller
        yaml_lines.append(f"  log_file: \"{source_info['log_file']}\"")
    if source_info.get('task_description'):
        # Escape quotes and limit length for YAML
        task_desc = source_info['task_description'].strip()[:200]
        task_desc = task_desc.replace('"', '\\"')
        yaml_lines.append(f"  task_description: \"{task_desc}\"")

    yaml_lines.append("---")

    # Build markdown content
    md_lines = [
        "",
        f"# {subtask['name']}",
        "",
        subtask['description'],
        "",
    ]

    # Add variables section if any
    if subtask.get('variables'):
        md_lines.extend(
            [
                "## Variables",
                "",
            ]
        )
        for var_name, var_config in subtask['variables'].items():
            default = var_config.get('default_value', 'N/A')
            desc = var_config.get('description', '')
            md_lines.append(f"- **{var_name}** (default: `{default}`): {desc}")
        md_lines.append("")

    # Add execution info
    if subtask.get('url_start'):
        md_lines.extend(
            [
                "## Execution Context",
                "",
                f"- **Start URL**: {subtask['url_start']}",
            ]
        )
        if subtask.get('url_end'):
            md_lines.append(f"- **End URL**: {subtask['url_end']}")
        md_lines.append("")

    return "\n".join(yaml_lines) + "\n".join(md_lines)


def generate_actions_json(subtask: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate actions.json content for a subtask.

    Args:
        subtask: The subtask definition

    Returns:
        The actions list for JSON serialization
    """
    actions = []
    for action in subtask.get('actions', []):
        # Create a clean action entry
        clean_action = {
            'action_step': action.get('action_step'),
            'action': action.get('action'),
            'element_label': action.get('element_label'),
            'args': action.get('args', []),
        }

        # Add optional fields if present
        if action.get('url_before'):
            clean_action['url_before'] = action['url_before']
        if action.get('url_after'):
            clean_action['url_after'] = action['url_after']
        if action.get('timestamp'):
            clean_action['timestamp'] = action['timestamp']

        actions.append(clean_action)

    return actions


def convert_subtask_configs_to_skills(
    config_dir: str,
    skills_dir: str,
    clean: bool = False,
) -> Dict[str, Any]:
    """Convert all subtask configs to Skills format.

    Args:
        config_dir: Directory containing subtask config JSON files
        skills_dir: Directory to output skills
        clean: If True, remove existing skills directory before converting

    Returns:
        Conversion summary with statistics
    """
    config_path = Path(config_dir)
    skills_path = Path(skills_dir)

    if not config_path.exists():
        raise ValueError(f"Config directory not found: {config_path}")

    # Clean existing skills directory if requested
    if clean and skills_path.exists():
        print(f"Cleaning existing skills directory: {skills_path}")
        shutil.rmtree(skills_path)

    # Create skills directory
    skills_path.mkdir(parents=True, exist_ok=True)

    # Track conversion stats
    stats = {
        'config_files_processed': 0,
        'skills_created': 0,
        'skills_skipped': 0,
        'errors': [],
    }

    # Process all config files
    config_files = sorted(config_path.glob("*_subtasks.json"))

    if not config_files:
        print(f"No subtask config files found in: {config_path}")
        return stats

    print(f"\nFound {len(config_files)} config file(s) to process\n")
    print("=" * 80)

    for config_file in config_files:
        print(f"\nProcessing: {config_file.name}")
        stats['config_files_processed'] += 1

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            error_msg = f"Failed to load {config_file.name}: {e}"
            print(f"  ERROR: {error_msg}")
            stats['errors'].append(error_msg)
            continue

        # Extract source info and convert log_file to relative path
        log_file_abs = config.get('log_file', '')
        log_file_rel = ''
        if log_file_abs:
            try:
                # Convert to relative path from skills directory
                log_file_path = Path(log_file_abs)
                log_file_rel = os.path.relpath(log_file_path, skills_path)
            except ValueError:
                # If on different drives (Windows), keep absolute
                log_file_rel = log_file_abs

        source_info = {
            'log_file': log_file_rel,
            'task_description': config.get('task_description', ''),
        }

        # Process each subtask
        subtasks = config.get('subtasks', [])
        print(f"  Found {len(subtasks)} subtask(s)")

        for subtask in subtasks:
            subtask_name = subtask.get('name', 'Unknown')

            # Create skill directory name: {slugified-name}
            skill_dir_name = slugify(subtask_name)
            skill_dir = skills_path / skill_dir_name

            # Check if skill already exists
            if skill_dir.exists():
                print(f"    Skipping {skill_dir_name} (already exists)")
                stats['skills_skipped'] += 1
                continue
            
            try:

                # Generate and write actions.json
                actions = generate_actions_json(subtask)
                if not actions:
                    continue  # Skip if no actions defined
                # Create skill directory
                skill_dir.mkdir(parents=True, exist_ok=True)
                actions_json_path = skill_dir / "actions.json"
                with open(actions_json_path, 'w', encoding='utf-8') as f:
                    json.dump(actions, f, indent=2, ensure_ascii=False)
                # Generate and write SKILL.md
                skill_md = generate_skill_md(subtask, source_info)
                skill_md_path = skill_dir / "SKILL.md"
                with open(skill_md_path, 'w', encoding='utf-8') as f:
                    f.write(skill_md)

                print(f"    Created: {skill_dir_name}/")
                stats['skills_created'] += 1

            except Exception as e:
                error_msg = f"Failed to create skill {skill_dir_name}: {e}"
                print(f"    ERROR: {error_msg}")
                stats['errors'].append(error_msg)
                # Clean up partial skill directory
                if skill_dir.exists():
                    shutil.rmtree(skill_dir)

    print("\n" + "=" * 80)
    print("\nCONVERSION SUMMARY")
    print("=" * 80)
    print(f"Config files processed: {stats['config_files_processed']}")
    print(f"Skills created: {stats['skills_created']}")
    print(f"Skills skipped: {stats['skills_skipped']}")
    if stats['errors']:
        print(f"Errors: {len(stats['errors'])}")
        for error in stats['errors']:
            print(f"  - {error}")
    print(f"\nSkills directory: {skills_path}")

    return stats


def main():
    """Main entry point for the conversion script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert subtask configs to Claude Code Skills format"
    )
    parser.add_argument(
        "--config-dir",
        type=str,
        default=None,
        help="Directory containing subtask config JSON files "
        "(default: ./subtask_configs)",
    )
    parser.add_argument(
        "--skills-dir",
        type=str,
        default=None,
        help="Directory to output skills (default: ./skills)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing skills directory before converting",
    )

    args = parser.parse_args()

    # Set default paths relative to script location
    script_dir = Path(__file__).resolve().parent
    config_dir = args.config_dir or str(script_dir / "subtask_configs")
    skills_dir = args.skills_dir or str(script_dir / "browser_skills")

    print("=" * 80)
    print("SUBTASK TO SKILLS CONVERTER")
    print("=" * 80)
    print(f"\nConfig directory: {config_dir}")
    print(f"Skills directory: {skills_dir}")
    print(f"Clean mode: {args.clean}")

    convert_subtask_configs_to_skills(
        config_dir=config_dir,
        skills_dir=skills_dir,
        clean=args.clean,
    )


if __name__ == "__main__":
    main()
