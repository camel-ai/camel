#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze browser log and subtask replay logs to:
1. Extract actions NOT in subtasks (by comparing timing values)
2. Generate timeline JSON with all agent actions in chronological order
3. Extract aria-label for each action from snapshots
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def extract_aria_label_from_snapshot(snapshot: str, ref: str) -> Optional[str]:
    """
    Extract aria-label for a given ref from snapshot.

    This method uses an improved algorithm:
    1. First tries to extract aria-label (text in quotes)
    2. If not found, looks for text value in child elements
    3. Returns the first child element's text value if available

    Args:
        snapshot: Snapshot text
        ref: Reference ID (e.g., 'e149')

    Returns:
        Aria-label text or child element text, or None if not found
    """
    if not snapshot:
        return None

    lines = snapshot.split('\n')
    target_line_index = -1

    # Step 1: Find the line with the target ref
    for i, line in enumerate(lines):
        if f'[ref={ref}]' in line:
            target_line_index = i
            break

    if target_line_index == -1:
        return None

    target_line = lines[target_line_index]

    # Step 2: Try to extract aria-label (text between quotes)
    label_match = re.search(r'"([^"]+)"', target_line)
    if label_match:
        return label_match.group(1)

    # Step 3: No aria-label found, look for text in child elements
    # Get the indentation level of the target element
    target_indent = len(target_line) - len(target_line.lstrip())

    # Search subsequent lines for child elements with text values
    for i in range(target_line_index + 1, len(lines)):
        child_line = lines[i]

        # Skip empty lines
        if not child_line.strip():
            continue

        # Get child indentation
        child_indent = len(child_line) - len(child_line.lstrip())

        # If indentation is same or less, we've left the children
        if child_indent <= target_indent:
            break

        # Look for text value in child (format: "- element: text_value")
        # Match pattern: ": value" at the end of line
        text_match = re.search(r':\s*(.+)$', child_line)
        if text_match:
            text_value = text_match.group(1).strip()
            # Make sure it's not a ref or attribute marker
            if (
                text_value
                and not text_value.startswith('[')
                and text_value != ':'
            ):
                return text_value

    return None


