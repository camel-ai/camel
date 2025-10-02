# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
import asyncio
import logging
from typing import Any, Dict, List

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.prompts import TextPrompt
from camel.tasks import Task
from camel.toolkits import HybridBrowserToolkit, TaskPlanningToolkit
from camel.types import ModelPlatformType, ModelType

# Import snapshot truncation utilities
try:
    from snapshot_truncator import add_snapshot_truncation
except ImportError:
    # Fallback if file is not in the same directory
    import sys
    sys.path.append('.')
    from snapshot_truncator import add_snapshot_truncation

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ],
)

logging.getLogger('camel.agents').setLevel(logging.INFO)
logging.getLogger('camel.models').setLevel(logging.INFO)
logging.getLogger('camel.models').setLevel(logging.INFO)
logging.getLogger('camel.toolkits.hybrid_browser_toolkit').setLevel(
    logging.DEBUG
)
USER_DATA_DIR = "User_Data"

model_backend = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
    model_config_dict={"temperature": 0.0, "top_p": 1},
)

# Example 1: Use default tools (basic functionality)
# web_toolkit_default = HybridBrowserToolkit(
#     headless=False,
#     user_data_dir=USER_DATA_DIR
# )
# print(f"Default tools: {web_toolkit_default.enabled_tools}")

# Example 2: Use all available tools
# web_toolkit_all = HybridBrowserToolkit(
#     headless=False,
#     user_data_dir=USER_DATA_DIR,
#     enabled_tools=HybridBrowserToolkit.ALL_TOOLS
# )
# print(f"All tools: {web_toolkit_all.enabled_tools}")

# Example 3: Use custom tools selection
custom_tools = [
    "browser_open",
    "browser_close",
    "browser_visit_page",
    "browser_back",
    "browser_forward",
    "browser_click",
    "browser_type",
    "browser_switch_tab",
    "browser_enter",
    # "browser_get_som_screenshot", # remove it to achieve faster operation
    # "browser_press_key",
    # "browser_console_view",
    # "browser_console_exec",
    # "browser_mouse_drag",
]

web_toolkit_custom = HybridBrowserToolkit(
    headless=False,
    user_data_dir=USER_DATA_DIR,
    enabled_tools=custom_tools,
    browser_log_to_file=True,  # generate detailed log file in ./browser_log
    stealth=True,  # Using stealth mode during browser operation
    viewport_limit=True,
    # Limit snapshot to current viewport to reduce context
)
print(f"Custom tools: {web_toolkit_custom.enabled_tools}")

# Initialize TaskPlanningToolkit
task_planning_toolkit = TaskPlanningToolkit()

# Create a wrapper class to intercept tool calls
class ToolCallLogger:
    def __init__(self):
        self.call_count = 0
        self.all_tool_calls = []
    
    def create_logged_tool(self, tool):
        """Wrap a tool to log its calls in real-time"""
        original_func = tool.func
        
        async def logged_func(*args, **kwargs):
            self.call_count += 1
            tool_name = tool.get_function_name()
            print(f"\n🔧 [{self.call_count}] Calling tool: {tool_name}")
            
            # Pretty print args and kwargs
            if args:
                print(f"   Args: {args}")
            
            # Special formatting for task planning tools
            if tool_name in ['decompose_task', 'replan_tasks']:
                print(f"   Original task: {kwargs.get('original_task_content', 'N/A')}")
                print(f"   Task ID: {kwargs.get('original_task_id', 'Auto-generated')}")
                if 'sub_task_contents' in kwargs:
                    print("   Sub-tasks to create:")
                    for i, content in enumerate(kwargs['sub_task_contents'], 1):
                        print(f"      {i}. {content}")
            else:
                # For other tools, show kwargs normally but format better
                for key, value in kwargs.items():
                    if isinstance(value, str) and len(value) > 100:
                        print(f"   {key}: {value[:100]}...")
                    else:
                        print(f"   {key}: {value}")
            
            # Execute the original function
            result = await original_func(*args, **kwargs) if asyncio.iscoroutinefunction(original_func) else original_func(*args, **kwargs)
            
            # Log the result with special formatting
            if tool_name in ['decompose_task', 'replan_tasks'] and isinstance(result, list):
                print("   Result - Created tasks:")
                for task in result:
                    print(f"      ✓ [{task.id}] {task.content}")
                    if hasattr(task, 'state') and task.state != 'OPEN':
                        print(f"        Status: {task.state}")
            else:
                result_str = str(result)
                if len(result_str) > 200:
                    print(f"   Result: {result_str[:200]}...")
                else:
                    print(f"   Result: {result_str}")
            
            # Store for summary
            self.all_tool_calls.append({
                'name': tool_name,
                'args': args,
                'kwargs': kwargs,
                'result': result
            })
            
            return result
        
        # Create a new tool with the logged function
        tool.func = logged_func
        return tool

# Create logger instance
tool_logger = ToolCallLogger()

# Wrap all tools with logging
logged_browser_tools = [tool_logger.create_logged_tool(tool) for tool in web_toolkit_custom.get_tools()]
logged_planning_tools = [tool_logger.create_logged_tool(tool) for tool in task_planning_toolkit.get_tools()]

