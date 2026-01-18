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
Analyze consecutive individual_action entries to determine if they can
form reusable subtasks.

This script uses CAMEL ChatAgent to analyze extracted individual_action
groups and determine if they can be composed into one or more reusable
subtasks based on existing subtask patterns.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from subtask_manager import SubtaskManager
from utils import create_chat_agent

from camel.messages import BaseMessage

load_dotenv()


def extract_consecutive_individual_actions(timeline_path: str):
    """
    Extract consecutive individual_action entries from action_timeline.json.

    Args:
        timeline_path: Path to the session log folder containing action_timeline.json

    Returns:
        List of consecutive individual_action groups (each group is a list of actions)
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


def load_all_existing_subtasks(
    subtask_configs_dir: str,
) -> List[Dict[str, Any]]:
    """
    Load all existing subtasks from the subtask_configs directory.

    Args:
        subtask_configs_dir: Path to the directory containing subtask config JSON files

    Returns:
        List of all subtask definitions from all config files
    """
    all_subtasks = []
    configs_path = Path(subtask_configs_dir)

    if not configs_path.exists():
        print(f"Warning: Subtask configs directory not found: {configs_path}")
        return []

    # Load all JSON files in the directory
    for json_file in sorted(configs_path.glob("*.json")):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                subtasks = config_data.get('subtasks', [])
                for subtask in subtasks:
                    # Add source file info
                    subtask['_source_file'] = json_file.name
                    all_subtasks.append(subtask)
        except Exception as e:
            print(f"Warning: Failed to load {json_file}: {e}")

    return all_subtasks


def create_analysis_prompt(
    task_description: str,
    action_groups: List[List[Dict[str, Any]]],
    existing_subtasks: List[Dict[str, Any]],
) -> str:
    """
    Create the prompt for the ChatAgent to analyze action groups.

    Args:
        task_description: The original task description
        action_groups: List of consecutive individual_action groups
        existing_subtasks: List of existing subtask definitions

    Returns:
        The formatted prompt string
    """
    # Format existing subtasks - Full JSON
    json.dumps(existing_subtasks, indent=2)

    # Format existing subtasks - Summary list for easy comparison
    existing_subtasks_summary = ""
    has_existing_subtasks = bool(existing_subtasks)

    if has_existing_subtasks:
        existing_subtasks_summary = (
            "\n**EXISTING SUBTASKS SUMMARY (for duplicate checking):**\n"
        )
        for idx, subtask in enumerate(existing_subtasks, 1):
            name = subtask.get('name', 'Unknown')
            description = subtask.get('description', 'No description')
            existing_subtasks_summary += (
                f"{idx}. **{name}**\n   - {description}\n"
            )
    else:
        existing_subtasks_summary = ""

    # Format action groups
    action_groups_str = ""
    for idx, group in enumerate(action_groups, 1):
        action_groups_str += (
            f"\n\n=== Action Group {idx} ({len(group)} actions) ===\n"
        )
        for action in group:
            action_groups_str += f"""
