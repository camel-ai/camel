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
"""
Run WebVoyager tasks with subtask agent and analyze results.

This script:
1. Reads tasks from WebVoyager JSONL file
2. Executes each task with subtask_agent_example.py
3. Uses ChatAgent to verify if task requirements are met
4. If met: runs analyze_subtask_candidate.py on the session
5. If not met: provides suggestions and retries the task
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Add path first
sys.path.insert(0, str(Path(__file__).parent))

from subtask_agent_example import SubtaskAgent
from utils import create_chat_agent

from camel.messages import BaseMessage

load_dotenv()


class TaskVerifier:
    """ChatAgent to verify if task results meet requirements."""

    def __init__(self):
        """Initialize the verifier agent."""
        self.agent = create_chat_agent(
            role_name="Task Verifier",
            system_content="You are an expert at verifying if browser automation task results meet the specified requirements.",
        )

    def verify_task(
        self, task_description: str, agent_response: str
    ) -> Dict[str, Any]:
        """
        Verify if the task was completed successfully.

        Args:
            task_description: Original task description
            agent_response: Agent's final response

        Returns:
            Dict with 'success' (bool), 'reasoning' (str), and 'suggestions' (str)
        """
        # IMPORTANT: Reset agent to clear conversation history
        # This ensures each task verification is independent
        self.agent.reset()

        prompt = f"""You are verifying if a browser automation task was completed successfully.

**TASK DESCRIPTION:**
{task_description}

**AGENT'S FINAL RESPONSE:**
{agent_response}

**YOUR TASK:**
Analyze whether the task requirements were fully met. Consider:
1. Did the agent complete all required actions? Do not be too strict!


**OUTPUT FORMAT:**
Return a JSON object with exactly this structure:
```json
{{
  "success": true or false,
  "reasoning": "Detailed explanation of why the task succeeded or failed",
  "suggestions": "If failed, specific suggestions for next attempt (focus on what was missed or done incorrectly). If succeeded, leave empty string."
}}
```

