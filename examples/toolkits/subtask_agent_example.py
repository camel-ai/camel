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
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

load_dotenv()

# Add project root to path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits.hybrid_browser_toolkit import HybridBrowserToolkit
from camel.types import ModelPlatformType, ModelType


class SubtaskFunction:
    """Wrapper for a subtask that can be called as a function."""

    def __init__(
        self,
        subtask_id: str,
        name: str,
        description: str,
        variables: Dict[str, Any],
        replayer: Any,
        stats_tracker: Optional[Dict[str, Any]] = None
    ):
        """Initialize subtask function.

        Args:
            subtask_id: Subtask ID
            name: Subtask name
            description: Subtask description
            variables: Variable definitions
            replayer: ActionReplayer instance
            stats_tracker: Reference to agent's stats dict for tracking
        """
        self.subtask_id = subtask_id
        self.name = name
        self.description = description
        self.variables = variables
        self.replayer = replayer
        self.last_result = None
        self.stats_tracker = stats_tracker

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
                    'variables_used': []
                }
            self.stats_tracker['subtask_details'][self.subtask_id]['calls'] += 1
            self.stats_tracker['subtask_details'][self.subtask_id]['variables_used'].append(kwargs)

        print(f"\n{'🎯 ' + '='*78}")
        print(f"EXECUTING SUBTASK: {self.name}")
        print(f"{'='*80}")
        print(f"📋 Subtask ID: {self.subtask_id}")
        print(f"📝 Description: {self.description}")

        if kwargs:
            print(f"🔧 Input Variables:")
            for key, value in kwargs.items():
                print(f"   • {key} = {value}")
        else:
            print(f"🔧 No input variables (fixed operation)")
        print()

        # Set variables in replayer
        self.replayer.subtask_id = self.subtask_id
        self.replayer.variable_overrides = kwargs
        self.replayer.load_subtask_config()

        # Debug: Check if agent recovery is enabled
        print(f"🔍 Debug: use_agent_recovery = {self.replayer.use_agent_recovery}")
        print(f"🔍 Debug: recovery_agent = {self.replayer.recovery_agent}")

        # Track recovery calls before execution
        recovery_calls_before = len(getattr(self.replayer, 'recovery_history', []))

        # Execute replay
        try:
            print(f"▶️  Starting subtask execution...")
            print(f"{'─' * 80}\n")

            # Execute the subtask
            execution_result = await self.replayer.replay_subtask()

            # Track recovery calls after execution
            recovery_calls_after = len(getattr(self.replayer, 'recovery_history', []))
            recovery_calls_made = recovery_calls_after - recovery_calls_before
            if self.stats_tracker is not None and recovery_calls_made > 0:
                self.stats_tracker['agent_recovery_calls'] += recovery_calls_made

                # Sum up tokens from new recovery calls
                recovery_history = getattr(self.replayer, 'recovery_history', [])
                for i in range(recovery_calls_before, recovery_calls_after):
                    if i < len(recovery_history):
                        tokens = recovery_history[i].get('tokens_used', 0)
                        self.stats_tracker['token_details']['recovery_agent'] += tokens
                        self.stats_tracker['total_tokens'] += tokens

            print(f"\n{'─' * 80}")
            print(f"✅ Subtask Execution Result:")
            print(f"   Status: {execution_result['status']}")
            print(f"   Successful actions: {len(execution_result['successful_actions'])}")
            print(f"   Failed actions: {len(execution_result['failed_actions'])}")
            print(f"   Skipped actions: {len(execution_result['skipped_actions'])}")

            # Get final snapshot
            print(f"\n📸 Getting final page snapshot...")
            final_snapshot = await self.replayer.toolkit.browser_get_page_snapshot()
            snapshot_preview = final_snapshot[:200] + "..." if len(final_snapshot) > 200 else final_snapshot
            print(f"   Snapshot length: {len(final_snapshot)} chars")
            print(f"   Preview: {snapshot_preview}")

            result = {
                'status': 'success' if execution_result['all_successful'] else 'partial_success',
                'message': f"Subtask '{self.name}' completed. {len(execution_result['successful_actions'])} successful, {len(execution_result['failed_actions'])} failed",
                'snapshot': final_snapshot,
                'variables_used': kwargs,
                'execution_details': execution_result
            }

            print(f"\n✅ SUBTASK COMPLETED SUCCESSFULLY")
            print(f"{'='*80}\n")

            self.last_result = result
            return result

        except Exception as e:
            print(f"\n❌ SUBTASK EXECUTION FAILED")
            print(f"   Error: {str(e)}")
            print(f"{'='*80}\n")

            import traceback
            traceback.print_exc()

            result = {
                'status': 'error',
                'message': f"Subtask '{self.name}' failed: {str(e)}",
                'snapshot': '',
                'variables_used': kwargs,
                'error': str(e)
            }
            self.last_result = result
            return result

    def get_function_schema(self) -> Dict[str, Any]:
        """Get the function schema for this subtask.

        Returns:
            OpenAI function schema
        """
        # Build parameters from variables
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }

        if self.variables:
            for var_name, var_config in self.variables.items():
                parameters["properties"][var_name] = {
                    "type": "string" if var_config['type'] in ['string', 'date'] else "string",
                    "description": var_config['description']
                }
                parameters["required"].append(var_name)

            description = f"{self.description}. Variables: {', '.join(self.variables.keys())}"
        else:
            # No variables - fixed operation
            description = f"{self.description}. This is a fixed operation with no parameters."

        return {
            "name": f"subtask_{self.subtask_id}",
            "description": description,
            "parameters": parameters
        }


