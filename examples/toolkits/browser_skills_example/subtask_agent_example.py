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
# ruff: noqa: E501, E402
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Subtask Agent Example

This script demonstrates how to use ChatAgent with subtask functions.
Each subtask from the subtask configuration is wrapped as a callable function
that the agent can use. The agent has both:
1. High-level subtask functions (e.g., enter_departure_location)
2. Low-level HybridBrowserToolkit tools

The agent is instructed to prefer reusable subtask functions when available.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Add project root to path first (before camel imports)
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

from utils import (
    extract_token_usage,
    get_timestamp_filename,
    get_timestamp_iso,
)

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.toolkits.hybrid_browser_toolkit import HybridBrowserToolkit

# Define default directories using relative paths
DEFAULT_BROWSER_LOG_DIR = script_dir.parent / "browser_log"
DEFAULT_SESSION_LOGS_DIR = script_dir.parent / "session_logs"
DEFAULT_SUBTASK_CONFIGS_DIR = script_dir / "subtask_configs"

load_dotenv()


class SubtaskFunction:
    """Wrapper for a subtask that can be called as a function."""

    def __init__(
        self,
        subtask_id: str,
        name: str,
        description: str,
        variables: Dict[str, Any],
        replayer: Any,
        stats_tracker: Optional[Dict[str, Any]] = None,
        session_log_dir: Optional[Path] = None,
    ):
        """Initialize subtask function.

        Args:
            subtask_id: Subtask ID
            name: Subtask name
            description: Subtask description
            variables: Variable definitions
            replayer: ActionReplayer instance
            stats_tracker: Reference to agent's stats dict for tracking
            session_log_dir: Directory to save session logs
        """
        self.subtask_id = subtask_id
        self.name = name
        self.description = description
        self.variables = variables
        self.replayer = replayer
        self.last_result = None
        self.stats_tracker = stats_tracker
        self.session_log_dir = session_log_dir

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the subtask with given variable values.

        Args:
            **kwargs: Variable values (e.g., departure_city="London")

        Returns:
            Execution result with status and snapshot
        """

        # Track subtask call
        if self.stats_tracker is not None:
            self.stats_tracker['subtask_calls'] += 1
            if self.subtask_id not in self.stats_tracker['subtask_details']:
                self.stats_tracker['subtask_details'][self.subtask_id] = {
                    'name': self.name,
                    'calls': 0,
                    'variables_used': [],
                }
            self.stats_tracker['subtask_details'][self.subtask_id][
                'calls'
            ] += 1
            self.stats_tracker['subtask_details'][self.subtask_id][
                'variables_used'
            ].append(kwargs)

        print(f"\n{'🎯 ' + '='*78}")
        print(f"EXECUTING SUBTASK: {self.name}")
        print(f"{'='*80}")
        print(f"📋 Subtask ID: {self.subtask_id}")
        print(f"📝 Description: {self.description}")

        if kwargs:
            print("🔧 Input Variables:")
            for key, value in kwargs.items():
                print(f"   • {key} = {value}")
        else:
            print("🔧 No input variables (fixed operation)")
        print()

        # Set variables in replayer
        self.replayer.subtask_id = self.subtask_id
        self.replayer.variable_overrides = kwargs
        self.replayer.load_subtask_config()

        # Debug: Check if agent recovery is enabled
        print(
            f"🔍 Debug: use_agent_recovery = {self.replayer.use_agent_recovery}"
        )
        print(f"🔍 Debug: recovery_agent = {self.replayer.recovery_agent}")

        # Track recovery calls before execution
        recovery_calls_before = len(
            getattr(self.replayer, 'recovery_history', [])
        )

        # Execute replay
        try:
            print("▶️  Starting subtask execution...")
            print(f"{'─' * 80}\n")

            # Execute the subtask
            execution_result = await self.replayer.replay_subtask()

            # Track recovery calls after execution
            recovery_calls_after = len(
                getattr(self.replayer, 'recovery_history', [])
            )
            recovery_calls_made = recovery_calls_after - recovery_calls_before
            if self.stats_tracker is not None and recovery_calls_made > 0:
                self.stats_tracker['agent_recovery_calls'] += (
                    recovery_calls_made
                )

                # Sum up tokens from new recovery calls
                recovery_history = getattr(
                    self.replayer, 'recovery_history', []
                )
                for i in range(recovery_calls_before, recovery_calls_after):
                    if i < len(recovery_history):
                        record = recovery_history[i]
                        prompt_tokens = record.get('prompt_tokens', 0)
                        completion_tokens = record.get('completion_tokens', 0)
                        total_tokens = record.get(
                            'tokens_used', prompt_tokens + completion_tokens
                        )

                        self.stats_tracker['token_details']['recovery_agent'][
                            'prompt'
                        ] += prompt_tokens
                        self.stats_tracker['token_details']['recovery_agent'][
                            'completion'
                        ] += completion_tokens
                        self.stats_tracker['token_details']['recovery_agent'][
                            'total'
                        ] += total_tokens
                        self.stats_tracker['total_tokens'] += total_tokens

            print(f"\n{'─' * 80}")
            print("✅ Subtask Execution Result:")
            print(f"   Status: {execution_result['status']}")
            print(
                f"   Successful actions: {len(execution_result['successful_actions'])}"
            )
            print(
                f"   Failed actions: {len(execution_result['failed_actions'])}"
            )
            print(
                f"   Skipped actions: {len(execution_result['skipped_actions'])}"
            )

            # Get final snapshot
            print("\n📸 Getting final page snapshot...")
            final_snapshot = (
                await self.replayer.toolkit.browser_get_page_snapshot()
            )
            snapshot_preview = (
                final_snapshot[:200] + "..."
                if len(final_snapshot) > 200
                else final_snapshot
            )
            print(f"   Snapshot length: {len(final_snapshot)} chars")
            print(f"   Preview: {snapshot_preview}")

            result = {
                'status': 'success'
                if execution_result['all_successful']
                else 'partial_success',
                'message': f"Subtask '{self.name}' completed. {len(execution_result['successful_actions'])} successful, {len(execution_result['failed_actions'])} failed",
                'snapshot': final_snapshot,
                'variables_used': kwargs,
                'execution_details': execution_result,
            }

            # Save replay actions to separate log file
            if (
                hasattr(self.replayer, 'replay_actions_log')
                and self.replayer.replay_actions_log
            ):
                # Save to session log directory if available, otherwise to browser_log
                if self.session_log_dir:
                    replay_log_file = (
                        self.session_log_dir
                        / f"subtask_{self.subtask_id}_replay_actions.json"
                    )
                else:
                    # Use browser_log default path
                    replay_log_dir = DEFAULT_BROWSER_LOG_DIR
                    replay_log_dir.mkdir(parents=True, exist_ok=True)
                    replay_log_file = (
                        replay_log_dir
                        / f"subtask_replay_actions_{get_timestamp_filename()}.json"
                    )

                replay_log_file.parent.mkdir(parents=True, exist_ok=True)

                with open(replay_log_file, 'w', encoding='utf-8') as f:
                    json.dump(
                        {
                            'subtask_id': self.subtask_id,
                            'subtask_name': self.name,
                            'variables_used': kwargs,
                            'actions': self.replayer.replay_actions_log,
                        },
                        f,
                        indent=2,
                        ensure_ascii=False,
                    )

                print(f"\n📝 Replay actions logged to: {replay_log_file}")
                print(
                    f"   Total replay actions: {len(self.replayer.replay_actions_log)}"
                )

                # Clear the log for next execution
                self.replayer.replay_actions_log.clear()

            print("\n✅ SUBTASK COMPLETED SUCCESSFULLY")
            print(f"{'='*80}\n")

            self.last_result = result
            return result

        except Exception as e:
            print("\n❌ SUBTASK EXECUTION FAILED")
            print(f"   Error: {e!s}")
            print(f"{'='*80}\n")

            import traceback

            traceback.print_exc()

            result = {
                'status': 'error',
                'message': f"Subtask '{self.name}' failed: {e!s}",
                'snapshot': '',
                'variables_used': kwargs,
                'error': str(e),
            }
            self.last_result = result
            return result

    def get_function_schema(self) -> Dict[str, Any]:
        """Get the function schema for this subtask.

        Returns:
            OpenAI function schema
        """
        # Build parameters from variables
        parameters = {"type": "object", "properties": {}, "required": []}

        if self.variables:
            for var_name, var_config in self.variables.items():
                parameters["properties"][var_name] = {
                    "type": "string"
                    if var_config['type'] in ['string', 'date']
                    else "string",
                    "description": var_config['description'],
                }
                parameters["required"].append(var_name)

            description = f"{self.description}. Variables: {', '.join(self.variables.keys())}"
        else:
            # No variables - fixed operation
            description = f"{self.description}. This is a fixed operation with no parameters."

        return {
            "name": f"subtask_{self.subtask_id}",
            "description": description,
            "parameters": parameters,
        }


class SubtaskAgent:
    """Agent that can execute subtasks as functions."""

    def __init__(
        self,
        subtask_config_dir: str,
        cdp_port: int = 9223,
        use_agent_recovery: bool = True,
    ):
        """Initialize the SubtaskAgent.

        Args:
            subtask_config_dir: Path to directory containing subtask configuration JSON files
            cdp_port: CDP port number
            use_agent_recovery: Use agent recovery for errors
        """
        self.subtask_config_dir = Path(subtask_config_dir)
        self.cdp_port = cdp_port
        self.use_agent_recovery = use_agent_recovery

        # Load all subtask configurations from directory
        self.subtask_configs = []  # List of (log_file, config) tuples
        self._load_subtask_configs()

        # Initialize components
        self.toolkit: Optional[HybridBrowserToolkit] = None
        self.agent: Optional[ChatAgent] = None
        self.subtask_functions: Dict[str, SubtaskFunction] = {}

        # Session log directory for this run
        self.session_timestamp = get_timestamp_filename()
        self.session_log_dir: Optional[Path] = None

        # Base directory for session logs
        self.session_logs_root = DEFAULT_SESSION_LOGS_DIR

        # Store current user task (actual task being executed)
        self.current_user_task = None

        # Statistics tracking
        self.stats = {
            'total_tokens': 0,
            'subtask_calls': 0,
            'browser_tool_calls': 0,
            'agent_recovery_calls': 0,
            'token_details': {
                'main_agent': {'prompt': 0, 'completion': 0, 'total': 0},
                'recovery_agent': {'prompt': 0, 'completion': 0, 'total': 0},
            },
            'subtask_details': {},  # Track each subtask call
            'browser_tool_details': {},  # Track each browser tool call
        }

        # Agent communication log
        self.agent_communication_log = []

        # Store system prompt and tool definitions for logging
        self.system_prompt = None
        self.tool_definitions = []

        # Store current user task (actual task being executed)
        self.current_user_task = None

    def _load_subtask_configs(self):
        """Load all subtask configuration files from the directory."""
        if not self.subtask_config_dir.exists():
            print(
                f"\n⚠️  Subtask config directory not found: {self.subtask_config_dir}"
            )
            print("📁 Creating directory...")
            self.subtask_config_dir.mkdir(parents=True, exist_ok=True)
            print(
                "✓ Directory created. No subtasks available yet (will be populated as tasks are analyzed).\n"
            )
            # Set empty config for backwards compatibility
            self.subtask_config = {}
            return

        if not self.subtask_config_dir.is_dir():
            raise ValueError(
                f"Path is not a directory: {self.subtask_config_dir}"
            )

        # Find all JSON files in the directory
        config_files = sorted(self.subtask_config_dir.glob("*.json"))

        if not config_files:
            print(
                f"\n📝 No subtask config files found in: {self.subtask_config_dir}"
            )
            print(
                "   Agent will run without pre-existing subtasks (will create new ones as needed).\n"
            )
            # Set empty config for backwards compatibility
            self.subtask_config = {}
            return

        print(f"Found {len(config_files)} subtask config file(s):")

        for config_file in config_files:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            log_file = config.get('log_file')
            if not log_file:
                print(f"  ⚠️  Skipping {config_file.name}: no 'log_file' field")
                continue

            subtasks = config.get('subtasks', [])
            print(
                f"  ✓ {config_file.name}: {len(subtasks)} subtask(s), log: {Path(log_file).name}"
            )

            self.subtask_configs.append((log_file, config))

        if not self.subtask_configs:
            raise ValueError("No valid subtask configs loaded")

        print(
            f"\nTotal: {len(self.subtask_configs)} config(s) loaded with {sum(len(cfg.get('subtasks', [])) for _, cfg in self.subtask_configs)} subtask(s)"
        )

        # For backwards compatibility, store first config as main config
        # This allows existing code to use self.subtask_config
        self.subtask_config = (
            self.subtask_configs[0][1] if self.subtask_configs else {}
        )

    async def initialize(self):
        """Initialize toolkit and agent."""
        print("=" * 80)
        print("INITIALIZING SUBTASK AGENT")
        print("=" * 80)

        # Create session log directory
        self.session_log_dir = (
            self.session_logs_root / f"session_{self.session_timestamp}"
        )
        self.session_log_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n📁 Session log directory: {self.session_log_dir}")
        print("   All logs for this session will be saved here\n")

        # Import ActionReplayer
        # sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'camel' / 'toolkits' / 'hybrid_browser_toolkit'))
        # Connect to browser - get browser endpoint, not page endpoint
        from urllib.request import urlopen

        from replay_from_log import ActionReplayer

        cdp_url = None
        try:
            # Use /json/version to get the browser-level WebSocket endpoint
            with urlopen(
                f'http://localhost:{self.cdp_port}/json/version', timeout=5
            ) as response:
                version_info = json.loads(response.read().decode('utf-8'))
                cdp_url = version_info.get('webSocketDebuggerUrl')
                print(
                    f"✓ Connected to browser: {version_info.get('Browser', 'N/A')}"
                )
                print(f"   CDP endpoint: {cdp_url}")
        except Exception as e:
            print(f"Error connecting to browser: {e}")
            return False

        if not cdp_url:
            print("Error: Could not get browser CDP endpoint")
            return False

        custom_tools = [
            "browser_open",
            "browser_visit_page",
            "browser_back",
            "browser_forward",
            "browser_click",
            "browser_type",
            "browser_switch_tab",
            "browser_enter",
            "browser_get_page_snapshot",
            # "browser_get_som_screenshot",
            # remove it to achieve faster operation
            # "browser_press_key",
            # "browser_console_view",
            # "browser_console_exec",
            # "browser_mouse_drag",
        ]
        # Initialize toolkit (single instance, shared by agent and replay)
        browser_log_dir = str(DEFAULT_BROWSER_LOG_DIR)
        self.toolkit = HybridBrowserToolkit(
            enabled_tools=custom_tools,
            headless=False,
            stealth=True,
            browser_log_to_file=True,
            log_dir=browser_log_dir,  # Set log directory to hardcoded path
            viewport_limit=False,
            cdp_url=cdp_url,
            default_start_url=None,
            # cdp_keep_current_page=True,  # Important: Keep existing page when connecting via CDP
        )

        # When connecting via CDP, browser is already open, no need to call browser_open()
        # await self.toolkit.browser_open()
        print("✓ Browser connected via CDP")

        # Create subtask functions from all configs
        print("\n" + "=" * 80)
        print("CREATING SUBTASK FUNCTIONS")
        print("=" * 80)

        # Iterate through all loaded configs
        for log_file, config in self.subtask_configs:
            config_name = config.get('metadata', {}).get(
                'subtask_type', 'unknown'
            )
            print(f"\n📦 Processing config: {Path(log_file).name}")
            print(f"   Type: {config_name}")

            # Save config to temp file for ActionReplayer
            # (ActionReplayer expects a file path, not a dict)
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.json', delete=False, encoding='utf-8'
            ) as temp_config:
                json.dump(config, temp_config, indent=2, ensure_ascii=False)
                temp_config_path = temp_config.name

            for subtask in config.get('subtasks', []):
                subtask_id = subtask['id']
                name = subtask['name']
                description = subtask['description']
                variables = subtask.get('variables', {})

                # Skip if subtask already exists (first config wins)
                if subtask_id in self.subtask_functions:
                    print(f"  ⚠️  Skipping duplicate subtask: {subtask_id}")
                    continue

                # Create replayer instance for this subtask
                replayer = ActionReplayer(
                    log_file=log_file,
                    cdp_port=self.cdp_port,
                    subtask_config=temp_config_path,
                    subtask_id=subtask_id,
                    use_agent_recovery=self.use_agent_recovery,
                )
                # Share the same toolkit to avoid WebSocket conflicts
                replayer.toolkit = self.toolkit

                # Check if subtask has embedded actions
                subtask_has_actions = bool(subtask.get('actions', []))

                if subtask_has_actions:
                    # Initialize with empty list - will be populated by load_subtask_config()
                    replayer.actions = []
                    print(
                        f"  [Info] Subtask {subtask_id} has embedded actions, skipping log file load"
                    )
                else:
                    # Load from log file for backward compatibility
                    replayer.actions = replayer.load_log_file()
                    print(
                        f"  [Info] Subtask {subtask_id} loading actions from log file"
                    )

                # Create subtask function with stats tracker and session log dir
                subtask_func = SubtaskFunction(
                    subtask_id=subtask_id,
                    name=name,
                    description=description,
                    variables=variables,
                    replayer=replayer,
                    stats_tracker=self.stats,
                    session_log_dir=self.session_log_dir,
                )

                self.subtask_functions[subtask_id] = subtask_func

                if variables:
                    print(f"  ✓ Created function: {subtask_id}")
                    print(f"     Variables: {list(variables.keys())}")
                else:
                    print(f"  ✓ Created function: {subtask_id}")
                    print("     No variables (fixed operation)")

        print(
            f"\n✅ Total subtask functions created: {len(self.subtask_functions)}"
        )

        # Create ChatAgent with both subtask functions and toolkit
        print("\n" + "=" * 80)
        print("CREATING CHAT AGENT")
        print("=" * 80)

        # Create model with parallel_tool_calls disabled
        from camel.models import ModelFactory
        from camel.types import ModelPlatformType, ModelType

        model = ModelFactory.create(
            model_platform=ModelPlatformType.AZURE,
            model_type=ModelType.GPT_4_1,
            model_config_dict={
                "temperature": 0.0,
                "parallel_tool_calls": False,
            },
        )

        print("✓ Model created")

        # Get toolkit tools - use them directly without wrapping
        # FunctionTool objects already have proper signatures
        browser_tools = self.toolkit.get_tools()
        print(f"✓ Got {len(browser_tools)} browser tools")

        # Note: We'll log browser tool calls through a different mechanism
        # to avoid breaking the function signatures that ChatAgent expects

        # Create subtask tool wrappers
        print("Creating subtask tool wrappers...")
        subtask_tools = []

        for subtask_id, subtask_func in self.subtask_functions.items():
            # Create wrapper with proper signature that logs calls
            if subtask_func.variables:
                # Build parameter list for the function signature
                param_list = []
                param_docs = []
                for var_name, var_config in subtask_func.variables.items():
                    param_list.append(f"{var_name}: str")
                    param_docs.append(
                        f"    {var_name} (str): {var_config['description']}"
                    )

                # Build function signature and docstring
                params_str = ", ".join(param_list)
                params_doc = "\n".join(param_docs)

                # Create function code dynamically with logging
                func_code = f"""
