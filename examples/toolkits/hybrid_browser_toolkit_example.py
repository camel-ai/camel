# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.toolkits import HybridBrowserToolkit
from camel.types import ModelPlatformType, ModelType

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ],
)

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env.test file

logging.getLogger('camel.agents').setLevel(logging.INFO)
logging.getLogger('camel.models').setLevel(logging.INFO)
logging.getLogger('camel.models').setLevel(logging.INFO)
logging.getLogger('camel.toolkits.hybrid_browser_toolkit').setLevel(
    logging.DEBUG
)
USER_DATA_DIR = "User_Data"

model_backend = ModelFactory.create(
    model_platform=ModelPlatformType.AZURE,
    model_type=ModelType.GPT_4_1,
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
    "browser_get_page_snapshot",
    "browser_get_som_screenshot",  # remove it to achieve faster operation
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
    cdp_url="http://localhost:9223",
    # Limit snapshot to current viewport to reduce context
)
print(f"Custom tools: {web_toolkit_custom.enabled_tools}")
# Use the custom toolkit for the actual task
agent = ChatAgent(
    model=model_backend,
    tools=[*web_toolkit_custom.get_tools()],
)

TASK_PROMPT = r"""
Using https://www.google.com/travel/flights/
Book a journey with return option on same day from Edinburg to Manchester on 2025 December 29th and show me the lowest price option available.

注意用enter来确认输入信息，填写日期的时候先点击日期输入框再在弹出框输入日期文本。最后要点击搜索按钮来确认搜索，并搜索到具体的航班信息
"""


def save_agent_log(agent, task_prompt, response, log_dir="./agent_logs"):
    """Save agent communications and token usage to a JSON file.

    Args:
        agent: The ChatAgent instance
        task_prompt: The task prompt string
        response: The ChatAgentResponse object
        log_dir: Directory to save logs (default: ./agent_logs)
    """
    # Create log directory if it doesn't exist
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # Generate timestamp-based filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(log_dir) / f"agent_log_{timestamp}.json"

    # Extract token usage
    usage = response.info.get('usage', {})
    prompt_tokens = usage.get('prompt_tokens', 0) if usage else 0
    completion_tokens = usage.get('completion_tokens', 0) if usage else 0
    total_tokens = usage.get('total_tokens', 0) if usage else 0

    # Extract all messages from agent's memory
    all_messages = []
    for msg in agent.memory.get_context():
        msg_dict = {
            'role': msg.role_name,
            'content': msg.content,
            'role_type': str(msg.role_type)
            if hasattr(msg, 'role_type')
            else None,
        }

        # Add function call info if available
        if hasattr(msg, 'func_name') and msg.func_name:
            msg_dict['func_name'] = msg.func_name
        if hasattr(msg, 'func_args') and msg.func_args:
            msg_dict['func_args'] = msg.func_args
        if hasattr(msg, 'func_result') and msg.func_result:
            msg_dict['func_result'] = str(msg.func_result)[
                :500
            ]  # Truncate long results

        all_messages.append(msg_dict)

    # Create log data structure
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'task_prompt': task_prompt,
        'token_usage': {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens,
        },
        'response_info': {
            'terminated': response.terminated,
            'num_tokens': response.info.get('num_tokens', 0),
            'termination_reasons': response.info.get(
                'termination_reasons', []
            ),
            'id': response.info.get('id'),
        },
        'final_response': response.msgs[0].content if response.msgs else None,
        'all_communications': all_messages,
        'tool_calls': [
            {
                'func_name': tc.func_name,
                'args': tc.args,
                'result': str(tc.result)[:500]
                if tc.result
                else None,  # Truncate long results
            }
            for tc in response.info.get('tool_calls', [])
        ],
    }

    # Save to file
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"Agent log saved to: {log_file}")
    print(f"{'='*60}")

    return log_file


async def main() -> None:
    try:
        response = await agent.astep(TASK_PROMPT)
        print("Task:", TASK_PROMPT)
        print(f"Using user data directory: {USER_DATA_DIR}")
        print(f"Enabled tools: {web_toolkit_custom.enabled_tools}")
        print("\nResponse from agent:")
        print(response.msgs[0].content if response.msgs else "<no response>")

        # Extract and display token usage
        usage = response.info.get('usage', {})
        if usage:
            print(f"\n{'='*60}")
            print("Token Usage Summary:")
            print(f"{'='*60}")
            print(f"Prompt tokens:     {usage.get('prompt_tokens', 0):,}")
            print(f"Completion tokens: {usage.get('completion_tokens', 0):,}")
            print(f"Total tokens:      {usage.get('total_tokens', 0):,}")
            print(f"{'='*60}")

        # Save detailed log
        log_file = save_agent_log(agent, TASK_PROMPT, response)

    finally:
        # Ensure browser is closed properly
        print("\nClosing browser...")
        await web_toolkit_custom.browser_close()
        print("Browser closed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