class SubtaskAgent:
    """Agent that can execute subtasks as functions."""

    def __init__(
        self,
        log_file: str,
        subtask_config_file: str,
        cdp_port: int = 9223,
        use_agent_recovery: bool = True
    ):
        """Initialize the SubtaskAgent.

        Args:
            log_file: Path to the browser action log file
            subtask_config_file: Path to subtask configuration JSON
            cdp_port: CDP port number
            use_agent_recovery: Use agent recovery for errors
        """
        self.log_file = log_file
        self.subtask_config_file = subtask_config_file
        self.cdp_port = cdp_port
        self.use_agent_recovery = use_agent_recovery

        # Load subtask configuration
        with open(subtask_config_file, 'r') as f:
            self.subtask_config = json.load(f)

        # Initialize components
        self.toolkit: Optional[HybridBrowserToolkit] = None
        self.agent: Optional[ChatAgent] = None
        self.subtask_functions: Dict[str, SubtaskFunction] = {}

        # Statistics tracking
        self.stats = {
            'total_tokens': 0,
            'subtask_calls': 0,
            'browser_tool_calls': 0,
            'agent_recovery_calls': 0,
            'token_details': {
                'main_agent': 0,
                'recovery_agent': 0
            },
            'subtask_details': {},  # Track each subtask call
            'browser_tool_details': {}  # Track each browser tool call
        }

    async def initialize(self):
        """Initialize toolkit and agent."""
        print("=" * 80)
        print("INITIALIZING SUBTASK AGENT")
        print("=" * 80)

        # Import ActionReplayer
        # sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'camel' / 'toolkits' / 'hybrid_browser_toolkit'))
        from replay_from_log import ActionReplayer

        # Connect to browser - get browser endpoint, not page endpoint
        from urllib.request import urlopen
        cdp_url = None
        try:
            # Use /json/version to get the browser-level WebSocket endpoint
            with urlopen(f'http://localhost:{self.cdp_port}/json/version', timeout=5) as response:
                version_info = json.loads(response.read().decode('utf-8'))
                cdp_url = version_info.get('webSocketDebuggerUrl')
                print(f"✓ Connected to browser: {version_info.get('Browser', 'N/A')}")
                print(f"   CDP endpoint: {cdp_url}")
        except Exception as e:
            print(f"Error connecting to browser: {e}")
            return False

        if not cdp_url:
            print("Error: Could not get browser CDP endpoint")
            return False

        # Initialize toolkit
        self.toolkit = HybridBrowserToolkit(
            mode="typescript",
            headless=False,
            stealth=True,
            browser_log_to_file=False,
            viewport_limit=False,
            cdp_url=cdp_url,
            default_start_url=None,
            cdp_keep_current_page=True,  # Important: Keep existing page when connecting via CDP
        )

        # When connecting via CDP, browser is already open, no need to call browser_open()
        # await self.toolkit.browser_open()
        print("✓ Browser connected via CDP")

        # Create subtask functions
        print("\n" + "=" * 80)
        print("CREATING SUBTASK FUNCTIONS")
        print("=" * 80)

        for subtask in self.subtask_config.get('subtasks', []):
            subtask_id = subtask['id']
            name = subtask['name']
            description = subtask['description']
            variables = subtask.get('variables', {})

            # Create replayer instance for this subtask
            replayer = ActionReplayer(
                log_file=self.log_file,
                cdp_port=self.cdp_port,
                subtask_config=self.subtask_config_file,
                subtask_id=subtask_id,
                use_agent_recovery=self.use_agent_recovery
            )
            replayer.toolkit = self.toolkit
            replayer.actions = replayer.load_log_file()

            # Create subtask function with stats tracker
            subtask_func = SubtaskFunction(
                subtask_id=subtask_id,
                name=name,
                description=description,
                variables=variables,
                replayer=replayer,
                stats_tracker=self.stats
            )

            self.subtask_functions[subtask_id] = subtask_func

            if variables:
                print(f"✓ Created function: {subtask_id}")
                print(f"  Variables: {list(variables.keys())}")
            else:
                print(f"✓ Created function: {subtask_id}")
                print(f"  No variables (fixed operation)")

        # Create ChatAgent with both subtask functions and toolkit
        print("\n" + "=" * 80)
        print("CREATING CHAT AGENT")
        print("=" * 80)

        model = ModelFactory.create(
            model_platform=ModelPlatformType.AZURE,
            model_type=ModelType.GPT_4_1,
            model_config_dict={"temperature": 0.0}
        )

        print("✓ Model created")

        # Get toolkit tools (similar to hybrid_browser_toolkit_example.py)
        browser_tools = self.toolkit.get_tools()
        print(f"✓ Got {len(browser_tools)} browser tools")

        # Create subtask tool wrappers
        print("Creating subtask tool wrappers...")
        subtask_tools = []

        for subtask_id, subtask_func in self.subtask_functions.items():
            # Create wrapper with proper signature
            if subtask_func.variables:
                # Build parameter list for the function signature
                param_list = []
                param_docs = []
                for var_name, var_config in subtask_func.variables.items():
                    param_list.append(f"{var_name}: str")
                    param_docs.append(f"    {var_name} (str): {var_config['description']}")

                # Build function signature and docstring
                params_str = ", ".join(param_list)
                params_doc = "\n".join(param_docs)

                # Create function code dynamically
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
    kwargs = {{{", ".join([f"'{var}': {var}" for var in subtask_func.variables.keys()])}}}
    result = await _sf.execute(**kwargs)
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
    result = await _sf.execute()
    return json.dumps(result, ensure_ascii=False)
