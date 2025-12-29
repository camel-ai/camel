"""
Analyze consecutive individual_action entries to determine if they can form reusable subtasks.

This script uses CAMEL ChatAgent to analyze extracted individual_action groups and determine
if they can be composed into one or more reusable subtasks based on existing subtask patterns.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Import the extraction function and subtask manager
from extract_individual_actions import extract_consecutive_individual_actions
from subtask_manager import SubtaskManager


def load_all_existing_subtasks(subtask_configs_dir: str) -> List[Dict[str, Any]]:
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
    # Format existing subtasks
    existing_subtasks_str = json.dumps(existing_subtasks, indent=2)

    # Format action groups
    action_groups_str = ""
    for idx, group in enumerate(action_groups, 1):
        action_groups_str += f"\n\n=== Action Group {idx} ({len(group)} actions) ===\n"
        for action in group:
            action_groups_str += f"""
Action Step: {action.get('action_step')}
Action: {action.get('action')}
Element Label: {action.get('element_label')}
Args: {action.get('args')}
"""

    prompt = f"""You are an expert at analyzing browser automation workflows and identifying reusable subtask patterns.

**TASK DESCRIPTION:**
{task_description}

**EXISTING SUBTASKS:**
The following subtasks already exist and are available for reuse:
```json
{existing_subtasks_str}
```

**CONSECUTIVE INDIVIDUAL ACTIONS TO ANALYZE:**
{action_groups_str}

**YOUR TASK:**
Analyze each group of consecutive individual actions and determine:

1. Can these actions be composed into one or more reusable subtasks?
2. Are they performing a coherent, reusable operation (e.g., "filter flights by stops", "sort by price", "select specific option")?
3. Do they have variables that could be parameterized for reuse in different contexts?

**OUTPUT FORMAT:**
For each action group that CAN be made into a reusable subtask, provide a JSON object in this exact format:

```json
{{
  "group_number": <group number>,
  "can_be_subtask": true,
  "subtasks": [
    {{
      "name": "<Short Name>",
      "description": "<Detailed description of what this subtask does and when to use it>",
      "start_index": <first action_step>,
      "end_index": <last action_step>,
      "actions": [],
      "variables": {{
        "<variable_name>": {{
          "action_index": <action_step where variable is used>,
          "arg_position": <0 for element_label, 1+ for args>,
          "type": "<string|date|number|etc>",
          "default_value": "<actual value from the action>",
          "description": "<Clear description of what this variable represents and format requirements>"
        }}
      }}
    }}
  ],
  "reasoning": "<Explain why these actions form a coherent, reusable subtask>"
}}
```

For action groups that CANNOT be made into reusable subtasks:
```json
{{
  "group_number": <group number>,
  "can_be_subtask": false,
  "reasoning": "<Explain why these actions are too specific or don't form a coherent reusable pattern>"
}}
```

**IMPORTANT GUIDELINES:**
1. **Variables and arg_position**: Identify which parts of the actions could be parameterized:

   **arg_position = 0** (Target Element):
   - Used when you want to operate on DIFFERENT ELEMENTS based on variable value
   - The variable value will be treated as an aria-label to search for
   - System will find the element with matching aria-label and click/type on it
   - Example: click action on different cities
     - Original log: click('e149') where e149's aria-label is "New York"
     - Variable: {{"arg_position": 0, "default_value": "London"}}
     - Result: System searches for element with aria-label "London" and clicks it

   **arg_position = 1** (Input Content):
   - Used when you want to input DIFFERENT CONTENT into the SAME ELEMENT
   - The variable value directly replaces the text/value to be typed/selected
   - Element stays the same, only the input content changes
   - Example: type action with different dates
     - Original log: type('e100', '2025-01-01')
     - Variable: {{"arg_position": 1, "default_value": "2026-03-15"}}
     - Result: type('e100', '2026-03-15')

   **When to use which:**
   - arg_position=0: "Click on {{city_name}}" - different buttons/links
   - arg_position=1: "Type {{date}} into departure date field" - same field, different input
   - For click actions: usually arg_position=0 (different elements to click)
   - For type actions: arg_position=0 for the input field ref, arg_position=1 for the text content

2. **Coherence**: Only create subtasks for actions that form a logical, complete operation
   - Good: "Filter flights by number of stops" (click filter button → select option)
   - Bad: Random unrelated clicks

3. **Reusability**: Consider if this pattern would be useful in other similar tasks
   - Good: "Apply filter and select option" (generic filtering pattern)
   - Bad: Very specific one-time operations

4. **start_index and end_index**: Use the actual action_step values from the actions

