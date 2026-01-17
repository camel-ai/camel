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
"""
Run WebVoyager tasks with subtask agent and analyze results.

This script:
1. Reads tasks from WebVoyager JSONL file
2. Executes each task with skill_agent.py
3. Uses WebJudge to verify if task requirements are met
4. If met: runs subtask_extractor.py on the session
5. If not met: provides suggestions and retries the task
"""

import asyncio
import logging
import datetime
import json
import os
from pathlib import Path

from camel.agents import ChatAgent
from camel.models import BaseModelBackend, ModelFactory
from camel.toolkits import HybridBrowserToolkit
from camel.types import ModelPlatformType, ModelType
from camel.messages.base import BaseMessage
from camel.logger import get_logger

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

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env.test file

CAMEL_LOG_DIR = Path(os.getenv("CAMEL_LOG_DIR"))
BROWSER_LOG_DIR = os.getenv("CAMEL_BROWSER_TOOL_LOG_DIR")
RESULT_DIRECTORY_PATH =Path("working_dir/google_flight")
RESULT_DIRECTORY_PATH.mkdir(parents=True, exist_ok=True)


logger = get_logger(__name__)


def load_tasks_from_jsonl(
    jsonl_path: str, start_index: int = 0, end_index: int | None = None
):
    """
    Load tasks from a JSONL file.

    Args:
        jsonl_path (str): Path to the JSONL file.
        start_index (int): Starting index (inclusive).
        end_index (int | None): Ending index (inclusive). If None, load
            all tasks from start_index.

    Returns:
        list: A list of task dictionaries.
    """
    tasks = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i < start_index:
                continue
            if end_index is not None and i > end_index:
                break
            tasks.append(json.loads(line.strip()))
    return tasks


def get_latest_conv_log(log_dir: str | Path, pattern: str = "conv_*.json") -> Path | None:
    p = Path(log_dir)
    if not p.exists():
        return None
    files = list(p.glob(pattern))
    if not files:
        return None
    return max(files, key=lambda f: f.stat().st_mtime)


async def verify_result_with_agent(
    task_content: str, result: str, model_backend: BaseModelBackend
):
    """
    Verify the workforce result using a chat agent.

    Args:
        task_content (str): The original task content.
        result (dict): The result from the workforce.
        model_backend (BaseModelBackend): The model backend to use.

    Returns:
        dict: A dictionary with 'success' (bool) and 'reasoning' (str).
    """
    verifier_agent = ChatAgent(
        system_message=(
            "You are a task verification expert. Your job is to analyze "
            "whether a task was completed successfully based on the task "
            "description and the execution result. You should output your "
            "verification in JSON format with two fields: 'success' "
            "(true/false) and 'reasoning' (explanation)."
        ),
        model=model_backend,
    )
    final_response = result if result else None
    # Build verification prompt with all available information
    verification_prompt_parts = [
        "Task Description:",
        task_content,
        "",
    ]
    # Add final response if extracted
    if final_response:
        verification_prompt_parts.extend(
            [
                "Final Agent Response:",
                str(final_response),
                "",
            ]
        )

    verification_prompt_parts.extend(
        [
            "Please verify if the task was completed successfully. Consider:",
            "1. Did the workforce complete the task objectives?",
            "2. Are there any errors or failures in the execution?",
            "3. Does the final result/answer align with the task "
            "requirements?",
            "4. Did the agent provide a comprehensive and accurate response?",
            "",
            "Output your verification in JSON format:",
            "{",
            '    "success": true/false,',
            '    "reasoning": "your detailed explanation here"',
            "}",
        ]
    )

    verification_prompt = "\n".join(verification_prompt_parts)
    response = verifier_agent.step(
        BaseMessage.make_user_message(
            role_name="Verifier", content=verification_prompt
        )
    )

    try:
        # Try to parse JSON from the response
        content = response.msg.content
        # Find JSON in the content
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        if start_idx != -1 and end_idx > start_idx:
            json_str = content[start_idx:end_idx]
            verification_result = json.loads(json_str)
        else:
            # Fallback if no JSON found
            verification_result = {
                "success": False,
                "reasoning": "Failed to parse verification response",
            }
    except Exception as e:
        verification_result = {
            "success": False,
            "reasoning": f"Error parsing verification: {e!s}",
        }

    return verification_result


async def run_browser_task(web: str, ques: str) -> None:
    """ Sets up and runs a browser-based task using the HybridBrowserToolkit.
    Args:
        web (str): The website URL to visit.
        ques (str): The question or task to perform on the website.
    """
    run_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    log_dir = CAMEL_LOG_DIR / f"run_{run_timestamp}"
    log_dir.mkdir(parents=True, exist_ok=True)
    os.environ["CAMEL_LOG_DIR"] = str(log_dir)
    # Set up browser tool log directory within the same run folder
    BROWSER_LOG_DIR_PATH = Path(BROWSER_LOG_DIR)
    BROWSER_LOG_DIR_PATH.mkdir(parents=True, exist_ok=True)

    model_backend = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
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
    # web_toolkit_          all = HybridBrowserToolkit(
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
        log_dir=BROWSER_LOG_DIR,
        stealth=True,  # Using stealth mode during browser operation
        enable_reasoning=True,
        viewport_limit=False,
        default_start_url="https://www.google.com/travel/flights/",
        # Limit snapshot to current viewport to reduce context
    )
    print(f"Custom tools: {web_toolkit_custom.enabled_tools}")
    # Use the custom toolkit for the actual task
    agent = ChatAgent(
        model=model_backend,
        tools=[*web_toolkit_custom.get_tools()],
        step_timeout=300.0,  # Increase timeout for browser operations
    )

    FINAL_TASK_PROMPT = rf"""
    Visit the website {web} using a browser and answer the following question: {ques}
    When filling in the date, first click the date input field, then enter the departure and return dates separately using the correct format, for example: 2026-01-28.
    The Enter key can be used either to confirm the input or to trigger the search.

    If you encounter an element not found error, you can use browser_get_page_snapshot to obtain the latest snapshot.
    If you want to view a screenshot, use browser_get_som_screenshot. If the screenshot shows that your task has not been completed or there is an issue, you need to make the corresponding adjustments.
    When encountering cookie consent dialogs, click "Accept All". Use browser_type and browser_enter to fill and submit forms.
    Make sure that the departure, destination, and dates are all correctly match to the information in the question.
    """
    try:
        message = BaseMessage.make_user_message(
            role_name="human", content=FINAL_TASK_PROMPT
        )
        response = await agent.astep(message)
        print("Task:", FINAL_TASK_PROMPT)
        print(f"Using user data directory: {USER_DATA_DIR}")
        print(f"Enabled tools: {web_toolkit_custom.enabled_tools}")
        print("\nResponse from agent:")
        print(response.msg.content if response.msg else "<no response>")
    finally:
        # Ensure browser is closed properly
        print("\nClosing browser...")
        await web_toolkit_custom.browser_close()
        print("Browser closed successfully.")
    return response