"""

            # Execute the code to create the function
            local_vars = {"_sf": subtask_func}
            exec(func_code, local_vars)
            wrapper = local_vars[f"subtask_{subtask_func.subtask_id}"]

            subtask_tools.append(wrapper)
            print(f"  ✓ Created wrapper for {subtask_id}: {wrapper.__name__}")

        # Combine all tools
        all_tools = [*browser_tools, *subtask_tools]
        print(f"✓ Total tools: {len(all_tools)} ({len(browser_tools)} browser + {len(subtask_tools)} subtask)")

        # Create agent (similar to hybrid_browser_toolkit_example.py)
        print("Creating ChatAgent...")
        self.agent = ChatAgent(
            model=model,
            tools=all_tools
        )

        print(f"✓ Agent created successfully")

        return True

    def get_system_message(self) -> str:
        """Get the system message for the agent."""
        subtask_list = "\n".join([
            f"- subtask_{sid}: {sf.description}" + (
                f" (variables: {list(sf.variables.keys())})" if sf.variables else " (no parameters)"
            )
            for sid, sf in self.subtask_functions.items()
        ])
        print("subtask_list", subtask_list)

        return f"""You are a browser automation agent with access to both high-level subtask functions and low-level browser tools.

AVAILABLE SUBTASK FUNCTIONS (PREFER THESE WHEN APPLICABLE):
{subtask_list}

GUIDELINES:
1. **Prefer subtask functions** when they match your goal - they are tested and reliable
2. Use low-level browser tools only when:
   - No suitable subtask function exists
   - You need fine-grained control
   - The subtask function failed and you need to recover

3. After executing a subtask function, you will receive:
   - Status (success/error)
   - Message describing the result
   - Current page snapshot
   - Variables that were used

4. If a subtask fails, you can either:
   - Retry with different variables
   - Use low-level browser tools to fix the issue
   - Ask for clarification

TASK DESCRIPTION:
{self.subtask_config.get('task_description', 'Complete browser automation tasks')}