# Create system prompt with task planning instructions
sys_prompt = TextPrompt(
    """You are a helpful assistant with browsing capabilities and task planning tools.
    
    When given a web browsing task:
    1. First use the task planning tools to decompose the task into smaller sub-tasks
    2. Execute each sub-task using the browser tools
    3. Track your progress through the sub-tasks
    
    IMPORTANT: When you encounter difficulties or unexpected results:
    - DO NOT give up or conclude the task is impossible
    - DO NOT simply report failure or inability to complete the task
    - INSTEAD, use the replan_tasks tool to create a new approach
    - Consider alternative strategies, different search terms, or modified steps
    - Try at least 3 different plans before concluding a task cannot be completed
    
    Examples of when to replan:
    - If search results don't show expected content
    - If you can't find specific information on a page
    
    Remember: Most tasks have multiple solution paths. Be creative and persistent!
    Always plan before acting, and replan when facing obstacles."""
)

# Use the custom toolkit for the actual task
agent = ChatAgent(
    system_message=sys_prompt,
    model=model_backend,
    tools=[*logged_browser_tools, *logged_planning_tools],
    toolkits_to_register_agent=[web_toolkit_custom],
    max_iteration=20,  # Increased for task planning and retries
)

# Add snapshot truncation to the agent
# Keep current + 3 recent snapshots complete, truncate older ones to 15 lines
agent = add_snapshot_truncation(agent, max_snapshot_lines=15, keep_recent_full=3)

TASK_PROMPT = r"""
"Find a recipe for a vegetarian lasagna under 600 calories per serving that has a prep time of less than 1 hour.", "web": "https://www.allrecipes.com/"
"""


async def main() -> None:
    max_retries = 3
    retry_count = 0
    
    try:
        print("Task:", TASK_PROMPT)
        print(f"Using user data directory: {USER_DATA_DIR}")
        print(f"Enabled browser tools: {web_toolkit_custom.enabled_tools}")
        print(f"Task planning tools enabled: decompose_task, replan_tasks")
        print(f"📊 Snapshot truncation: keeping 4 most recent snapshots complete")
        print(f"   Older snapshots truncated to 15 lines")
        print("\n" + "="*60 + "\n")
        print("🚀 Starting task execution (tool calls will be logged in real-time)...")
        
        # Initial task decomposition and execution
        response = await agent.astep(TASK_PROMPT)
        
        # Check if task needs retrying based on tool calls and results
        while retry_count < max_retries:
            tool_calls = response.info.get('tool_calls', [])
            
            # Check for any failures in browser operations
            failed_operations = [
                call for call in tool_calls 
                if call.tool_name.startswith('browser_') and 
                ('error' in str(call.result).lower() or 'failed' in str(call.result).lower())
            ]
            
            if failed_operations:
                retry_count += 1
                print(f"\n⚠️  Detected {len(failed_operations)} failed operations. Retry {retry_count}/{max_retries}")
                
                # Create a prompt for replanning
                replan_prompt = f"""
                The following browser operations failed:
                {', '.join([f"{call.tool_name} - {call.args}" for call in failed_operations])}
                
                Please use the replan_tasks tool to adjust the approach and retry the task.
                Original task: {TASK_PROMPT}
                """
                
                print(f"\n🔄 Initiating retry with task replanning...")
                response = await agent.astep(replan_prompt)
            else:
                # No failures detected, task completed successfully
                print("\n✅ Task completed successfully!")
                break
                
        # Final response
        print("\n" + "="*60 + "\n")
        print("Final Response from agent:")
        print(response.msgs[0].content if response.msgs else "<no response>")
        
        # Show complete tool call summary using logged data
        print("\n" + "="*60 + "\n")
        print("📊 Complete Tool Call Summary:")
        print(f"Total tool calls: {len(tool_logger.all_tool_calls)}")
        
        # Group by tool type
        tool_counts = {}
        for call in tool_logger.all_tool_calls:
            tool_counts[call['name']] = tool_counts.get(call['name'], 0) + 1
        
        print("\nTool usage breakdown:")
        for tool, count in sorted(tool_counts.items()):
            print(f"  - {tool}: {count} call(s)")
        
        # Show task decomposition summary if available
        decompose_calls = [
            call for call in tool_logger.all_tool_calls
            if call['name'] in ['decompose_task', 'replan_tasks']
        ]
        if decompose_calls:
            print("\n" + "="*60 + "\n")
            print("🎯 Task Planning Details:")
            for call in decompose_calls:
                print(f"\n{call['name']}:")
                if isinstance(call['result'], list):
                    for task in call['result']:
                        print(f"  - {task.id}: {task.content}")
        
        # Show browser action sequence
        browser_calls = [
            call for call in tool_logger.all_tool_calls
            if call['name'].startswith('browser_')
        ]
        if browser_calls:
            print("\n" + "="*60 + "\n")
            print("🌐 Browser Action Sequence:")
            for i, call in enumerate(browser_calls, 1):
                print(f"{i}. {call['name']}")
                # Extract relevant info from kwargs
                kwargs = call['kwargs']
                if call['name'] == 'browser_visit_page' and 'url' in kwargs:
                    print(f"   URL: {kwargs['url']}")
                elif call['name'] == 'browser_click' and 'element_id' in kwargs:
                    print(f"   Element: {kwargs['element_id']}")
                elif call['name'] == 'browser_type' and 'text' in kwargs:
                    print(f"   Text: {kwargs['text'][:50]}{'...' if len(kwargs['text']) > 50 else ''}")
                        
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        raise
    finally:
        # Ensure browser is closed properly
        print("\nClosing browser...")
        await web_toolkit_custom.browser_close()
        print("Browser closed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
