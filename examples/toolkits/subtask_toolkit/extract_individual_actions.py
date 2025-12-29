"""
Extract consecutive individual_action entries from action_timeline.json.

This script reads an action_timeline.json file and extracts groups of
consecutive individual_action entries (2 or more in a row).
"""

import json
import sys
from pathlib import Path


def extract_consecutive_individual_actions(timeline_path: str):
    """
    Extract consecutive individual_action entries from action_timeline.json.

    Args:
        timeline_path: Path to the session log folder containing action_timeline.json
    """
    # Construct path to action_timeline.json
    session_folder = Path(timeline_path)
    json_file = session_folder / "action_timeline.json"

    if not json_file.exists():
        print(f"Error: File not found: {json_file}")
        return []

    # Load the JSON file
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    timeline = data.get('timeline', [])

    # Find consecutive individual_action groups
    consecutive_groups = []
    current_group = []

    for entry in timeline:
        if entry.get('action_type') == 'individual_action':
            current_group.append(entry)
        else:
            # If we have a group of 2 or more, save it
            if len(current_group) >= 2:
                consecutive_groups.append(current_group)
            current_group = []

    # Don't forget the last group
    if len(current_group) >= 2:
        consecutive_groups.append(current_group)

    return consecutive_groups


def print_results(groups):
    """Print the extracted groups in a readable format."""
    if not groups:
        print("No consecutive individual_action groups found (need 2+ consecutive actions)")
        return

    print(f"\n{'='*80}")
    print(f"Found {len(groups)} group(s) of consecutive individual_action entries")
    print(f"{'='*80}\n")

    for group_idx, group in enumerate(groups, 1):
        print(f"\n{'─'*80}")
        print(f"Group {group_idx}: {len(group)} consecutive actions")
        print(f"{'─'*80}")

        for action in group:
            print(f"\n  Action Step: {action.get('action_step')}")
            print(f"  Action: {action.get('action')}")
            print(f"  Element Label: {action.get('element_label')}")
            print(f"  Args: {action.get('args')}")

        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_individual_actions.py <session_folder_path>")
        print("Example: python extract_individual_actions.py /path/to/session_logs/session_20251229_164455")
        sys.exit(1)

    session_folder = sys.argv[1]
    groups = extract_consecutive_individual_actions(session_folder)
    print_results(groups)


if __name__ == "__main__":
    main()
