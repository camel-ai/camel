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
Batch Browser Code Toolkit Processor

This script demonstrates batch processing of tasks using BrowserCodeToolkit.
It loads tasks from a JSONL file and processes them sequentially with verification.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits.browser_code_toolkit import BrowserCodeToolkit
from camel.types import ModelPlatformType, ModelType, RoleType

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()],
)

# Set log levels
logging.getLogger('camel.agents').setLevel(logging.INFO)
logging.getLogger('camel.models').setLevel(logging.INFO)
logging.getLogger('camel.toolkits').setLevel(logging.INFO)

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

USER_DATA_DIR = "User_Data"

# Model configuration
model_backend = ModelFactory.create(
    model_platform=ModelPlatformType.AZURE,
    model_type=ModelType.GPT_4_1,
    model_config_dict={"temperature": 0.0, "top_p": 1},
)

# Verification agent model
verification_model = ModelFactory.create(
    model_platform=ModelPlatformType.AZURE,
    model_type=ModelType.GPT_4_1,
    model_config_dict={"temperature": 0.0, "top_p": 1},
)

# System prompt for browser automation
SYSTEM_PROMPT = """You are a browser automation expert. You can write Python code to control a browser.

CRITICAL RULES:
1. **DO NOT write placeholder code** - Never use comments like "# find ref here" or fake ref values
2. **Work step-by-step** - You CANNOT complete tasks in one code execution
3. **Get information first** - Always call browser.get_snapshot() to see actual ref IDs before using them
4. **Use actual values only** - Only use ref IDs that you have seen in snapshot output

WORKFLOW (MUST FOLLOW):
Step 1: Open browser and get initial snapshot
```python
browser.open()
browser.visit_page("https://example.com")
snapshot = browser.get_snapshot()
print(snapshot)  # You will see the actual ref IDs here
```

Step 2: After seeing the snapshot, write code to interact with ACTUAL refs
```python
# Now you know ref="e15" is the search box from previous output
browser.type(ref="e15", text="search query")
browser.enter()
```

Step 3: Get new snapshot after interaction if needed
```python
snapshot = browser.get_snapshot()
print(snapshot)  # See updated page structure
```

EXECUTION RETURNS:
When you execute code, you will receive:
- The code you executed
- All print() output showing snapshots, results, etc.
- Any error messages

USE THIS OUTPUT to decide your next step!

COMMON MISTAKES TO AVOID:
❌ Writing all code at once without seeing ref IDs
❌ Using placeholder refs like "ref_to_find" or "element_ref"
❌ Assuming ref IDs without checking snapshot
❌ Not reading the execution output from previous step

✅ CORRECT APPROACH:
1. Execute code to get snapshot
2. Read the output to find actual ref IDs
3. Execute new code using those actual ref IDs
4. Repeat until task is complete

填写日期的时候先点击日期框，然后再分别输入去程和返程日期，用正确格式如：2026-01-28
enter可以作为确认，也可以用来执行搜索
"""

# Custom tools selection
custom_tools = [
    "browser_open",
    "browser_close",
    "browser_visit_page",
    "browser_back",
    "browser_forward",
    "browser_click",
    "browser_type",
    "browser_enter",
    "browser_get_page_snapshot",
]

# Create output directory
output_dir = Path("batch_browser_code_results")
output_dir.mkdir(exist_ok=True)

# JSONL file path
JSONL_PATH = '/Users/puzhen/Downloads/WebVoyager_data (3).jsonl'


def load_tasks_from_jsonl(
    start_index: int = 0, end_index: int = None, filter_keyword: str = None
):
    """
    Load tasks from JSONL file

    Args:
        start_index: Starting index (inclusive)
        end_index: Ending index (exclusive), None means to the end
        filter_keyword: Filter tasks by keyword in 'web' field

    Returns:
        List of task dictionaries
    """
    tasks = []
    with open(JSONL_PATH, 'r', encoding='utf-8') as f:
        for idx, line in enumerate(f):
            # Skip until start_index
            if idx < start_index:
                continue

            # Stop at end_index
            if end_index is not None and idx >= end_index:
                break

            data = json.loads(line)

            # Apply filter if specified
            if filter_keyword:
                if filter_keyword not in data.get('web', '').lower():
                    continue

            tasks.append(
                {
                    'index': idx,
                    'web': data.get('web', ''),
                    'question': data.get('ques', ''),
                }
            )

    return tasks