Action Step: {action.get('action_step')}
Action: {action.get('action')}
Element Label: {action.get('element_label')}
Args: {action.get('args')}
"""

    # Build the simplified prompt
    prompt_parts = [
        "You are an expert at analyzing browser automation workflows and identifying reusable subtask patterns.",
        "",
        "**TASK DESCRIPTION:**",
        task_description,
        "",
    ]

    # Add existing subtasks summary if available
    if has_existing_subtasks:
        prompt_parts.extend(
            [
                existing_subtasks_summary,
                "❗ Check if functionality already exists above before creating new subtasks.",
                "",
            ]
        )

    prompt_parts.extend(
        [
            "**ACTION GROUPS TO ANALYZE:**",
            action_groups_str,
            "",
            "**🎯 GUIDELINES:**",
            "",
            "1. **Proper granularity** - Don't wrap entire task as one subtask, break into atomic pieces:",
            "   - ✅ Enter departure (2-4 actions)",
            "   - ✅ Enter destination (2-4 actions)",
            "   - ✅ Set dates (2-5 actions, keep related dates together)",
            "   - ❌ Enter departure + destination + dates + search (too large)",
            "",
            "2. **Date handling:**",
            "   - Round-trip dates: ONE subtask with 2 variables (departure_date, return_date)",
            "   - One-way date: ONE subtask with 1 variable (departure_date)",
            "   - Round-trip vs One-way are DIFFERENT subtasks",
            "",
            "3. **Include confirmation** - If typing is followed by Enter, include both",
            "",
            "4. **Browser initialization** - Opening browser and navigating to a URL CAN be a subtask:",
            "   - ✅ Open browser + visit specific page (e.g., Google Flights)",
            "   - Variable can be the target URL or page type",
            "   - Useful for starting different workflows on different sites",
            "",
            "5. **Identify variables** - For each variable, specify:",
            "   - Which action_step it appears in",
            "   - A clear description of what it represents",
            "",
            "**📋 OUTPUT FORMAT:**",
            "",
            "For reusable subtask:",
            "```json",
            "{{",
            "  \"can_be_subtask\": true,",
            "  \"subtasks\": [",
            "    {{",
            "      \"name\": \"Enter Departure Location\",",
            "      \"description\": \"Enter and select departure city for flight search\",",
            "      \"start_index\": 15,",
            "      \"end_index\": 19,",
            "      \"variables\": {{",
            "        \"departure_city\": {{",
            "          \"action_index\": 17,",
            "          \"description\": \"Name of the departure city (e.g., 'New York', 'London')\"",
            "        }}",
            "      }}",
            "    }}",
            "  ],",
            "  \"reasoning\": \"Reusable pattern for entering any departure city\"",
            "}}",
            "```",
            "",
            "For non-reusable:",
            "```json",
            "{{",
            "  \"can_be_subtask\": false,",
            "  \"reasoning\": \"Only 1 action, too simple\"",
            "}}",
            "```",
            "",
            "**IMPORTANT:**",
            "- Return ONLY valid JSON objects, one per group",
            "- For variables, you only need: action_index and description",
            "- Do NOT provide: arg_position, type, default_value (auto-generated)",
        ]
    )

    prompt = "\n".join(prompt_parts)
    return prompt


def determine_arg_position(action: Dict) -> int:
    """
    Automatically determine arg_position based on the action type.

    Rules:
        - Type-style actions: arg_position = 1 (content argument)
        - Other action types: arg_position = 0 (element argument)
    """

    action_type = action.get('action', '')

    if action_type == 'type':
        # type(element_ref, text) - return index for text parameter
        return 1
    else:
        # click, select, etc. use element_label for positioning
        return 0


def extract_default_value(action: Dict, arg_position: int) -> str:
    """
    Extract default_value from action data.

    The arg_position corresponds to the index in the args array:
        - arg_position = 0: args[0] or element_label (for element references)
        - arg_position = 1: args[1] (for text parameters in type actions)
    """

    action_type = action.get('action', '')

    # For some actions, even if arg_position=0, extract from args instead of element_label
    # These actions have URL or other values as parameters, not element references
    args_based_actions = ['visit_page', 'open_browser']

    if arg_position == 0 and action_type not in args_based_actions:
        # Element parameter: use element_label
        return action.get('element_label', '')
    else:
        # Content or URL parameter: use args[arg_position]
        args = action.get('args', [])
        if len(args) > arg_position:
            return args[arg_position]
        return ''


def infer_variable_type(value: str) -> str:
    """
    Infer the type from a value.
    """

    import re

    # Date format detection
    if re.match(r'\w+ \d{1,2}, \d{4}', str(value)):
        return 'date'

    # Number detection
    if str(value).isdigit():
        return 'number'

    # Default to string
    return 'string'


def clean_url_for_display(url: str) -> str:
    """
    Clean a URL by keeping only the domain and path, removing the query string.

    Args:
        url: The full URL

    Returns:
        The cleaned URL (without query parameters)

    Examples:
    >>> clean_url_for_display("https://www.google.com/travel/flights?tfs=abc&tfu=xyz")
        "https://www.google.com/travel/flights"
        >>> clean_url_for_display("https://example.com/")
        "https://example.com/"
    """
    if not url:
        return ""

    # Split URL, keep only the part before '?'
    if '?' in url:
        return url.split('?')[0]
    return url


def enrich_subtask_definitions(
    agent_results: List[Dict], action_groups: List[List[Dict]]
) -> List[Dict]:
    """
    Expand the agent's simplified output into a complete subtask definition.

    Args:
        agent_results: Simplified results returned by the agent
        action_groups: Original action groups (used to look up action details)

    Returns:
        A list of complete subtask definitions
    """

    enriched_subtasks = []

    # action_step -> action Mapping
    action_map = {}
    for group in action_groups:
        for action in group:
            action_map[action['action_step']] = action

    # Process each subtask returned by agent
    for result in agent_results:
        if not result.get('can_be_subtask'):
            continue

        for subtask in result.get('subtasks', []):
            start_index = subtask['start_index']
            end_index = subtask['end_index']

            # Extract actions between start_index and end_index from action_map
            actions = []
            for step in range(start_index, end_index + 1):
                if step in action_map:
                    # Copy action and preserve url_before/url_after if present
                    action_copy = action_map[step].copy()
                    actions.append(action_copy)

            # Calculate subtask-level URL changes
            url_start = None
            url_end = None
            if actions:
                # Get url_before from the first action
                url_start = actions[0].get('url_before')
                # Get url_after from the last action
                url_end = actions[-1].get('url_after')

            # Enhance description with execution page info
            enhanced_description = subtask['description']
            if url_start:
                clean_url = clean_url_for_display(url_start)
                enhanced_description = (
                    f"{enhanced_description}. Execution page: {clean_url}"
                )

            enriched_subtask = {
                'name': subtask['name'],
                'description': enhanced_description,
                'start_index': start_index,
                'end_index': end_index,
                'actions': actions,
                'variables': {},
                'url_start': url_start,
                'url_end': url_end,
            }

            for var_name, var_info in subtask.get('variables', {}).items():
                action_index = var_info['action_index']
                action = action_map.get(action_index)

                if action:
                    arg_position = determine_arg_position(action)

                    default_value = extract_default_value(action, arg_position)

                    var_type = infer_variable_type(default_value)

                    var_description = var_info.get(
                        'description', f'{var_name} parameter'
                    )

                    enriched_subtask['variables'][var_name] = {
                        'action_index': action_index,
                        'arg_position': arg_position,
                        'type': var_type,
                        'default_value': default_value,
                        'description': var_description,
                    }

            enriched_subtasks.append(enriched_subtask)

    return enriched_subtasks


def parse_agent_response(response_text: str) -> List[Dict[str, Any]]:
    """
    Parse the agent's response to extract JSON objects.

    Args:
        response_text: The raw response from the agent

    Returns:
        List of parsed JSON objects
    """
    results = []

    # Try to extract JSON objects from code blocks or raw text
    # Look for ```json blocks first
    import re

    json_blocks = re.findall(
        r'```json\s*(.*?)\s*```', response_text, re.DOTALL
    )

    if json_blocks:
        for block in json_blocks:
            try:
                parsed = json.loads(block)
                results.append(parsed)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON block: {e}")
    else:
        # Try to parse the entire response as JSON
        try:
            parsed = json.loads(response_text)
            if isinstance(parsed, list):
                results.extend(parsed)
            else:
                results.append(parsed)
        except json.JSONDecodeError:
            # Try to find JSON objects in the text
            json_objects = re.findall(
                r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text
            )
            for obj_str in json_objects:
                try:
                    parsed = json.loads(obj_str)
                    results.append(parsed)
                except json.JSONDecodeError:
                    pass

    return results


def analyze_with_agent(
    session_folder: str,
    subtask_configs_dir: str | None = None,
    auto_save: bool = True,
) -> Dict[str, Any]:
    """
    Main function to analyze individual actions using ChatAgent.

    Args:
        session_folder: Path to the session log folder
        subtask_configs_dir: Path to the directory containing existing subtask configs
        auto_save: If True, automatically save identified subtasks to a new config file

    Returns:
        Dictionary containing analysis results and token usage
    """
    # Set default subtask_configs_dir using relative path
    if subtask_configs_dir is None:
        script_dir = Path(__file__).resolve().parent
        subtask_configs_dir = str(script_dir / "subtask_configs")

    print(f"\n{'='*80}")
    print("SUBTASK CANDIDATE ANALYZER")
    print(f"{'='*80}\n")

    # Step 1: Extract consecutive individual actions
    print("Step 1: Extracting consecutive individual actions...")
    action_groups = extract_consecutive_individual_actions(session_folder)

    if not action_groups:
        print(
            "No consecutive individual_action groups found (need 2+ consecutive actions)"
        )
        return {
            'success': False,
            'message': 'No consecutive individual_action groups found',
            'token_usage': {
                'input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0,
            },
        }

    print(f"✓ Found {len(action_groups)} group(s) of consecutive actions\n")

    # Step 2: Load task description from action_timeline.json
    print("Step 2: Loading task description...")
    timeline_path = Path(session_folder) / "action_timeline.json"
    with open(timeline_path, 'r', encoding='utf-8') as f:
        timeline_data = json.load(f)
        task_description = timeline_data.get(
            'task_description', 'No description available'
        )

    print(f"Task: {task_description}\n")

    # Step 3: Load existing subtasks
    print("Step 3: Loading existing subtasks...")
    existing_subtasks = load_all_existing_subtasks(subtask_configs_dir)
    print(f"✓ Loaded {len(existing_subtasks)} existing subtasks\n")

    # Step 4: Create ChatAgent
    print("Step 4: Initializing ChatAgent...")
    agent = create_chat_agent(
        role_name="Subtask Analyzer",
        system_content="You are an expert at analyzing browser automation workflows and identifying reusable subtask patterns.",
    )
    print("✓ ChatAgent initialized\n")

    # Step 5: Create analysis prompt
    print("Step 5: Creating analysis prompt...")
    prompt = create_analysis_prompt(
        task_description, action_groups, existing_subtasks
    )
    print(f"✓ Prompt created ({len(prompt)} characters)\n")

    # Step 6: Get agent response
    print("Step 6: Analyzing with ChatAgent...")
    print("-" * 80)
    response = agent.step(
        BaseMessage.make_user_message(role_name="User", content=prompt)
    )
    print("-" * 80)

    # Get token usage from response
    token_usage = response.info.get('usage', {})
    input_tokens = token_usage.get('prompt_tokens', 0)
    output_tokens = token_usage.get('completion_tokens', 0)
    total_tokens = token_usage.get('total_tokens', 0)

    print("\n✓ Analysis complete")
    print("  Token usage:")
    print(f"    Input tokens:  {input_tokens:,}")
    print(f"    Output tokens: {output_tokens:,}")
    print(f"    Total tokens:  {total_tokens:,}\n")

    # Step 7: Parse and display results
    print("Step 7: Parsing results...")
    print(f"\n{'='*80}")
    print("AGENT RESPONSE")
    print(f"{'='*80}\n")
    print(response.msg.content)
    print(f"\n{'='*80}")

    # Try to parse structured results
    results = parse_agent_response(response.msg.content)

    if results:
        print(f"\n{'='*80}")
        print("PARSED RESULTS")
        print(f"{'='*80}\n")
        print(json.dumps(results, indent=2))

        # Summary
        reusable_count = sum(1 for r in results if r.get('can_be_subtask'))
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Total action groups analyzed: {len(results)}")
        print(f"Can be made into subtasks: {reusable_count}")
        print(f"Cannot be made into subtasks: {len(results) - reusable_count}")

        # Display each reusable subtask
        for idx, result in enumerate(results, 1):
            if result.get('can_be_subtask'):
                print(f"\n--- Group {idx} ---")
                for subtask in result.get('subtasks', []):
                    print(f"  Name: {subtask.get('name')}")
                    print(f"  Description: {subtask.get('description')}")
                    if subtask.get('variables'):
                        print(
                            f"  Variables: {', '.join(subtask['variables'].keys())}"
                        )

        # Step 8: Save new subtasks if auto_save is enabled
        if auto_save and reusable_count > 0:
            print(f"\n{'='*80}")
            print("Step 8: Saving new subtasks...")
            print(f"{'='*80}\n")

            # Initialize SubtaskManager
            manager = SubtaskManager(subtask_configs_dir)
            manager.load_all_subtasks()

            # Enrich subtasks: expand agent's simplified output to full definition
            print("Enriching subtask definitions...")
            new_subtasks = enrich_subtask_definitions(results, action_groups)
            print(
                f"✓ Enriched {len(new_subtasks)} subtask(s) with auto-generated fields"
            )

            # Add new subtasks to a new config file
            new_file = manager.add_new_subtasks(
                new_subtasks=new_subtasks,
                session_folder=session_folder,
                task_description=task_description,
            )

            print(
                f"\n✓ Successfully saved to: {subtask_configs_dir}/{new_file}"
            )

        elif not auto_save and reusable_count > 0:
            print(f"\n{'='*80}")
            print(
                "NOTE: Auto-save is disabled. Use auto_save=True to save results."
            )
            print(f"{'='*80}")

        # Save analysis report to session folder
        analysis_report = {
            'session_folder': session_folder,
            'task_description': task_description,
            'timestamp': timeline_data.get('timestamp', ''),
            'action_groups_analyzed': len(results),
            'reusable_subtasks_found': reusable_count,
            'token_usage': {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
            },
            'existing_subtasks_count': len(existing_subtasks),
            'results': results,
        }

        report_path = Path(session_folder) / "subtask_analysis_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_report, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*80}")
        print(f"Analysis report saved to: {report_path}")
        print(f"{'='*80}")

        return {
            'success': True,
            'reusable_subtasks_found': reusable_count,
            'token_usage': {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
            },
            'report_path': str(report_path),
        }

    else:
        # No results parsed
        print(
            "\n⚠️  Warning: Could not parse any structured results from agent response"
        )

        # Still save the raw response
        analysis_report = {
            'session_folder': session_folder,
            'task_description': task_description,
            'timestamp': timeline_data.get('timestamp', ''),
            'action_groups_analyzed': len(action_groups),
            'token_usage': {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
            },
            'existing_subtasks_count': len(existing_subtasks),
            'raw_response': response.msg.content,
            'error': 'Failed to parse structured results',
        }

        report_path = Path(session_folder) / "subtask_analysis_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_report, f, indent=2, ensure_ascii=False)

        print(f"Raw response saved to: {report_path}")

        return {
            'success': False,
            'message': 'Failed to parse structured results',
            'token_usage': {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
            },
            'report_path': str(report_path),
        }


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python analyze_subtask_candidate.py <session_folder_path> [subtask_configs_dir]"
        )
        print("\nExample:")
        print(
            "  python analyze_subtask_candidate.py /path/to/session_logs/session_20251229_164455"
        )
        print("\nOptional:")
        print(
            "  python analyze_subtask_candidate.py /path/to/session_logs/session_20251229_164455 /path/to/subtask_configs"
        )
        sys.exit(1)

    session_folder = sys.argv[1]

    # Use command line argument if provided, otherwise use default (None -> handled in function)
    subtask_configs_dir = sys.argv[2] if len(sys.argv) > 2 else None

    analyze_with_agent(session_folder, subtask_configs_dir)


if __name__ == "__main__":
    main()