async def subtask_{subtask_func.subtask_id}({params_str}):
    \"\"\"
    {subtask_func.description}

    Args:
{params_doc}

    Returns:
        str: JSON result containing status, message, and page snapshot
    \"\"\"
    import json

    # Log the call
    kwargs = {{{", ".join([f"'{var}': {var}" for var in subtask_func.variables.keys()])}}}

    call_log = {{
        'timestamp': get_timestamp_iso(),
        'type': 'subtask_call',
        'subtask_id': '{subtask_func.subtask_id}',
        'subtask_name': '{subtask_func.name}',
        'arguments': kwargs,
        'result': None
    }}

    result = await _sf.execute(**kwargs)
    call_log['result'] = result

    # Add to agent's communication log
    if hasattr(_agent, 'agent_communication_log'):
        _agent.agent_communication_log.append(call_log)

    return json.dumps(result, ensure_ascii=False)
"""
            else:
                # No parameters - fixed operation
                func_code = f"""
async def subtask_{subtask_func.subtask_id}():
    \"\"\"
    {subtask_func.description}. This is a fixed operation with no parameters.

    Returns:
        str: JSON result containing status, message, and page snapshot
    \"\"\"
    import json

    # Log the call
    call_log = {{
        'timestamp': get_timestamp_iso(),
        'type': 'subtask_call',
        'subtask_id': '{subtask_func.subtask_id}',
        'subtask_name': '{subtask_func.name}',
        'arguments': {{}},
        'result': None
    }}

    result = await _sf.execute()
    call_log['result'] = result

    # Add to agent's communication log
    if hasattr(_agent, 'agent_communication_log'):
        _agent.agent_communication_log.append(call_log)

    return json.dumps(result, ensure_ascii=False)
