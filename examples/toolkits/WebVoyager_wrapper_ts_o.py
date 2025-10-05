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

"""
Quick WebVoyager Test - TypeScript Original Version

This script provides a lightweight way to test the ORIGINAL TypeScript version
of the Hybrid Browser Toolkit (without reflection capabilities) on WebVoyager
tasks.

Usage:
    python WebVoyager_wrapper_ts_o.py [num_tasks]

    num_tasks: Number of tasks to run (default: 10)
               Use -1 to run all tasks in the dataset

Examples:
    python WebVoyager_wrapper_ts_o.py      # Run 10 tasks
    python WebVoyager_wrapper_ts_o.py 5    # Run 5 tasks
    python WebVoyager_wrapper_ts_o.py -1   # Run all tasks
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime

# Add the camel directory to the path - go up two levels to reach camel
# directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from camel.agents import ChatAgent
    from camel.messages import BaseMessage
    from camel.models import ModelFactory

    # Import the ORIGINAL version without reflection
    from camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit_ts_o import (  # noqa: E501
        HybridBrowserToolkit,
    )
    from camel.types import ModelPlatformType, ModelType
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the correct directory")
    sys.exit(1)


def setup_logging():
    """Setup logging configuration."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"webvoyager_test_ts_o_{timestamp}.log"

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout),  # Also log to console
        ],
    )

    return log_filename