async def process_all_tasks(
        data_path:str,
        verifier_model:BaseModelBackend,
        start, end) -> None:
    """ Process all tasks and verify results."""
    all_results = []
    tasks = load_tasks_from_jsonl(data_path, start, end)
    print(f"Loaded {len(tasks)} tasks (index {start} to {end})")
    for idx, task_data in enumerate(tasks):
        actual_idx = start + idx
        print(f"\n{'='*80}")
        task_id = task_data.get('id', 'unknown')
        print(f"Processing Task {actual_idx}: {task_id}")
        print(f"{'='*80}")
        task_content = f"{task_data['ques']} in \"{task_data['web']}\""
        try:
            # Run the browser task
            response = await run_browser_task(task_data['web'], task_data['ques'])
            result = response.msg.content if response.msg else None

            print("\n--- Verifying Result with Agent ---")
            # Verify the result
            verification = await verify_result_with_agent(
                task_content, result, verifier_model
            )

            print("\nVerification Result:")
            print(f"  Success: {verification['success']}")
            print(f"  Reasoning: {verification['reasoning']}")

            # Store complete result
            task_result = {
                "task_index": actual_idx,
                "task_id": task_data.get('id', str(actual_idx)),
                "task_content": task_content,
                "result": result,
                "verification": verification,
            }
            all_results.append(task_result)

            # Save individual task result
            result_id = task_data.get('id', str(actual_idx))
            filename = f"task_result_{actual_idx}_{result_id}.json"
            individual_result_file = RESULT_DIRECTORY_PATH / filename
            with open(individual_result_file, 'w', encoding='utf-8') as f:
                json.dump(task_result, f, indent=2, ensure_ascii=False)

            # Save accumulated results (all tasks so far)
            results_file = f"all_results_{start}_{end}.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)

            print(f"\n=== Task {actual_idx} Complete ===")
            print(f"camel log: {os.environ.get("CAMEL_LOG_DIR", "")}")
            print(f"Task result:   {individual_result_file}")
            print(f"All results:   {results_file}")

        except Exception as e:
            print(f"\n!!! Error processing task {actual_idx}: {e!s}")
            error_result = {
                "task_index": actual_idx,
                "task_id": task_data.get('id', str(actual_idx)),
                "task_content": task_content,
                "error": str(e),
                "verification": {
                    "success": False,
                    "reasoning": f"Exception occurred: {e!s}",
                },
            }
            all_results.append(error_result)

            # Save individual error result
            result_id = task_data.get('id', str(actual_idx))
            filename = f"task_result_{actual_idx}_{result_id}.json"
            individual_result_file = RESULT_DIRECTORY_PATH / filename
            with open(individual_result_file, 'w', encoding='utf-8') as f:
                json.dump(error_result, f, indent=2, ensure_ascii=False)

            # Save accumulated results
            results_file = (
                RESULT_DIRECTORY_PATH / f"all_results_{start}_{end}.json"  # noqa: E501
            )
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)

            print(f"Error result saved to: {individual_result_file}")
    print(f"\n{'='*80}")
    print("=== All Tasks Complete ===")
    print(f"{'='*80}")
    print(f"Processed {len(tasks)} tasks")
    print(f"Results saved to: all_results_{start}_{end}.json")

            
async def main(args) -> None:
    # Load tasks from JSONL file
    if not args.jsonl or not os.path.exists(args.jsonl):
        raise ValueError(f"JSONL file not found: {args.jsonl}")
    if not args.start or args.start < 0:
        start = 0
    else:
        start = int(args.start)
    if not args.end or args.end < args.start:
        end = start
    else:
        end = int(args.end)
    # Create model backend for verification
    verifier_model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4_1,
        model_config_dict={
            "stream": False,
        },
    )
    await process_all_tasks(
        args.jsonl, verifier_model, start, end)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Run eigent workforce on WebVoyager tasks'
    )
    parser.add_argument(
        '--start', type=int, default=0, help='Start index (inclusive)'
    )
    parser.add_argument(
        '--end', type=int, default=None, help='End index (inclusive)'
    )
    parser.add_argument(
        '--jsonl',
        type=str,
        default=r'C:\Users\moizh\workspace\camel\data\webvoyager\WebVoyager_data.jsonl',
        help='Path to JSONL file',
    )
    args = parser.parse_args()
    asyncio.run(main(args))