Remember: Subtask functions are your first choice - they encapsulate complex multi-step operations!
"""

    async def run(self, user_task: str):
        """Run the agent with a user task.

        Args:
            user_task: The task for the agent to complete
        """
        print("\n" + "=" * 80)
        print("AGENT EXECUTION")
        print("=" * 80)
        print(f"Task: {user_task}")
        print()

        print("\n" + "🤖 " + "=" * 78)
        print("AGENT STARTING TO PROCESS TASK")
        print("=" * 80)

        # Use astep like hybrid_browser_toolkit_example.py
        print("\nSending task to agent...")
        response = await self.agent.astep(user_task)

        print("\n" + "=" * 80)
        print("AGENT EXECUTION COMPLETED")
        print("=" * 80)
        print(f"Response:")
        if response.msgs:
            print(response.msgs[0].content)
        else:
            print("<no response>")
        print()

        # Extract token usage from agent response
        if hasattr(response, 'info') and response.info:
            if 'usage' in response.info:
                usage = response.info['usage']
                if hasattr(usage, 'prompt_tokens') and hasattr(usage, 'completion_tokens'):
                    total_tokens = usage.prompt_tokens + usage.completion_tokens
                    self.stats['token_details']['main_agent'] += total_tokens
                    self.stats['total_tokens'] += total_tokens
                    print(f"\n📊 Tokens used in this agent call: {total_tokens}")
                elif isinstance(usage, dict):
                    total_tokens = usage.get('prompt_tokens', 0) + usage.get('completion_tokens', 0)
                    self.stats['token_details']['main_agent'] += total_tokens
                    self.stats['total_tokens'] += total_tokens
                    print(f"\n📊 Tokens used in this agent call: {total_tokens}")

        # Count tool calls from the response
        # Browser tool calls are tracked through function calls in the response
        # We can look at the response info for tool_calls if available
        if hasattr(response, 'info') and response.info and 'tool_calls' in response.info:
            tool_calls = response.info['tool_calls']
            if isinstance(tool_calls, list):
                for tool_call in tool_calls:
                    if isinstance(tool_call, dict) and 'function' in tool_call:
                        func_name = tool_call['function'].get('name', 'unknown')
                        # Only count browser tools, not subtask functions
                        if func_name.startswith('browser_'):
                            self.stats['browser_tool_calls'] += 1
                            if func_name not in self.stats['browser_tool_details']:
                                self.stats['browser_tool_details'][func_name] = 0
                            self.stats['browser_tool_details'][func_name] += 1

        return response

    def print_statistics(self):
        """Print comprehensive statistics about the task execution."""
        print("\n" + "=" * 80)
        print("📊 TASK EXECUTION STATISTICS")
        print("=" * 80)

        print(f"\n🎯 Subtask Calls: {self.stats['subtask_calls']}")
        if self.stats['subtask_details']:
            for subtask_id, details in self.stats['subtask_details'].items():
                print(f"   • {details['name']} ({subtask_id}): {details['calls']} call(s)")
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
            print("   Note: Browser tool calls made by the agent are not tracked separately.")
            print("   Tool calls within subtasks are included in subtask execution.")

        print(f"\n🤖 Agent Recovery Calls: {self.stats['agent_recovery_calls']}")

        print(f"\n💰 Total Tokens Used: {self.stats['total_tokens']}")
        print(f"   • Main Agent: {self.stats['token_details']['main_agent']} tokens")
        print(f"   • Recovery Agent: {self.stats['token_details']['recovery_agent']} tokens")

        print("\n" + "=" * 80)


async def main():
    """Main entry point."""
    # Configuration
    log_file = "/Users/puzhen/Desktop/pre/camel_project/camel/examples/toolkits/browser_log/hybrid_browser_toolkit_ws_20251228_010752_None.log"
    subtask_config_file = "/Users/puzhen/Desktop/pre/camel_project/camel/examples/toolkits/browser_log/hybrid_browser_toolkit_ws_20251228_010752_None_subtasks.json"

    # Create agent
    agent = SubtaskAgent(
        log_file=log_file,
        subtask_config_file=subtask_config_file,
        use_agent_recovery=True
    )

    try:
        # Initialize
        success = await agent.initialize()
        if not success:
            print("Failed to initialize agent")
            return

        # Example task
        task = """
        Please book a flight from Munich to Paris on January 15, 2026, returning on January 20, 2026.
        Use the subtask functions when possible to fill in the locations and dates.
        
        Tell me the most cheap flight option after you searched result
        """

        await agent.run(task)

        # Print statistics
        agent.print_statistics()

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