async def quick_test(num_tasks: int = 10):
    """Run test on WebVoyager tasks using TypeScript implementation.

    Args:
        num_tasks: Number of tasks to run (use -1 for all tasks)
    """

    # Setup logging
    log_filename = setup_logging()
    logger = logging.getLogger(__name__)

    print("🚀 Starting WebVoyager Test - TypeScript ORIGINAL Version")
    print("📦 Using HybridBrowserToolkit (WITHOUT reflection parameters)")
    logger.info("Starting WebVoyager Test - TypeScript ORIGINAL Version")
    logger.info("Using HybridBrowserToolkit (WITHOUT reflection parameters)")

    # Load dataset - fix the path to use relative path
    dataset_path = os.path.join(
        os.path.dirname(__file__), '..', '..', '..', 'WebVoyager_data.jsonl'
    )

    if not os.path.exists(dataset_path):
        print(f"❌ Dataset not found at: {dataset_path}")
        logger.error(f"Dataset not found at: {dataset_path}")
        return []

    # Load all tasks from the dataset
    tasks = []
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                task = json.loads(line.strip())
                tasks.append(task)

    total_in_dataset = len(tasks)

    # Limit to num_tasks if specified (unless -1 for all)
    if num_tasks > 0:
        tasks = tasks[:num_tasks]
        print(f"📊 Running {len(tasks)}/{total_in_dataset} tasks from dataset")
        logger.info(
            f"Running {len(tasks)}/{total_in_dataset} tasks from dataset"
        )
    else:
        print(
            f"📊 Running ALL {total_in_dataset} tasks from WebVoyager dataset"
        )
        logger.info(
            f"Running ALL {total_in_dataset} tasks from WebVoyager dataset"
        )

    total_tasks = len(tasks)

    # Initialize TypeScript toolkit (original version)
    toolkit = HybridBrowserToolkit(
        headless=True,  # Set to False if you want to see the browser
        user_data_dir="User_Data_TS_Original",
    )

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict={"temperature": 0.0, "top_p": 1},
    )

    # Create agent with proper toolkit integration
    # NOTE: No reflection parameters in system message since toolkit doesn't
    # support them
    agent = ChatAgent(
        model=model,
        system_message=BaseMessage.make_assistant_message(
            role_name="Web Navigator",
            content=(
                "You are a web automation expert. Your job is to complete web "
                "tasks autonomously using browser tools.\n\n"
                "Work independently until the task is complete. Do not ask "
                "for next steps.\n\n"
                "Workflow: navigate → search → click → extract → answer.\n"
            ),
        ),
        tools=toolkit.get_tools(),
        toolkits_to_register_agent=[toolkit],
        max_iteration=20,
    )

    # Process tasks
    task_results = []

    for i, task in enumerate(tasks, 1):
        print(f"\n{'='*60}")
        print(f"📋 TASK {i}/{total_tasks} [{task['id']}]")
        print(f"Question: {task['ques']}")
        print(f"Website: {task['web']}")
        print("─" * 60)

        logger.info(f"Starting Task {i}/{total_tasks} [{task['id']}]")
        logger.info(f"Question: {task['ques']}")
        logger.info(f"Website: {task['web']}")

        try:
            # Create generic task prompt for evaluation
            task_prompt = f"""
Use the browser to complete this task: {task['ques']}

Website: {task['web']}

Instructions:
- Navigate to the website and complete the task
- Provide a complete answer when finished
"""

            # Single step call - let CAMEL handle iterations internally
            response = await agent.astep(task_prompt)

            if response.msgs:
                answer = response.msgs[-1].content
                print("\n💬 FINAL ANSWER:")
                print(answer)
                print("─" * 60)

                logger.info(f"Task {task['id']} completed successfully")
                logger.info(f"Answer: {answer}")

                task_results.append(
                    {'task_id': task['id'], 'success': True, 'answer': answer}
                )
            else:
                print("\n💬 FINAL ANSWER:")
                print("No response from agent")
                print("─" * 60)

                logger.warning(
                    f"Task {task['id']} failed: No response from agent"
                )
                task_results.append(
                    {
                        'task_id': task['id'],
                        'success': False,
                        'error': 'No response',
                    }
                )

            # Clear agent's message history to prevent context accumulation
            agent.reset()

        except Exception as e:
            print("\n💬 FINAL ANSWER:")
            print(f"Task failed: {e!s}")
            print("─" * 60)

            logger.error(f"Task {task['id']} failed with exception: {e}")
            task_results.append(
                {'task_id': task['id'], 'success': False, 'error': str(e)}
            )
            # Reset agent even on error
            agent.reset()

    # Clean up browser at the end
    try:
        await toolkit.browser_close()
    except Exception:
        pass

    # Simple summary
    successful = sum(1 for r in task_results if r['success'])
    print(f"\n{'='*60}")
    print(
        f"📊 FINAL SUMMARY: {successful}/{len(task_results)} tasks completed"
    )
    print(f"Success rate: {successful/len(task_results)*100:.1f}%")
    print("=" * 60)

    logger.info(
        f"FINAL SUMMARY: {successful}/{len(task_results)} tasks completed"
    )
    logger.info(f"Success rate: {successful/len(task_results)*100:.1f}%")

    # Write detailed results to JSON file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_filename = f"webvoyager_results_ts_o_{timestamp}.json"
    with open(results_filename, 'w', encoding='utf-8') as f:
        json.dump(
            {
                'summary': {
                    'total_tasks': len(task_results),
                    'successful_tasks': successful,
                    'failed_tasks': len(task_results) - successful,
                    'success_rate': successful / len(task_results) * 100,
                    'timestamp': datetime.now().isoformat(),
                    'version': 'original_typescript',
                },
                'results': task_results,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    logger.info(f"Detailed results saved to: {results_filename}")
    logger.info(f"Log file saved as: {log_filename}")
    print(f"\n📁 Results saved to: {results_filename}")
    print(f"📁 Log file saved as: {log_filename}")

    return task_results


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description=(
            'Run WebVoyager tasks with TypeScript Browser Toolkit (Original)'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python WebVoyager_wrapper_ts_o.py         # Run 10 tasks (default)
  python WebVoyager_wrapper_ts_o.py 5       # Run 5 tasks
  python WebVoyager_wrapper_ts_o.py -1      # Run all tasks
  python WebVoyager_wrapper_ts_o.py 100     # Run 100 tasks
        """,
    )
    parser.add_argument(
        'num_tasks',
        type=int,
        nargs='?',
        default=10,
        help='Number of tasks to run (default: 10, use -1 for all)',
    )

    args = parser.parse_args()

    num_tasks = args.num_tasks

    print("🧪 Starting WebVoyager Test with TypeScript Implementation...")
    print("📝 Using ORIGINAL version (no reflection parameters)")
    if num_tasks == -1:
        print("🎯 Running ALL WebVoyager tasks...")
    elif num_tasks == 1:
        print(f"🎯 Running {num_tasks} task...")
    else:
        print(f"🎯 Running {num_tasks} tasks...")

    try:
        results = asyncio.run(quick_test(num_tasks=num_tasks))
        print("✅ Script completed successfully")

    except Exception as e:
        print(f"❌ Script failed with error: {e}")
        import traceback

        traceback.print_exc()