"""

            # Execute the code to create the function
            local_vars = {"_sf": subtask_func, "_agent": self}
            exec(func_code, local_vars)
            wrapper = local_vars[f"subtask_{subtask_func.subtask_id}"]

            subtask_tools.append(wrapper)
            print(f"  ✓ Created wrapper for {subtask_id}: {wrapper.__name__}")

        # Combine all tools
        all_tools = [*browser_tools, *subtask_tools]
        print(
            f"✓ Total tools: {len(all_tools)} ({len(browser_tools)} browser + {len(subtask_tools)} subtask)"
        )

        # Get system prompt before creating agent
        self.system_prompt = self.get_system_message()

        # Create agent with system message
        print("Creating ChatAgent...")
        system_message = BaseMessage.make_assistant_message(
            role_name="Browser Automation Agent", content=self.system_prompt
        )

        self.agent = ChatAgent(
            model=model, tools=all_tools, system_message=system_message
        )

        print("✓ Agent created successfully with system prompt")

        # Collect tool definitions (name + docstring)
        self.tool_definitions = []

        # Browser tools
        for tool in browser_tools:
            tool_info = {
                'type': 'browser_tool',
                'name': tool.func.__name__
                if hasattr(tool.func, '__name__')
                else str(tool),
                'docstring': tool.func.__doc__
                if hasattr(tool.func, '__doc__')
                else None,
            }
            self.tool_definitions.append(tool_info)

        # Subtask tools
        for tool in subtask_tools:
            tool_info = {
                'type': 'subtask_function',
                'name': tool.__name__,
                'docstring': tool.__doc__,
            }
            self.tool_definitions.append(tool_info)

        return True

    def get_system_message(self) -> str:
        """Get the system message for the agent."""
        # Check if there are any subtask functions available
        has_subtasks = bool(self.subtask_functions)

        # Build prompt parts dynamically
        prompt_parts = []

        if has_subtasks:
            # Generate subtask list
            subtask_list = "\n".join(
                [
                    f"- subtask_{sid}: {sf.description}"
                    + (
                        f" (variables: {list(sf.variables.keys())})"
                        if sf.variables
                        else " (no parameters)"
                    )
                    for sid, sf in self.subtask_functions.items()
                ]
            )
            print("subtask_list", subtask_list)

            # Agent with subtasks
            prompt_parts.extend(
                [
                    "You are a browser automation agent with access to both high-level subtask functions and low-level browser tools.",
                    "",
                    "AVAILABLE SUBTASK FUNCTIONS (PREFER THESE WHEN APPLICABLE):",
                    subtask_list,
                    "",
                    "GUIDELINES:",
                    "1. **Prefer subtask functions** when they match your goal - they are tested and reliable",
                    "2. **IMPORTANT: Only call subtasks that match the current page URL**",
                    "   - Each subtask has an 'Execution page' specified in its description",
                    "   - Before calling a subtask, verify you are on the correct page using browser_get_page_snapshot",
                    "   - Do not call subtasks designed for different pages (e.g., don't call a subtask for Google Flights when on Google Search)",
                    "3. Use low-level browser tools only when:",
                    "   - No suitable subtask function exists",
                    "   - You need fine-grained control",
                    "   - The subtask function failed and you need to recover",
                    "",
                    "4. After executing a subtask function, you will receive:",
                    "   - Status (success/error)",
                    "   - Message describing the result",
                    "   - Current page snapshot",
                    "   - Variables that were used",
                    "",
                    "5. If a subtask fails, you can either:",
                    "   - Retry with different variables",
                    "   - Use low-level browser tools to fix the issue",
                    "   - Ask for clarification",
                    "",
                    "TASK DESCRIPTION:",
                    self.subtask_config.get(
                        'task_description', 'Complete browser automation tasks'
                    ),
                    "Remember: Subtask functions are your first choice - they encapsulate complex multi-step operations!",
                    "If you find some subtask may not finished by reusing previous subtask, you need to do it by yourself!",
                    "",
                ]
            )
        else:
            # Agent without subtasks - simpler prompt
            prompt_parts.extend(
                [
                    "You are a browser automation agent with access to low-level browser tools.",
                    "",
                    "GUIDELINES:",
                    "1. Use the available browser tools to complete the task step by step",
                    "2. Always verify the current state of the page before taking actions",
                    "3. If an action fails, analyze the page state and adjust your approach",
                    "",
                    "TASK DESCRIPTION:",
                    self.subtask_config.get(
                        'task_description', 'Complete browser automation tasks'
                    ),
                    "",
                ]
            )

        # Common guidelines (apply to both cases)
        prompt_parts.extend(
            [
                """
