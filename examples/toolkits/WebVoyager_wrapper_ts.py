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
Quick WebVoyager Test - TypeScript Version

This script provides a lightweight way to test the TypeScript version of the
Hybrid Browser Toolkit with reflection capabilities on a few WebVoyager
tasks.
"""

import asyncio
import json
import os
import sys

# Add the camel directory to the path - go up two levels to reach camel
# directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from camel.agents import ChatAgent
    from camel.messages import BaseMessage
    from camel.models import ModelFactory
    from camel.toolkits.hybrid_browser_toolkit.hybrid_browser_toolkit_ts import (  # noqa: E501
        HybridBrowserToolkit,
    )
    from camel.types import ModelPlatformType, ModelType
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the correct directory")
    sys.exit(1)


async def quick_test(num_tasks: int = 10):
    """Run test on WebVoyager tasks using TypeScript implementation.

    Args:
        num_tasks: Number of tasks to run
    """

    print("🚀 Starting WebVoyager Test - TypeScript Version")
    print("📦 Using HybridBrowserToolkit (TypeScript implementation)")

    # Load dataset - fix the path to use relative path
    dataset_path = os.path.join(
        os.path.dirname(__file__), '..', '..', '..', 'WebVoyager_data.jsonl'
    )

    if not os.path.exists(dataset_path):
        print(f"❌ Dataset not found at: {dataset_path}")
        return []

    tasks = []
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= num_tasks + 1:
                break
            if line.strip() and i >= 1:  # Skip first task, start from second
                task = json.loads(line.strip())
                tasks.append(task)

    print(f"📊 Loaded {len(tasks)} tasks from dataset")

    # Initialize TypeScript toolkit
    toolkit = HybridBrowserToolkit(
        headless=True,  # Set to False if you want to see the browser
        user_data_dir="User_Data_TS",
    )

    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O,
        model_config_dict={"temperature": 0.0, "top_p": 1},
    )

    # Create agent with proper toolkit integration
    agent = ChatAgent(
        model=model,
        system_message=BaseMessage.make_assistant_message(
            role_name="Web Navigator",
            content=(
                "You are a web automation expert. Your job is to complete web "
                "tasks autonomously using browser tools.\n\n"
                "IMPORTANT:\n"
                "• When you call ANY `browser_*` tool, ALWAYS include two "
                "keyword args:\n"
                "  - thinking: one short sentence explaining why this action\n"
                "  - next_goal: one short sentence describing your next planned "  # noqa: E501
                "action\n"
                "• Work independently until the task is complete. Do not ask "
                "for next steps.\n"
                "• Steps: navigate → search → click → extract → answer.\n"
            ),
        ),
        tools=toolkit.get_tools(),  # Get tools from toolkit
        toolkits_to_register_agent=[toolkit],  # Register agent with toolkit
        max_iteration=10,
    )

    # Process tasks
    task_results = []

    for i, task in enumerate(tasks, 1):
        print(f"\n📋 TASK {i}: {task['ques']}")
        print("─" * 60)

        try:
            # Create specific, actionable task prompt
            task_prompt = f"""
        Use the browser to complete this task: {task['ques']}

        Website: {task['web']}

        Instructions:
        - Navigate to the website and complete the task
        - Use the reasoning parameters (thinking and next_goal) for 
            each browser action, use the reasoning parameters 
            from the previous tool calls to guide your decision
            making process
        - If you notice repetitive tool calls break out of the loop and choose
            a different approach
        - Provide a complete answer when finished
        """

            # Single step call - let CAMEL handle iterations internally
            response = await agent.astep(task_prompt)

            if response.msgs:
                answer = response.msgs[-1].content
                print("\n💬 FINAL ANSWER:")
                print(answer)
                print("─" * 60)

                task_results.append(
                    {'task_id': task['id'], 'success': True, 'answer': answer}
                )
            else:
                print("\n💬 FINAL ANSWER:")
                print("No response from agent")
                print("─" * 60)
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
            task_results.append(
                {'task_id': task['id'], 'success': False, 'error': str(e)}
            )

    # Clean up browser at the end
    try:
        await toolkit.browser_close(
            "Cleaning up browser after all tasks", "Task completed"
        )
    except Exception:
        pass

    # Simple summary
    successful = sum(1 for r in task_results if r['success'])
    print(
        f"\n📊 SUMMARY: {successful}/{len(task_results)} tasks completed successfully"  # noqa: E501
    )

    return task_results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="WebVoyager Test with TypeScript Hybrid Browser Toolkit"
    )
    parser.add_argument(
        "--num-tasks",
        type=int,
        default=3,
        help="Number of tasks to run (default: 3)",
    )

    args = parser.parse_args()

    print("🧪 Starting WebVoyager Test with TypeScript Implementation...")
    try:
        results = asyncio.run(quick_test(num_tasks=args.num_tasks))
        print("✅ Script completed successfully")

    except Exception as e:
        print(f"❌ Script failed with error: {e}")
        import traceback

        traceback.print_exc()