async def verify_response(question: str, response: str) -> dict:
    """Use a verification agent to check if the response satisfies the question requirements"""
    verification_agent = ChatAgent(
        model=verification_model,
        system_message=BaseMessage(
            role_name="Verifier",
            role_type=RoleType.ASSISTANT,
            meta_dict={},
            content="""You are a verification agent. Your job is to check if the agent's response adequately satisfies the user's question/task requirements.

Analyze the question and the response, then provide:
1. A boolean verdict (True/False) - whether the response satisfies the requirements
2. A detailed explanation of your reasoning
3. What was expected vs what was provided
4. Any missing information or errors

Return your analysis in a structured format.""",
        ),
    )

    verification_prompt = f"""
Question/Task: {question}

Agent's Response: {response}

Please verify if this response adequately completes the task. Provide:
1. Verdict (satisfied/not_satisfied)
2. Reasoning
3. Expected information vs Provided information
4. Missing elements (if any)
"""

    try:
        verification_result = await verification_agent.astep(
            verification_prompt
        )
        verification_text = (
            verification_result.msgs[0].content
            if verification_result.msgs
            else "No verification response"
        )

        return {
            "verified": True,
            "verification_text": verification_text,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "verified": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


async def process_single_task(
    task_idx: int, total_tasks: int, task: dict
) -> dict:
    """Process a single task using BrowserCodeToolkit"""
    print(f"\n{'='*80}")
    print(f"Processing Task {task_idx + 1}/{total_tasks}")
    print(f"Index: {task['index']}")
    print(f"Website: {task['web']}")
    print(f"Question: {task['question'][:100]}...")
    print(f"{'='*80}\n")

    # Create toolkit for this task
    toolkit = BrowserCodeToolkit(
        browser_mode="typescript",
        sandbox="internal_python",
        headless=False,
        user_data_dir=USER_DATA_DIR,
        enabled_tools=custom_tools,
        print_code_output=True,
        browser_log_to_file=True,
        stealth=True,
        viewport_limit=True,
    )

    # Create agent
    agent = ChatAgent(
        model=model_backend,
        system_message=BaseMessage.make_assistant_message(
            role_name="Browser Automation Expert",
            content=SYSTEM_PROMPT,
        ),
        tools=toolkit.get_tools(),
        max_iteration=15,
    )

    # Prepare task prompt
    task_prompt = f"""
Visit the website: {task['web']}

Task: {task['question']}

Use the execute_browser_code tool to control the browser and complete this task.
"""

    result = {
        "task_index": task['index'],
        "website": task['web'],
        "question": task['question'],
        "task_prompt": task_prompt,
        "response": None,
        "verification": None,
        "error": None,
        "timestamp": datetime.now().isoformat(),
    }

    try:
        # Execute task
        print("Executing task...")
        response = await agent.astep(task_prompt)
        response_text = (
            response.msgs[0].content if response.msgs else "<no response>"
        )
        result["response"] = response_text

        print("\nResponse from agent:")
        print(response_text)

        # Verify response
        print("\nVerifying response...")
        verification = await verify_response(task['question'], response_text)
        result["verification"] = verification

        print("\nVerification result:")
        print(verification.get("verification_text", "No verification text"))

    except Exception as e:
        error_msg = f"Error processing task: {e!s}"
        print(error_msg)
        import traceback

        traceback.print_exc()
        result["error"] = error_msg

    finally:
        # Clean up resources
        try:
            print("\nCleaning up browser resources...")
            await toolkit.cleanup()
            print("Browser closed successfully.")
        except Exception as e:
            print(f"Error closing browser: {e}")

    # Save individual result
    result_file = output_dir / f"task_{task['index']}_result.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nResult saved to: {result_file}")

    return result


async def main():
    """Main function to process tasks in batch"""
    print("=" * 80)
    print("Batch Browser Code Toolkit Processor")
    print("=" * 80)

    # Configuration - Modify these parameters to customize batch processing
    START_INDEX = 428  # Starting task index
    END_INDEX = None  # Ending task index (None = process all remaining)
    FILTER_KEYWORD = (
        'google.com/travel/flights'  # Filter by website (None = no filter)
    )

    print("\nConfiguration:")
    print(f"  JSONL file: {JSONL_PATH}")
    print(f"  Start index: {START_INDEX}")
    print(f"  End index: {END_INDEX if END_INDEX else 'End of file'}")
    print(f"  Filter keyword: {FILTER_KEYWORD if FILTER_KEYWORD else 'None'}")
    print(f"  Output directory: {output_dir.absolute()}")

    # Load tasks
    print("\nLoading tasks from JSONL file...")
    all_tasks = load_tasks_from_jsonl(
        start_index=START_INDEX,
        end_index=END_INDEX,
        filter_keyword=FILTER_KEYWORD,
    )

    print(f"Loaded {len(all_tasks)} tasks")
    if all_tasks:
        print(
            f"Task range: indices {all_tasks[0]['index']} to {all_tasks[-1]['index']}"
        )

    if not all_tasks:
        print("No tasks to process. Exiting.")
        return

    # Process all tasks
    all_results = []
    for idx, task in enumerate(all_tasks):
        result = await process_single_task(idx, len(all_tasks), task)
        all_results.append(result)

        # Save cumulative results
        summary_file = output_dir / "all_results_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(
                {
                    "configuration": {
                        "start_index": START_INDEX,
                        "end_index": END_INDEX,
                        "filter_keyword": FILTER_KEYWORD,
                        "jsonl_path": JSONL_PATH,
                    },
                    "total_tasks": len(all_tasks),
                    "processed_tasks": idx + 1,
                    "results": all_results,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        print(f"\n[Progress: {idx + 1}/{len(all_tasks)} tasks completed]")

        # Optional: Add delay between tasks to avoid rate limiting
        if idx < len(all_tasks) - 1:
            await asyncio.sleep(2)

    # Final summary
    print(f"\n{'='*80}")
    print("BATCH PROCESSING COMPLETE")
    print(f"{'='*80}")
    print(f"Total tasks processed: {len(all_results)}")
    print(f"Results saved to: {output_dir.absolute()}")
    print(f"Summary file: {summary_file.absolute()}")

    # Generate statistics
    successful = sum(
        1 for r in all_results if r.get('response') and not r.get('error')
    )
    failed = sum(1 for r in all_results if r.get('error'))

    print("\nStatistics:")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Success rate: {successful / len(all_results) * 100:.1f}%")

    stats_file = output_dir / "statistics.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(
            {
                "total_tasks": len(all_results),
                "successful": successful,
                "failed": failed,
                "success_rate": successful / len(all_results)
                if all_results
                else 0,
                "timestamp": datetime.now().isoformat(),
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"Statistics saved to: {stats_file.absolute()}")


if __name__ == "__main__":
    asyncio.run(main())
