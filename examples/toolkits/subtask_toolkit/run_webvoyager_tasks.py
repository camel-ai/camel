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

load_dotenv()

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# Import the subtask agent
sys.path.insert(0, str(Path(__file__).parent))
from subtask_agent_example import SubtaskAgent


class TaskVerifier:
    """ChatAgent to verify if task results meet requirements."""

    def __init__(self):
        """Initialize the verifier agent."""
        model = ModelFactory.create(
            model_platform=ModelPlatformType.AZURE,
            model_type=ModelType.GPT_4_1,
            model_config_dict={"temperature": 0.0},
        )

        self.agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name="Task Verifier",
                content="You are an expert at verifying if browser automation task results meet the specified requirements.",
            ),
            model=model,
        )

    def verify_task(
        self, task_description: str, final_snapshot: str, agent_response: str
    ) -> Dict[str, Any]:
        """
        Verify if the task was completed successfully.

        Args:
            task_description: Original task description
            final_snapshot: Final page snapshot
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

**FINAL PAGE SNAPSHOT:**
{final_snapshot[:5000]}  # First 5000 chars

**YOUR TASK:**
Analyze whether the task requirements were fully met. Consider:
1. Did the agent complete all required actions?
2. Is the final state what the task asked for?
3. Are there any missing steps or errors?

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

        # Results tracking
        self.results: List[Dict[str, Any]] = []

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
        self, task: Dict[str, Any], attempt: int = 1, previous_suggestions: str = ""
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
        print(f"RUNNING TASK: {task_id} (Attempt {attempt}/{self.max_retries + 1})")
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

            # Run task
            await agent.run(full_task)

            # Get results
            session_dir = agent.session_log_dir

            # Save communication log
            agent.save_communication_log()

            # Get final snapshot from agent
            final_snapshot = ""
            if agent.toolkit:
                try:
                    snapshot_result = await agent.toolkit.browser_get_page_snapshot()
                    final_snapshot = snapshot_result.get('snapshot', '')
                except Exception as e:
                    print(f"⚠️  Could not get final snapshot: {e}")

            # Get agent's last response (from communication log)
            agent_response = "Task completed."
            if agent.agent_communication_log:
                last_comm = agent.agent_communication_log[-1]
                agent_response = last_comm.get('content', 'Task completed.')

            # Verify task completion
            print(f"\n{'='*80}")
            print("🔍 VERIFYING TASK COMPLETION")
            print(f"{'='*80}")

            verification = self.verifier.verify_task(
                task_description, final_snapshot, agent_response
            )

            print(f"\n✓ Verification complete:")
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

                    analyze_with_agent(
                        session_folder=str(session_dir),
                        subtask_configs_dir=self.subtask_config_dir,
                        auto_save=True,
                    )
                    result['subtask_analysis'] = 'completed'
                except Exception as e:
                    print(f"⚠️  Subtask analysis failed: {e}")
                    import traceback

                    traceback.print_exc()
                    result['subtask_analysis'] = f'failed: {e}'

            return result

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
            Final result dictionary
        """
        attempt = 1
        suggestions = ""

        while attempt <= self.max_retries + 1:
            result = await self.run_single_task(task, attempt, suggestions)

            if result.get('success'):
                print(f"\n✅ Task {task['id']} succeeded on attempt {attempt}!")
                return result

            # Get suggestions for next attempt
            suggestions = result.get('suggestions', '')

            if attempt < self.max_retries + 1 and suggestions:
                print(
                    f"\n🔄 Task failed. Retrying with suggestions (attempt {attempt + 1}/{self.max_retries + 1})..."
                )
                attempt += 1
            else:
                print(
                    f"\n❌ Task {task['id']} failed after {attempt} attempt(s)."
                )
                return result

        return result

    async def run_all_tasks(self, start_index: int = 0, max_tasks: Optional[int] = None):
        """
        Run all tasks from the JSONL file.

        Args:
            start_index: Start from this task index
            max_tasks: Maximum number of tasks to run (None = all)
        """
        tasks = self.load_tasks()

        print(f"\n{'='*80}")
        print(f"WEBVOYAGER TASK RUNNER")
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

        # Final summary
        self.print_summary()

    def save_results(self):
        """Save results to JSON file."""
        output_file = Path("webvoyager_results.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {output_file}")

    def print_summary(self):
        """Print summary of results."""
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")

        total = len(self.results)
        succeeded = sum(1 for r in self.results if r.get('success'))
        failed = total - succeeded

        print(f"Total tasks: {total}")
        print(f"Succeeded: {succeeded} ({succeeded/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")

        # Show failed tasks
        if failed > 0:
            print(f"\nFailed tasks:")
            for r in self.results:
                if not r.get('success'):
                    print(
                        f"  - {r['task_id']}: {r.get('error') or r.get('reasoning')}"
                    )


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run WebVoyager tasks with subtask agent"
    )
    parser.add_argument(
        "--jsonl",
        default="/Users/puzhen/Downloads/WebVoyager_data_08312025_updated.jsonl",
        help="Path to WebVoyager JSONL file",
    )
    parser.add_argument(
        "--config-dir",
        default="/Users/puzhen/Desktop/pre/camel_project/camel/examples/toolkits/subtask_configs",
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
        default=2,
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