Return ONLY the JSON object, no other text.
"""

        response = self.agent.step(
            BaseMessage.make_user_message(role_name="User", content=prompt)
        )

        # Parse response
        try:
            # Try to extract JSON from response
            import re

            json_match = re.search(
                r'```json\s*(.*?)\s*```', response.msg.content, re.DOTALL
            )
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                result = json.loads(response.msg.content)

            return result
        except Exception as e:
            print(f"⚠️  Failed to parse verifier response: {e}")
            print(f"Raw response: {response.msg.content}")
            return {
                "success": False,
                "reasoning": "Failed to parse verification result",
                "suggestions": "Unable to provide suggestions due to parsing error",
            }


class WebVoyagerRunner:
    """Run WebVoyager tasks with retry logic."""

    def __init__(
        self,
        jsonl_file: str,
        subtask_config_dir: str,
        max_retries: int = 2,
    ):
        """
        Initialize the runner.

        Args:
            jsonl_file: Path to WebVoyager JSONL file
            subtask_config_dir: Path to subtask configs directory
            max_retries: Maximum retry attempts per task
        """
        self.jsonl_file = Path(jsonl_file)
        self.subtask_config_dir = subtask_config_dir
        self.max_retries = max_retries
        self.verifier = TaskVerifier()

        # Ensure subtask config directory exists
        self._ensure_config_dir_exists()

        # Results tracking
        self.results: List[Dict[str, Any]] = []

    def _ensure_config_dir_exists(self):
        """
        Ensure the subtask config directory exists.
        Creates it if it doesn't exist.
        """
        config_path = Path(self.subtask_config_dir)

        if not config_path.exists():
            print(f"\n⚠️  Config directory not found: {config_path}")
            print(f"📁 Creating directory: {config_path}")
            config_path.mkdir(parents=True, exist_ok=True)
            print("✓ Directory created successfully\n")
        else:
            # Check if it's actually a directory
            if not config_path.is_dir():
                raise ValueError(
                    f"Subtask config path exists but is not a directory: {config_path}"
                )

    def load_tasks(self) -> List[Dict[str, Any]]:
        """Load tasks from JSONL file."""
        tasks = []
        with open(self.jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    tasks.append(json.loads(line))
        return tasks

    async def run_single_task(
        self,
        task: Dict[str, Any],
        attempt: int = 1,
        previous_suggestions: str = "",
    ) -> Dict[str, Any]:
        """
        Run a single task with the subtask agent.

        Args:
            task: Task dictionary
            attempt: Current attempt number
            previous_suggestions: Suggestions from previous failed attempt

        Returns:
            Result dictionary
        """
        task_id = task.get('id', 'unknown')
        task_description = task.get('ques', '')

        print(f"\n{'='*80}")
        print(
            f"RUNNING TASK: {task_id} (Attempt {attempt}/{self.max_retries + 1})"
        )
        print(f"{'='*80}")
        print(f"Task: {task_description}")
        if previous_suggestions:
            print(f"\n💡 Previous suggestions:\n{previous_suggestions}")
        print()

        # Create agent
        agent = SubtaskAgent(
            subtask_config_dir=self.subtask_config_dir,
            use_agent_recovery=True,
        )

        try:
            # Initialize
            success = await agent.initialize()
            if not success:
                return {
                    'task_id': task_id,
                    'attempt': attempt,
                    'success': False,
                    'error': 'Failed to initialize agent',
                }

            # Prepare task with suggestions if available
            full_task = task_description
            if previous_suggestions:
                full_task += f"\n\n**IMPORTANT NOTES FROM PREVIOUS ATTEMPT:**\n{previous_suggestions}"

            # Run task and get response
            response = await agent.run(full_task)

            # Get results
            session_dir = agent.session_log_dir

            # Save communication log
            agent.save_communication_log()

            # Get final snapshot from agent BEFORE closing tabs
            if agent.toolkit:
                try:
                    _snapshot = await agent.toolkit.browser_get_page_snapshot()
                    # _snapshot is a string, can be stored if needed in the future
                    # For now, just capture it to ensure the browser state is recorded
                except Exception as e:
                    print(f"⚠️  Could not get final snapshot: {e}")

            # Close browser completely after each task
            print("\n🧹 Closing browser...")
            if agent.toolkit:
                try:
                    await agent.toolkit.browser_close()
                    print("✓ Browser closed successfully")
                except Exception as e:
                    print(f"⚠️  Browser close failed: {e}")

            # Get agent's response content
            agent_response = "Task completed."
            if response and response.msgs:
                agent_response = response.msgs[0].content
            elif agent.agent_communication_log:
                # Fallback to communication log if response is empty
                last_comm = agent.agent_communication_log[-1]
                agent_response = last_comm.get('response', 'Task completed.')

            # Verify task completion
            print(f"\n{'='*80}")
            print("🔍 VERIFYING TASK COMPLETION")
            print(f"{'='*80}")

            verification = self.verifier.verify_task(
                task_description, agent_response
            )

            print("\n✓ Verification complete:")
            print(f"  Success: {verification['success']}")
            print(f"  Reasoning: {verification['reasoning']}")
            if verification.get('suggestions'):
                print(f"  Suggestions: {verification['suggestions']}")

            result = {
                'task_id': task_id,
                'task_description': task_description,
                'attempt': attempt,
                'success': verification['success'],
                'reasoning': verification['reasoning'],
                'suggestions': verification.get('suggestions', ''),
                'session_dir': str(session_dir) if session_dir else None,
            }

            # If successful, analyze for subtask candidates
            if verification['success'] and session_dir:
                print(f"\n{'='*80}")
                print("🔎 ANALYZING FOR SUBTASK CANDIDATES")
                print(f"{'='*80}")

                try:
                    from analyze_subtask_candidate import analyze_with_agent

                    analysis_result = analyze_with_agent(
                        session_folder=str(session_dir),
                        subtask_configs_dir=self.subtask_config_dir,
                        auto_save=True,
                    )

                    # Record analysis results and token usage
                    result['subtask_analysis'] = {
                        'status': 'completed',
                        'success': analysis_result.get('success', False),
                        'reusable_subtasks_found': analysis_result.get(
                            'reusable_subtasks_found', 0
                        ),
                        'token_usage': analysis_result.get('token_usage', {}),
                        'report_path': analysis_result.get('report_path', ''),
                    }

                    # Print token summary
                    token_usage = analysis_result.get('token_usage', {})
                    if token_usage:
                        print("\n📊 Subtask Analysis Token Usage:")
                        print(
                            f"  Input:  {token_usage.get('input_tokens', 0):,}"
                        )
                        print(
                            f"  Output: {token_usage.get('output_tokens', 0):,}"
                        )
                        print(
                            f"  Total:  {token_usage.get('total_tokens', 0):,}"
                        )

                except Exception as e:
                    print(f"⚠️  Subtask analysis failed: {e}")
                    import traceback

                    traceback.print_exc()
                    result['subtask_analysis'] = {
                        'status': 'failed',
                        'error': str(e),
                    }

            return result

        except asyncio.TimeoutError as e:
            print(f"⏱️  Task execution timeout: {e}")
            import traceback

            traceback.print_exc()

            return {
                'task_id': task_id,
                'attempt': attempt,
                'success': False,
                'error': f'TimeoutError: {e}',
                'is_timeout': True,
            }

        except Exception as e:
            print(f"❌ Task execution failed: {e}")
            import traceback

            traceback.print_exc()

            return {
                'task_id': task_id,
                'attempt': attempt,
                'success': False,
                'error': str(e),
            }

    async def run_task_with_retries(
        self, task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run a task with retry logic.

        Args:
            task: Task dictionary

        Returns:
            Final result dictionary with retry history
        """
        attempt = 1
        suggestions = ""
        attempt_history = []  # Track all attempts

        while attempt <= self.max_retries + 1:
            result = await self.run_single_task(task, attempt, suggestions)

            # Record this attempt in history
            attempt_history.append(
                {
                    'attempt_number': attempt,
                    'success': result.get('success', False),
                    'reasoning': result.get('reasoning', ''),
                    'suggestions': result.get('suggestions', ''),
                    'error': result.get('error', ''),
                    'session_dir': result.get('session_dir', ''),
                    'is_timeout': result.get('is_timeout', False),
                }
            )

            if result.get('success'):
                print(
                    f"\n✅ Task {task['id']} succeeded on attempt {attempt}!"
                )
                # Add retry metadata to final result
                result['total_attempts'] = attempt
                result['retry_count'] = attempt - 1
                result['attempt_history'] = attempt_history
                return result

            # Check if it's a timeout error
            is_timeout = result.get('is_timeout', False)

            # Get suggestions for next attempt
            suggestions = result.get('suggestions', '')

            if attempt < self.max_retries + 1:
                if is_timeout:
                    # For timeout errors, wait 40s before retry
                    print(
                        f"\n⏱️  Task timed out. Waiting 40 seconds before retry (attempt {attempt + 1}/{self.max_retries + 1})..."
                    )
                    await asyncio.sleep(40)
                    print("✓ Ready to retry")
                    attempt += 1
                elif suggestions:
                    # For other failures with suggestions, retry immediately
                    print(
                        f"\n🔄 Task failed. Retrying with suggestions (attempt {attempt + 1}/{self.max_retries + 1})..."
                    )
                    attempt += 1
                else:
                    # No suggestions, stop retrying
                    print(
                        f"\n❌ Task {task['id']} failed after {attempt} attempt(s)."
                    )
                    # Add retry metadata to final result
                    result['total_attempts'] = attempt
                    result['retry_count'] = attempt - 1
                    result['attempt_history'] = attempt_history
                    return result
            else:
                print(
                    f"\n❌ Task {task['id']} failed after {attempt} attempt(s)."
                )
                # Add retry metadata to final result
                result['total_attempts'] = attempt
                result['retry_count'] = attempt - 1
                result['attempt_history'] = attempt_history
                return result

        return result

    async def run_all_tasks(
        self, start_index: int = 0, max_tasks: Optional[int] = None
    ):
        """
        Run all tasks from the JSONL file.

        Args:
            start_index: Start from this task index
            max_tasks: Maximum number of tasks to run (None = all)
        """
        tasks = self.load_tasks()

        print(f"\n{'='*80}")
        print("WEBVOYAGER TASK RUNNER")
        print(f"{'='*80}")
        print(f"Total tasks: {len(tasks)}")
        print(f"Start index: {start_index}")
        print(f"Max tasks: {max_tasks or 'all'}")
        print(f"Max retries per task: {self.max_retries}")
        print()

        # Slice tasks
        if max_tasks:
            tasks = tasks[start_index : start_index + max_tasks]
        else:
            tasks = tasks[start_index:]

        print(f"Running {len(tasks)} tasks...")

        # Run each task
        for idx, task in enumerate(tasks, start=start_index):
            print(f"\n{'#'*80}")
            print(f"TASK {idx + 1}/{len(tasks) + start_index}: {task['id']}")
            print(f"{'#'*80}")

            result = await self.run_task_with_retries(task)
            self.results.append(result)

            # Save intermediate results
            self.save_results()

            # Wait 20 seconds before next task
            if (
                idx < len(tasks) + start_index - 1
            ):  # Don't wait after last task
                print("\n⏳ Waiting 20 seconds before next task...")
                await asyncio.sleep(20)
                print("✓ Ready for next task")

        # Final summary
        self.print_summary()

    def save_results(self):
        """Save results to JSON file."""
        output_file = Path("webvoyager_results_1.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {output_file}")

    def print_summary(self):
        """Print summary of results."""
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")

        total = len(self.results)

        # Guard against empty results to avoid ZeroDivisionError
        if total == 0:
            print("No tasks were executed.")
            return

        succeeded = sum(1 for r in self.results if r.get('success'))
        failed = total - succeeded

        print(f"Total tasks: {total}")
        print(f"Succeeded: {succeeded} ({succeeded/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")

        # Retry statistics
        total_retries = sum(r.get('retry_count', 0) for r in self.results)
        tasks_with_retries = sum(
            1 for r in self.results if r.get('retry_count', 0) > 0
        )
        succeeded_after_retry = sum(
            1
            for r in self.results
            if r.get('success') and r.get('retry_count', 0) > 0
        )

        print("\n📊 Retry Statistics:")
        print(f"Total retries across all tasks: {total_retries}")
        print(f"Tasks that needed retries: {tasks_with_retries}/{total}")
        print(
            f"Tasks succeeded after retry: {succeeded_after_retry}/{tasks_with_retries if tasks_with_retries > 0 else 0}"
        )

        # Show failed tasks
        if failed > 0:
            print("\n❌ Failed tasks:")
            for r in self.results:
                if not r.get('success'):
                    retry_info = (
                        f" (after {r.get('retry_count', 0)} retries)"
                        if r.get('retry_count', 0) > 0
                        else ""
                    )
                    print(
                        f"  - {r['task_id']}{retry_info}: {r.get('error') or r.get('reasoning')}"
                    )

        # Show successful tasks that needed retries
        if succeeded_after_retry > 0:
            print("\n✅ Tasks succeeded after retry:")
            for r in self.results:
                if r.get('success') and r.get('retry_count', 0) > 0:
                    print(
                        f"  - {r['task_id']}: succeeded on attempt {r.get('total_attempts', 1)}"
                    )


async def main():
    """Main entry point."""
    import argparse

    # Calculate default paths using relative path
    script_dir = Path(__file__).resolve().parent
    default_config_dir = str(script_dir / "subtask_configs")
    default_jsonl = str(
        Path.home() / "Downloads" / "WebVoyager_data_08312025_updated.jsonl"
    )

    parser = argparse.ArgumentParser(
        description="Run WebVoyager tasks with subtask agent"
    )
    parser.add_argument(
        "--jsonl",
        default=default_jsonl,
        help="Path to WebVoyager JSONL file",
    )
    parser.add_argument(
        "--config-dir",
        default=default_config_dir,
        help="Path to subtask configs directory",
    )
    parser.add_argument(
        "--start", type=int, default=0, help="Start from task index"
    )
    parser.add_argument(
        "--max-tasks", type=int, default=None, help="Maximum tasks to run"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=4,
        help="Maximum retry attempts per task",
    )

    args = parser.parse_args()

    runner = WebVoyagerRunner(
        jsonl_file=args.jsonl,
        subtask_config_dir=args.config_dir,
        max_retries=args.max_retries,
    )

    await runner.run_all_tasks(
        start_index=args.start, max_tasks=args.max_tasks
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