- All tasks are to be performed on Google Flights
- When entering the date, make sure to click on the date input field first and then type the date in the textbox. Both the date and the departure/destination fields can be confirmed by pressing Enter (enter after input).
- When entering the origin and destination, you do not need to be overly specific; entering the city name is sufficient.
- The date entry process is as follows: first click on the date input field, then type the departure date and the return date into the date fields respectively. Press Enter to confirm the date input, press Enter again to exit the date selection field, and then press Enter once more to initiate the search.
- If you want to check the current state of the page, call browser_get_page_snapshot. If the Search button is visible in snapshot, this indicates that you have not yet entered the results page. In that case, ensure that all required information (departure, destination, and date) has been fully entered, and then click the Search button to initiate the search.

            """
            ]
        )

        return "\n".join(prompt_parts)

    async def run(self, user_task: str):
        """Run the agent with a user task.

        Args:
            user_task: The task for the agent to complete
        """
        # Store the current user task for logging
        self.current_user_task = user_task

        print("\n" + "=" * 80)
        print("AGENT EXECUTION")
        print("=" * 80)
        print(f"Task: {user_task}")
        print()

        print("\n" + "🤖 " + "=" * 78)
        print("AGENT STARTING TO PROCESS TASK")
        print("=" * 80)

        # Log the user task
        timestamp = get_timestamp_iso()

        communication_entry = {
            'timestamp': timestamp,
            'type': 'main_agent_call',
            'user_task': user_task,
            'response': None,
            'tool_calls': [],  # Will store all tool calls made by agent
            'tokens': {'prompt': 0, 'completion': 0, 'total': 0},
        }

        # Use astep like hybrid_browser_toolkit_example.py
        print("\nSending task to agent...")
        response = await self.agent.astep(user_task)

        # Log the response
        if response.msgs:
            for msg in response.msgs:
                communication_entry['response'] = msg.content

                # Extract tool calls from the message
                if hasattr(msg, 'info') and msg.info:
                    if 'tool_calls' in msg.info:
                        tool_calls_info = msg.info['tool_calls']
                        if isinstance(tool_calls_info, list):
                            for tool_call in tool_calls_info:
                                if isinstance(tool_call, dict):
                                    communication_entry['tool_calls'].append(
                                        tool_call
                                    )

        print("\n" + "=" * 80)
        print("AGENT EXECUTION COMPLETED")
        print("=" * 80)
        print("Response:")
        if response.msgs:
            print(response.msgs[0].content)
        else:
            print("<no response>")
        print()

        # Extract token usage from agent response
        if hasattr(response, 'info') and response.info:
            if 'usage' in response.info:
                token_usage = extract_token_usage(response.info['usage'])
                prompt_tokens = token_usage['prompt']
                completion_tokens = token_usage['completion']
                total_tokens = token_usage['total']

                if total_tokens > 0:
                    self.stats['token_details']['main_agent']['prompt'] += (
                        prompt_tokens
                    )
                    self.stats['token_details']['main_agent'][
                        'completion'
                    ] += completion_tokens
                    self.stats['token_details']['main_agent']['total'] += (
                        total_tokens
                    )
                    self.stats['total_tokens'] += total_tokens

                    # Update communication entry
                    communication_entry['tokens'] = {
                        'prompt': prompt_tokens,
                        'completion': completion_tokens,
                        'total': total_tokens,
                    }

                    print("\n📊 Tokens used in this agent call:")
                    print(f"   • Prompt: {prompt_tokens}")
                    print(f"   • Completion: {completion_tokens}")
                    print(f"   • Total: {total_tokens}")

        # Save communication entry
        self.agent_communication_log.append(communication_entry)

        # Note: Browser tool calls are extracted from the browser log file
        # in save_communication_log() method, not from response.info
        # This ensures we capture all browser actions with full details

        return response

    def _extract_agent_browser_calls(self):
        """Extract browser tool calls made directly by agent (not from subtask replay).

        Returns:
            List of browser action records from the log file that were initiated by the agent.
        """

        print("\n" + "=" * 80)
        print("🔍 EXTRACTING AGENT BROWSER CALLS FROM LOG FILE")
        print("=" * 80)

        # Find the browser log file
        browser_log_dir = DEFAULT_BROWSER_LOG_DIR

        if not browser_log_dir.exists():
            print("⚠️  Warning: Browser log directory not found")
            print(f"   Expected: {browser_log_dir}")
            return []

        print(f"✓ Browser log directory found: {browser_log_dir.absolute()}")

        # Get the most recent browser log file (contains ALL actions)
        all_log_files = sorted(
            [
                f
                for f in browser_log_dir.glob("hybrid_browser_toolkit*.log")
                if not f.name.startswith('typescript')
            ],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not all_log_files:
            print("⚠️  Warning: No browser log files found")
            return []

        browser_log_file = all_log_files[0]
        print(f"\n📂 Reading complete browser log from: {browser_log_file}")

        # Read all actions from browser log
        # The log file contains multiple JSON objects concatenated together
        # separated by newlines (format: }\n{)
        all_browser_actions = []
        try:
            with open(browser_log_file, 'r', encoding='utf-8') as f:
                content = f.read()

                # Split by }\n{ to separate JSON objects
                # Add back the braces that were removed by split
                json_strings = content.split('}\n{')

                for i, json_str in enumerate(json_strings):
                    if not json_str.strip():
                        continue

                    # Add back the braces
                    if i == 0:
                        # First object: already has opening {, needs closing }
                        json_str = json_str + '}'
                    elif i == len(json_strings) - 1:
                        # Last object: already has closing }, needs opening {
                        json_str = '{' + json_str
                    else:
                        # Middle objects: need both braces
                        json_str = '{' + json_str + '}'

                    try:
                        action = json.loads(json_str)
                        all_browser_actions.append(action)
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Failed to parse JSON object {i+1}: {e}")
                        # Show first 100 chars for debugging
                        print(f"   Content preview: {json_str[:100]}")
                        continue

        except Exception as e:
            print(f"⚠️  Error reading browser log: {e}")
            import traceback

            traceback.print_exc()
            return []

        print(
            f"   Found {len(all_browser_actions)} total browser actions in log"
        )

        # Load all subtask replay action logs from session directory
        replay_log_files = []
        if self.session_log_dir and self.session_log_dir.exists():
            replay_log_files = sorted(
                self.session_log_dir.glob("subtask_*_replay_actions.json")
            )
            print(
                f"\n📂 Reading replay logs from session directory: {self.session_log_dir}"
            )
        else:
            # Fallback to browser_log directory
            replay_log_files = sorted(
                browser_log_dir.glob("subtask_replay_actions_*.json")
            )
            print("\n📂 Reading replay logs from browser_log directory")

        print(f"   Found {len(replay_log_files)} subtask replay log files")

        all_replay_actions = []
        for replay_log_file in replay_log_files:
            try:
                with open(replay_log_file, 'r', encoding='utf-8') as f:
                    replay_data = json.load(f)
                    actions = replay_data.get('actions', [])
                    all_replay_actions.extend(actions)
                    print(
                        f"   • {replay_log_file.name}: {len(actions)} actions"
                    )
            except Exception as e:
                print(f"   ⚠️  Error reading {replay_log_file.name}: {e}")

        print(f"\n   Total replay actions: {len(all_replay_actions)}")

        # Filter out replay actions from browser log
        # Strategy: Create a set of (timestamp, action) pairs from replay logs
        # and exclude browser actions that match
        replay_signatures = set()
        for replay_action in all_replay_actions:
            timestamp = replay_action.get('timestamp', '')
            action_name = replay_action.get('action', '')
            if timestamp and action_name:
                # Use timestamp (to second precision) + action name as signature
                # This is a simple heuristic; actions within the same second with same name are considered duplicates
                ts_seconds = timestamp[:19]  # Keep only YYYY-MM-DDTHH:MM:SS
                replay_signatures.add((ts_seconds, action_name))

        print(
            f"   Created {len(replay_signatures)} replay action signatures for filtering"
        )

        # Filter browser actions
        agent_initiated_actions = []

        for action in all_browser_actions:
            action_timestamp = action.get('timestamp', '')
            action_name = action.get('action', '')

            if not action_timestamp:
                continue

            # Check if this action matches a replay action
            ts_seconds = action_timestamp[:19]
            action_signature = (ts_seconds, action_name)

            if action_signature in replay_signatures:
                # This is a replay action, skip it
                continue

            # This is an agent-initiated action
            agent_initiated_actions.append(
                {
                    'timestamp': action_timestamp,
                    'type': 'browser_tool_call',
                    'tool_name': f"browser_{action_name}",
                    'arguments': action.get('inputs', {}),
                    'result': action.get('outputs', {}),
                    'execution_time_ms': action.get('execution_time_ms', 0),
                }
            )

        print(f"\n   Agent-initiated actions: {len(agent_initiated_actions)}")
        print(
            f"   Replay actions (filtered out): {len(all_browser_actions) - len(agent_initiated_actions)}"
        )

        # Update statistics
        self.stats['browser_tool_calls'] = len(agent_initiated_actions)
        for action in agent_initiated_actions:
            tool_name = action['tool_name']
            if tool_name not in self.stats['browser_tool_details']:
                self.stats['browser_tool_details'][tool_name] = 0
            self.stats['browser_tool_details'][tool_name] += 1

        return agent_initiated_actions

    def print_statistics(self):
        """Print comprehensive statistics about the task execution."""
        print("\n" + "=" * 80)
        print("📊 TASK EXECUTION STATISTICS")
        print("=" * 80)

        print(f"\n🎯 Subtask Calls: {self.stats['subtask_calls']}")
        if self.stats['subtask_details']:
            for subtask_id, details in self.stats['subtask_details'].items():
                print(
                    f"   • {details['name']} ({subtask_id}): {details['calls']} call(s)"
                )
                for i, vars_used in enumerate(details['variables_used'], 1):
                    if vars_used:
                        print(f"      Call {i}: {vars_used}")
                    else:
                        print(f"      Call {i}: (no variables)")

        print(f"\n🔧 Browser Tool Calls: {self.stats['browser_tool_calls']}")
        if self.stats['browser_tool_details']:
            for tool_name, count in self.stats['browser_tool_details'].items():
                print(f"   • {tool_name}: {count} call(s)")
        elif self.stats['browser_tool_calls'] == 0:
            print(
                "   Note: Browser tool calls made by the agent are not tracked separately."
            )
            print(
                "   Tool calls within subtasks are included in subtask execution."
            )

        print(
            f"\n🤖 Agent Recovery Calls: {self.stats['agent_recovery_calls']}"
        )

        print(f"\n💰 Total Tokens Used: {self.stats['total_tokens']}")
        print("   Main Agent:")
        print(
            f"      • Prompt: {self.stats['token_details']['main_agent']['prompt']} tokens"
        )
        print(
            f"      • Completion: {self.stats['token_details']['main_agent']['completion']} tokens"
        )
        print(
            f"      • Total: {self.stats['token_details']['main_agent']['total']} tokens"
        )
        print("   Recovery Agent:")
        print(
            f"      • Prompt: {self.stats['token_details']['recovery_agent']['prompt']} tokens"
        )
        print(
            f"      • Completion: {self.stats['token_details']['recovery_agent']['completion']} tokens"
        )
        print(
            f"      • Total: {self.stats['token_details']['recovery_agent']['total']} tokens"
        )

        print("\n" + "=" * 80)

    def save_communication_log(self):
        """Save all agent communications to a JSON file."""
        # Extract browser tool calls from browser log file
        browser_tool_calls_from_log = self._extract_agent_browser_calls()

        # Collect all recovery agent communications from replayers
        recovery_communications = []
        for subtask_id, subtask_func in self.subtask_functions.items():
            if hasattr(subtask_func.replayer, 'recovery_history'):
                for record in subtask_func.replayer.recovery_history:
                    recovery_communications.append(
                        {
                            'type': 'recovery_agent_call',
                            'subtask_id': subtask_id,
                            **record,
                        }
                    )

        # Merge browser tool calls from log into agent communication log
        all_communications_list = (
            self.agent_communication_log + browser_tool_calls_from_log
        )

        # Sort all communications by timestamp
        sorted_communications = sorted(
            all_communications_list, key=lambda x: x.get('timestamp', '')
        )

        # Combine all communications
        # Use current user task if available, otherwise fall back to config task
        task_desc = self.current_user_task or self.subtask_config.get(
            'task_description', ''
        )

        all_communications = {
            'session_start': get_timestamp_iso(),
            'task_description': task_desc,
            'system_prompt': self.system_prompt,  # Add system prompt
            'tool_definitions': self.tool_definitions,  # Add tool definitions
            'communications': sorted_communications,  # All communications in chronological order
            'recovery_agent_communications': recovery_communications,
            'statistics': self.stats,
            'summary': {
                'total_communications': len(sorted_communications),
                'subtask_calls': len(
                    [
                        c
                        for c in sorted_communications
                        if c.get('type') == 'subtask_call'
                    ]
                ),
                'browser_tool_calls': len(
                    [
                        c
                        for c in sorted_communications
                        if c.get('type') == 'browser_tool_call'
                    ]
                ),
                'main_agent_calls': len(
                    [
                        c
                        for c in sorted_communications
                        if c.get('type') == 'main_agent_call'
                    ]
                ),
                'recovery_calls': len(recovery_communications),
                'total_tools': len(self.tool_definitions),
            },
        }

        # Save to session directory if available
        if self.session_log_dir:
            log_path = self.session_log_dir / "agent_communication_log.json"
        else:
            log_filename = (
                f"agent_communication_log_{get_timestamp_filename()}.json"
            )
            log_path = Path("camel_logs") / log_filename
            log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(all_communications, f, indent=2, ensure_ascii=False)

        print(f"\n📝 Agent communication log saved to: {log_path}")
        print(
            f"   Total communications logged: {all_communications['summary']['total_communications']}"
        )
        print(
            f"   - Main agent calls: {all_communications['summary']['main_agent_calls']}"
        )
        print(
            f"   - Subtask calls: {all_communications['summary']['subtask_calls']}"
        )
        print(
            f"   - Browser tool calls: {all_communications['summary']['browser_tool_calls']}"
        )
        print(
            f"   - Recovery calls: {all_communications['summary']['recovery_calls']}"
        )

        # Copy browser log to session directory
        if self.session_log_dir:
            browser_log_dir = DEFAULT_BROWSER_LOG_DIR

            if browser_log_dir.exists():
                # Get the most recent browser log
                all_log_files = sorted(
                    [
                        f
                        for f in browser_log_dir.glob(
                            "hybrid_browser_toolkit*.log"
                        )
                        if not f.name.startswith('typescript')
                    ],
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if all_log_files:
                    import shutil

                    browser_log_file = all_log_files[0]
                    dest_file = (
                        self.session_log_dir / "complete_browser_log.log"
                    )
                    shutil.copy2(browser_log_file, dest_file)
                    print(f"\n📋 Complete browser log copied to: {dest_file}")
                    print(f"   Source: {browser_log_file}")

        # Auto-generate timeline analysis
        self._generate_timeline_analysis()

    def _generate_timeline_analysis(self):
        """Auto-generate timeline analysis from session logs."""
        if not self.session_log_dir or not self.session_log_dir.exists():
            print(
                "\n⚠️  Session directory not found, skipping timeline analysis"
            )
            return

        print("\n" + "=" * 80)
        print("📊 GENERATING TIMELINE ANALYSIS")
        print("=" * 80)

        # Import the analyze_session module
        import sys
        from pathlib import Path

        # Add the toolkits directory to path if needed
        toolkits_dir = Path(__file__).parent
        if str(toolkits_dir) not in sys.path:
            sys.path.insert(0, str(toolkits_dir))

        try:
            # Import the analyze_session module
            from analyze_session import analyze_session

            print(f"\n🔍 Analyzing session: {self.session_log_dir}")

            # Run the analysis
            analyze_session(str(self.session_log_dir))

            print("\n✅ Timeline analysis completed successfully!")

        except ImportError as e:
            print(f"\n⚠️  Could not import analyze_session module: {e}")
            print(
                "   Make sure analyze_session.py is in the same directory as this script"
            )
        except Exception as e:
            print(f"\n⚠️  Error during timeline analysis: {e}")
            import traceback

            traceback.print_exc()


async def main():
    """Main entry point."""
    # Configuration - now using directory instead of individual files
    subtask_config_dir = str(DEFAULT_SUBTASK_CONFIGS_DIR)

    # Create agent
    agent = SubtaskAgent(
        subtask_config_dir=subtask_config_dir,
        use_agent_recovery=True,
    )

    try:
        # Initialize
        success = await agent.initialize()
        if not success:
            print("Failed to initialize agent")
            return

        # Example task
        task = """
        Show me the list of one-way flights on January 17, 2026 from Chicago to Paris.
        """

        await agent.run(task)

        # Print statistics
        agent.print_statistics()

        # Save agent communication log
        agent.save_communication_log()

    finally:
        # Cleanup (similar to hybrid_browser_toolkit_example.py)
        if agent.toolkit:
            print("\n" + "=" * 80)
            print("CLEANUP")
            print("=" * 80)
            print("Closing browser...")
            # Note: browser is already managed by CDP, no need to close
            print("✓ Cleanup completed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