def load_main_log(log_file: str) -> List[Dict[str, Any]]:
    """Load and parse the main browser log file."""
    actions = []
    print(f"Loading main log file: {log_file}")

    with open(log_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split JSON objects by finding balanced braces
    current_obj = ""
    brace_count = 0
    in_string = False
    escape_next = False

    for char in content:
        if escape_next:
            current_obj += char
            escape_next = False
            continue

        if char == '\\' and in_string:
            current_obj += char
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string

        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1

        current_obj += char

        # When we have a complete JSON object
        if brace_count == 0 and current_obj.strip():
            try:
                action = json.loads(current_obj.strip())
                actions.append(action)
                current_obj = ""
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON object: {e}")
                current_obj = ""

    print(f"✓ Loaded {len(actions)} actions from main log")
    return actions


def load_subtask_log(log_file: str) -> Dict[str, Any]:
    """Load a subtask replay log file."""
    with open(log_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def timing_matches(timing1: Dict, timing2: Dict) -> bool:
    """
    Check if two timing dictionaries match exactly.

    Args:
        timing1: First timing dict
        timing2: Second timing dict

    Returns:
        True if all timing values match exactly
    """
    if not timing1 or not timing2:
        return False

    return timing1 == timing2


def get_latest_snapshot_before_action(main_actions: List[Dict], action_index: int) -> str:
    """
    Get the most recent snapshot before a given action index.

    Note: Handles two different snapshot structures:
    1. Regular actions: outputs.snapshot (dict with 'snapshot' key)
    2. get_page_snapshot: outputs directly (string)

    Args:
        main_actions: List of all main log actions
        action_index: Index of the current action (0-based)

    Returns:
        Snapshot text (empty if not found)
    """
    for i in range(action_index - 1, -1, -1):
        action = main_actions[i]
        action_name = action.get('action', '')
        outputs = action.get('outputs', {})

        # Case 1: get_page_snapshot - outputs is directly a string
        if action_name == 'get_page_snapshot':
            if isinstance(outputs, str) and outputs and '- generic' in outputs:
                return outputs

        # Case 2: Regular action - snapshot is in outputs.snapshot (dict)
        if isinstance(outputs, dict):
            snapshot = outputs.get('snapshot', '')
            if snapshot and isinstance(snapshot, str):
                return snapshot

    return ""


def main():
    # File paths
    main_log_file = "/Users/puzhen/Desktop/pre/camel_project/camel/examples/toolkits/browser_log/hybrid_browser_toolkit_ws_20251228_164540_None.log"

    subtask_files = [
        "/Users/puzhen/Desktop/pre/camel_project/camel/examples/toolkits/browser_log/subtask_replay_actions_20251228_164546.json",
        "/Users/puzhen/Desktop/pre/camel_project/camel/examples/toolkits/browser_log/subtask_replay_actions_20251228_164552.json",
        "/Users/puzhen/Desktop/pre/camel_project/camel/examples/toolkits/browser_log/subtask_replay_actions_20251228_164555.json",
        "/Users/puzhen/Desktop/pre/camel_project/camel/examples/toolkits/browser_log/subtask_replay_actions_20251228_164617.json",
    ]

    # Actions to exclude from timeline
    excluded_actions = {'get_tab_info', 'get_page_snapshot', 'get_som_screenshot'}

    # Load main log
    main_actions = load_main_log(main_log_file)

    # Load all subtasks
    subtasks = []
    all_subtask_timings = set()

    for subtask_file in subtask_files:
        print(f"\nLoading subtask: {subtask_file}")
        subtask_data = load_subtask_log(subtask_file)
        subtasks.append(subtask_data)

        subtask_id = subtask_data.get('subtask_id', 'unknown')
        subtask_name = subtask_data.get('subtask_name', 'Unknown')
        actions = subtask_data.get('actions', [])

        print(f"  Subtask: {subtask_name} ({subtask_id})")
        print(f"  Actions: {len(actions)}")

        # Collect timing values from this subtask
        for action in actions:
            result = action.get('result', {})
            if isinstance(result, dict):
                timing = result.get('timing')
                if timing:
                    # Convert timing dict to a hashable tuple for set storage
                    timing_tuple = tuple(sorted(timing.items()))
                    all_subtask_timings.add(timing_tuple)

    print(f"\n✓ Loaded {len(subtasks)} subtasks with {len(all_subtask_timings)} unique timings")

    # Filter main log actions that are NOT in subtasks
    non_subtask_actions = []

    for action in main_actions:
        outputs = action.get('outputs', {})
        if isinstance(outputs, dict):
            timing = outputs.get('timing')
            if timing:
                timing_tuple = tuple(sorted(timing.items()))
                if timing_tuple not in all_subtask_timings:
                    non_subtask_actions.append(action)
        else:
            # No timing, include it
            non_subtask_actions.append(action)

    print(f"\n✓ Found {len(non_subtask_actions)} actions NOT in subtasks")

    # Save non-subtask actions to file
    output_file = "/Users/puzhen/Desktop/pre/camel_project/camel/examples/toolkits/browser_log/non_subtask_actions.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(non_subtask_actions, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved non-subtask actions to: {output_file}")

    # Generate timeline with all actions in chronological order
    timeline = []

    # Track all subtask actions with their timing
    # Map: timing_tuple -> subtask info
    subtask_action_timings = {}
    # Map: subtask_id -> first_action_timing (for identifying subtask start)
    subtask_first_action = {}

    for subtask in subtasks:
        subtask_id = subtask.get('subtask_id', 'unknown')
        subtask_name = subtask.get('subtask_name', 'Unknown')
        variables_used = subtask.get('variables_used', {})
        actions = subtask.get('actions', [])

        for idx, action in enumerate(actions):
            result = action.get('result', {})
            if isinstance(result, dict):
                timing = result.get('timing')
                if timing:
                    timing_tuple = tuple(sorted(timing.items()))
                    subtask_action_timings[timing_tuple] = {
                        'subtask_id': subtask_id,
                        'subtask_name': subtask_name,
                        'action_index': idx,
                        'variables_used': variables_used,
                    }

                    # Record first action timing for this subtask
                    if idx == 0:
                        subtask_first_action[subtask_id] = {
                            'timing': timing_tuple,
                            'timestamp': action.get('timestamp'),
                            'subtask_name': subtask_name,
                            'variables_used': variables_used,
                        }

    # Check if action failed
    def is_action_failed(action: Dict[str, Any]) -> bool:
        """Check if an action failed."""
        outputs = action.get('outputs', {})

        # Check if outputs contains a failure indicator
        if isinstance(outputs, dict):
            result = outputs.get('result', '')
            if isinstance(result, str):
                # Check for failure patterns
                if any(pattern in result.lower() for pattern in ['failed', 'error', 'not found']):
                    # Exclude "executed successfully" which might contain "error" in context
                    if 'successfully' not in result.lower():
                        return True

        return False

    # Process main log and build timeline
    already_added_subtasks = set()

    for action_index, action in enumerate(main_actions):
        action_name = action.get('action', '')

        # Skip excluded actions
        if action_name in excluded_actions:
            continue

        # Skip failed actions
        if is_action_failed(action):
            continue

        timestamp = action.get('timestamp', '')
        outputs = action.get('outputs', {})

        # Check if this action is part of a subtask
        timing = None
        if isinstance(outputs, dict):
            timing = outputs.get('timing')

        is_subtask_action = False
        subtask_info = None

        if timing:
            timing_tuple = tuple(sorted(timing.items()))
            if timing_tuple in subtask_action_timings:
                is_subtask_action = True
                subtask_info = subtask_action_timings[timing_tuple]

        # If this is a subtask action, check if it's the first one
        if is_subtask_action and subtask_info:
            subtask_id = subtask_info['subtask_id']
            action_index_in_subtask = subtask_info.get('action_index', 0)

            # Only add subtask_replay entry for the first action of each subtask
            if action_index_in_subtask == 0 and subtask_id not in already_added_subtasks:
                # Extract aria label for the first action if it has args
                inputs = action.get('inputs', {})
                args = inputs.get('args', [])
                element_label = None

                if args:
                    # Get the most recent snapshot before this action
                    snapshot_before = get_latest_snapshot_before_action(main_actions, action_index)

                    # Try to extract label from first ref argument
                    for arg in args:
                        if isinstance(arg, str) and re.match(r'^e\d+$', arg):
                            element_label = extract_aria_label_from_snapshot(snapshot_before, arg)
                            if element_label:
                                break

                timeline.append({
                    'timestamp': timestamp,
                    'action_type': 'subtask_replay',
                    'subtask_id': subtask_id,
                    'subtask_name': subtask_info['subtask_name'],
                    'element_label': element_label,
                    'variables_used': subtask_info.get('variables_used', {}),
                })

                already_added_subtasks.add(subtask_id)

        # If not a subtask action, add as individual action
        elif not is_subtask_action:
            inputs = action.get('inputs', {})
            args = inputs.get('args', [])

            # Extract aria label from snapshot
            element_label = None
            if args:
                # Get the most recent snapshot before this action
                snapshot_before = get_latest_snapshot_before_action(main_actions, action_index)

                # Try to extract label from first ref argument
                for arg in args:
                    if isinstance(arg, str) and re.match(r'^e\d+$', arg):
                        element_label = extract_aria_label_from_snapshot(snapshot_before, arg)
                        if element_label:
                            break

            timeline.append({
                'timestamp': timestamp,
                'action_type': 'individual_action',
                'action': action_name,
                'element_label': element_label,
                'args': args,
            })

    # Save timeline
    timeline_file = "/Users/puzhen/Desktop/pre/camel_project/camel/examples/toolkits/browser_log/action_timeline.json"
    with open(timeline_file, 'w', encoding='utf-8') as f:
        json.dump(timeline, f, indent=2, ensure_ascii=False)

    print(f"✓ Generated timeline with {len(timeline)} entries")
    print(f"✓ Saved timeline to: {timeline_file}")

    # Print summary
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    print(f"Total actions in main log: {len(main_actions)}")
    print(f"Actions in subtasks: {len(main_actions) - len(non_subtask_actions)}")
    print(f"Actions NOT in subtasks: {len(non_subtask_actions)}")
    print(f"Timeline entries: {len(timeline)}")
    print(f"  - Subtask replays: {len(already_added_subtasks)}")
    print(f"  - Individual actions: {len(timeline) - len(already_added_subtasks)}")
    print("\nOutput files:")
    print(f"  - Non-subtask actions: {output_file}")
    print(f"  - Timeline: {timeline_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