Return ONLY valid JSON objects, one per action group analyzed. Do not include any other text outside the JSON.
"""

    return prompt


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

    json_blocks = re.findall(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)

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
            json_objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text)
            for obj_str in json_objects:
                try:
                    parsed = json.loads(obj_str)
                    results.append(parsed)
                except json.JSONDecodeError:
                    pass

    return results


def analyze_with_agent(
    session_folder: str,
    subtask_configs_dir: str = "/Users/puzhen/Desktop/pre/camel_project/camel/examples/toolkits/subtask_configs",
    auto_save: bool = True,
) -> None:
    """
    Main function to analyze individual actions using ChatAgent.

    Args:
        session_folder: Path to the session log folder
        subtask_configs_dir: Path to the directory containing existing subtask configs
        auto_save: If True, automatically save identified subtasks to a new config file
    """
    print(f"\n{'='*80}")
    print("SUBTASK CANDIDATE ANALYZER")
    print(f"{'='*80}\n")

    # Step 1: Extract consecutive individual actions
    print("Step 1: Extracting consecutive individual actions...")
    action_groups = extract_consecutive_individual_actions(session_folder)

    if not action_groups:
        print("No consecutive individual_action groups found (need 2+ consecutive actions)")
        return

    print(f"✓ Found {len(action_groups)} group(s) of consecutive actions\n")

    # Step 2: Load task description from action_timeline.json
    print("Step 2: Loading task description...")
    timeline_path = Path(session_folder) / "action_timeline.json"
    with open(timeline_path, 'r', encoding='utf-8') as f:
        timeline_data = json.load(f)
        task_description = timeline_data.get('task_description', 'No description available')

    print(f"Task: {task_description}\n")

    # Step 3: Load existing subtasks
    print("Step 3: Loading existing subtasks...")
    existing_subtasks = load_all_existing_subtasks(subtask_configs_dir)
    print(f"✓ Loaded {len(existing_subtasks)} existing subtasks\n")

    # Step 4: Create ChatAgent
    print("Step 4: Initializing ChatAgent...")
    model = ModelFactory.create(
        model_platform=ModelPlatformType.AZURE,
        model_type=ModelType.GPT_4_1,
        model_config_dict={"temperature": 0.0},
    )

    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Subtask Analyzer",
            content="You are an expert at analyzing browser automation workflows and identifying reusable subtask patterns.",
        ),
        model=model,
    )
    print("✓ ChatAgent initialized\n")

    # Step 5: Create analysis prompt
    print("Step 5: Creating analysis prompt...")
    prompt = create_analysis_prompt(task_description, action_groups, existing_subtasks)
    print(f"✓ Prompt created ({len(prompt)} characters)\n")

    # Step 6: Get agent response
    print("Step 6: Analyzing with ChatAgent...")
    print("-" * 80)
    response = agent.step(BaseMessage.make_user_message(role_name="User", content=prompt))
    print("-" * 80)
    print("\n✓ Analysis complete\n")

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
        for result in results:
            if result.get('can_be_subtask'):
                print(f"\n--- Group {result.get('group_number')} ---")
                for subtask in result.get('subtasks', []):
                    print(f"  Name: {subtask.get('name')}")
                    print(f"  Description: {subtask.get('description')}")
                    if subtask.get('variables'):
                        print(f"  Variables: {', '.join(subtask['variables'].keys())}")

        # Step 8: Save new subtasks if auto_save is enabled
        if auto_save and reusable_count > 0:
            print(f"\n{'='*80}")
            print("Step 8: Saving new subtasks...")
            print(f"{'='*80}\n")

            # Initialize SubtaskManager
            manager = SubtaskManager(subtask_configs_dir)
            manager.load_all_subtasks()

            # Collect all new subtasks
            new_subtasks = []
            for result in results:
                if result.get('can_be_subtask'):
                    subtasks = result.get('subtasks', [])
                    new_subtasks.extend(subtasks)

            # Add new subtasks to a new config file
            new_file = manager.add_new_subtasks(
                new_subtasks=new_subtasks,
                session_folder=session_folder,
                task_description=task_description
            )

            print(f"\n✓ Successfully saved to: {subtask_configs_dir}/{new_file}")

        elif not auto_save and reusable_count > 0:
            print(f"\n{'='*80}")
            print("NOTE: Auto-save is disabled. Use auto_save=True to save results.")
            print(f"{'='*80}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_subtask_candidate.py <session_folder_path> [subtask_configs_dir]")
        print("\nExample:")
        print("  python analyze_subtask_candidate.py /path/to/session_logs/session_20251229_164455")
        print("\nOptional:")
        print("  python analyze_subtask_candidate.py /path/to/session_logs/session_20251229_164455 /path/to/subtask_configs")
        sys.exit(1)

    session_folder = sys.argv[1]
    subtask_configs_dir = (
        sys.argv[2] if len(sys.argv) > 2
        else "/Users/puzhen/Desktop/pre/camel_project/camel/examples/toolkits/subtask_configs"
    )

    analyze_with_agent(session_folder, subtask_configs_dir)


if __name__ == "__main__":
    main()
