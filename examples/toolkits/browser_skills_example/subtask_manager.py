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
# ruff: noqa: E501
"""
Unified Subtask Manager - manages subtask IDs and configurations across all files.

This module provides centralized management for:
1. Loading all subtasks from multiple config files
2. Assigning unique numeric IDs to subtasks
3. Saving subtasks back to config files
4. Renumbering existing subtasks to use numeric IDs
"""

import json
from pathlib import Path
from typing import Any, Dict, List


class SubtaskManager:
    """Manages subtask configurations and IDs across multiple files."""

    def __init__(self, config_dir: str):
        """
        Initialize the subtask manager.

        Args:
            config_dir: Directory containing subtask configuration files
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # All subtasks from all files
        self.all_subtasks: List[Dict[str, Any]] = []

        # Mapping from file to subtasks
        self.file_subtasks: Dict[str, List[Dict[str, Any]]] = {}

        # Mapping from file to full config data
        self.file_configs: Dict[str, Dict[str, Any]] = {}

    def load_all_subtasks(self) -> List[Dict[str, Any]]:
        """
        Load all subtasks from all config files.

        Returns:
            List of all subtask definitions with source file info
        """
        self.all_subtasks = []
        self.file_subtasks = {}
        self.file_configs = {}

        # Load all JSON files in the directory
        for json_file in sorted(self.config_dir.glob("*_subtasks.json")):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # Store full config
                self.file_configs[json_file.name] = config_data

                # Extract subtasks
                subtasks = config_data.get('subtasks', [])
                self.file_subtasks[json_file.name] = subtasks

                for subtask in subtasks:
                    # Add source file info
                    subtask['_source_file'] = json_file.name
                    self.all_subtasks.append(subtask)

            except Exception as e:
                print(f"Warning: Failed to load {json_file}: {e}")

        return self.all_subtasks

    def get_next_numeric_id(self) -> int:
        """
        Get the next available numeric ID.

        Returns:
            Next available numeric ID (1, 2, 3, ...)
        """
        max_id = 0

        for subtask in self.all_subtasks:
            current_id = subtask.get('id', '0')

            # Extract numeric part from ID
            # Handle formats like "01", "1", "06_filter_by_stops", etc.
            if isinstance(current_id, str):
                # Try to extract leading number
                import re

                match = re.match(r'^(\d+)', current_id)
                if match:
                    num_id = int(match.group(1))
                    max_id = max(max_id, num_id)
            elif isinstance(current_id, int):
                max_id = max(max_id, current_id)

        return max_id + 1

    def renumber_all_subtasks(self) -> None:
        """
        Renumber all subtasks with sequential numeric IDs.

        This updates IDs in-memory. Call save_all_subtasks() to persist changes.
        """
        next_id = 1

        # Process each file in order
        for file_name in sorted(self.file_subtasks.keys()):
            subtasks = self.file_subtasks[file_name]

            for subtask in subtasks:
                # Store old ID for reference
                old_id = subtask.get('id')
                subtask['_old_id'] = old_id

                # Assign new numeric ID
                subtask['id'] = next_id
                next_id += 1

    def save_all_subtasks(self, backup: bool = True) -> None:
        """
        Save all subtasks back to their respective config files.

        Args:
            backup: If True, create .backup files before overwriting
        """
        for file_name, config_data in self.file_configs.items():
            file_path = self.config_dir / file_name

            # Create backup if requested
            if backup and file_path.exists():
                backup_path = file_path.with_suffix('.json.backup')
                import shutil

                shutil.copy2(file_path, backup_path)
                print(f"✓ Backed up to {backup_path.name}")

            # Get updated subtasks for this file
            subtasks = self.file_subtasks.get(file_name, [])

            # Remove internal fields
            cleaned_subtasks = []
            for subtask in subtasks:
                cleaned = {
                    k: v for k, v in subtask.items() if not k.startswith('_')
                }
                cleaned_subtasks.append(cleaned)

            # Update config
            config_data['subtasks'] = cleaned_subtasks

            # Update metadata
            if 'metadata' in config_data:
                config_data['metadata']['total_subtasks'] = len(
                    cleaned_subtasks
                )

            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            print(f"✓ Saved {len(cleaned_subtasks)} subtasks to {file_name}")

    def add_new_subtasks(
        self,
        new_subtasks: List[Dict[str, Any]],
        session_folder: str,
        task_description: str,
    ) -> str:
        """
        Add new subtasks to a new config file.

        Args:
            new_subtasks: List of new subtask definitions (without IDs)
            session_folder: Path to the session folder
            task_description: Task description for the config

        Returns:
            Name of the created file
        """
        # Assign numeric IDs to new subtasks
        next_id = self.get_next_numeric_id()

        for subtask in new_subtasks:
            # Remove agent-generated ID if present
            if 'id' in subtask and isinstance(subtask['id'], str):
                subtask['_agent_suggested_id'] = subtask['id']

            # Assign new numeric ID
            subtask['id'] = next_id
            next_id += 1

        # Find next config file number
        existing_numbers = []
        for file_name in self.config_dir.glob("*_subtasks.json"):
            import re

            match = re.match(r'^(\d+)_subtasks\.json$', file_name.name)
            if match:
                existing_numbers.append(int(match.group(1)))

        next_number = max(existing_numbers, default=0) + 1
        new_file_name = f"{next_number}_subtasks.json"

        # Get log file path from session folder
        session_path = Path(session_folder)
        log_file = None

        # Look for complete_browser_log.log
        potential_log = session_path / "complete_browser_log.log"
        if potential_log.exists():
            log_file = str(potential_log)

        # Clean internal fields from subtasks before saving
        cleaned_subtasks = []
        for subtask in new_subtasks:
            cleaned = {
                k: v for k, v in subtask.items() if not k.startswith('_')
            }
            cleaned_subtasks.append(cleaned)

        # Create config structure
        config_data = {
            "log_file": log_file
            or f"{session_folder}/complete_browser_log.log",
            "task_description": task_description,
            "subtasks": cleaned_subtasks,
            "metadata": {
                "total_subtasks": len(cleaned_subtasks),
                "created_from": "subtask_candidate_analyzer",
                "source_session": session_folder,
            },
        }

        # Save to file
        file_path = self.config_dir / new_file_name
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Created new config file: {new_file_name}")
        print(f"  Contains {len(new_subtasks)} new subtask(s)")
        print(f"  IDs assigned: {[s['id'] for s in new_subtasks]}")

        return new_file_name

    def get_subtask_summary(self) -> Dict[str, Any]:
        """
        Get summary of all subtasks.

        Returns:
            Dictionary with summary statistics
        """
        return {
            "total_files": len(self.file_configs),
            "total_subtasks": len(self.all_subtasks),
            "files": {
                file_name: len(subtasks)
                for file_name, subtasks in self.file_subtasks.items()
            },
            "id_range": {
                "min": min(
                    (s.get('id', 0) for s in self.all_subtasks), default=0
                ),
                "max": max(
                    (s.get('id', 0) for s in self.all_subtasks), default=0
                ),
            },
        }


def renumber_existing_subtasks(config_dir: str, backup: bool = True) -> None:
    """
    Renumber all existing subtasks to use sequential numeric IDs.

    Args:
        config_dir: Directory containing subtask configuration files
        backup: If True, create backup files before modifying
    """
    print(f"\n{'='*80}")
    print("RENUMBERING EXISTING SUBTASKS")
    print(f"{'='*80}\n")

    manager = SubtaskManager(config_dir)

    # Load all subtasks
    print("Loading existing subtasks...")
    all_subtasks = manager.load_all_subtasks()
    print(
        f"✓ Loaded {len(all_subtasks)} subtasks from {len(manager.file_configs)} files\n"
    )

    # Show current IDs
    print("Current subtask IDs:")
    for file_name, subtasks in manager.file_subtasks.items():
        print(f"\n  {file_name}:")
        for subtask in subtasks:
            print(f"    - {subtask.get('id')}: {subtask.get('name')}")

    # Renumber
    print(f"\n{'='*80}")
    print("Renumbering all subtasks...")
    manager.renumber_all_subtasks()

    # Show new IDs
    print("\nNew subtask IDs:")
    for file_name, subtasks in manager.file_subtasks.items():
        print(f"\n  {file_name}:")
        for subtask in subtasks:
            old_id = subtask.get('_old_id')
            new_id = subtask.get('id')
            print(f"    - {new_id} (was: {old_id}): {subtask.get('name')}")

    # Save
    print(f"\n{'='*80}")
    print("Saving changes...")
    manager.save_all_subtasks(backup=backup)

    # Summary
    summary = manager.get_subtask_summary()
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total files: {summary['total_files']}")
    print(f"Total subtasks: {summary['total_subtasks']}")
    print(
        f"ID range: {summary['id_range']['min']} - {summary['id_range']['max']}"
    )
    print("\n✓ All subtasks renumbered successfully!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python subtask_manager.py <config_dir>")
        print("\nExample:")
        print("  python subtask_manager.py /path/to/subtask_configs")
        sys.exit(1)

    config_dir = sys.argv[1]
    renumber_existing_subtasks(config_dir, backup=True)
