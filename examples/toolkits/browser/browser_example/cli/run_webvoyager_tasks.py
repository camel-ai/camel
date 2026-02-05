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
#!/usr/bin/env python3
"""
Run WebVoyager tasks with browser toolkit agent and analyze results.

This script:
1. Reads tasks from WebVoyager JSONL file
2. Executes each task with browser toolkit agent
3. Uses WebJudge to verify if task requirements are met
4. If met: records success and computes session summary
5. If not met: retries the task
"""

import asyncio
import json
import re
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List

from camel.evaluators.webjudge import (
    WebJudgeVisionConfig,
    WebJudgeVisionEvaluator,
)
from examples.toolkits.browser.browser_example.core.agent import BrowserAgent
from examples.toolkits.browser.browser_example.core.modeling import (
    DEFAULT_MODEL_PLATFORM,
    DEFAULT_MODEL_TYPE,
)
from examples.toolkits.browser.utils.utils import (
    compute_session_summary,
    get_timestamp_filename,
    get_timestamp_iso,
)

_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_.-]+")


def safe_name(value: str) -> str:
    value = (value or "").strip()
    value = _SAFE_NAME_RE.sub("_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unknown"


class WebJudgeTaskVerifier:
    """WebJudge-based verifier using session evidence (vision-only)."""

    def __init__(
        self,
        *,
        vision_config: WebJudgeVisionConfig | None = None,
    ):
        resolved_config = vision_config or WebJudgeVisionConfig(
            model_platform=DEFAULT_MODEL_PLATFORM,
            model_type=DEFAULT_MODEL_TYPE,
        )
        self.vision_evaluator = WebJudgeVisionEvaluator(config=resolved_config)

    def verify_task(
        self,
        task_description: str,
        agent_response: str,
        *,
        session_dir: Path | None = None,
        website: str | None = None,
    ) -> Dict[str, Any]:
        if session_dir is None:
            return {
                "success": False,
                "reasoning": "WebJudge verifier requires session_dir evidence",
                "suggestions": "Re-run with session logging enabled and pass session_dir to the verifier.",
            }
        return self.vision_evaluator.evaluate_session(
            task=task_description,
            session_dir=session_dir,
            agent_response=agent_response,
            website=website,
        )


class WebVoyagerRunner:
    """Run WebVoyager tasks with retry logic."""

    def __init__(
        self,
        jsonl_file: str,
        website_filter: str = "",
        max_retries: int = 2,
        run_summary_out: str = "",
        results_out: str = "",
        run_dir: Path | None = None,
        step_timeout: float | None = 180.0,
        tool_execution_timeout: float | None = 180.0,
    ):
        """
        Initialize the runner.

        Args:
            jsonl_file: Path to WebVoyager JSONL file
            max_retries: Maximum retry attempts per task
        """
        self.jsonl_file = Path(jsonl_file)
        self.website_filter = website_filter.strip()
        self.max_retries = max_retries
        self.run_summary_out = (
            run_summary_out.strip() or "browser_webvoyager_run_summary.json"
        )
        self.results_out = (
            results_out.strip() or "browser_webvoyager_results_1.json"
        )
        self.run_dir = run_dir
        self.step_timeout = step_timeout
        self.tool_execution_timeout = tool_execution_timeout
        self.verifier = WebJudgeTaskVerifier()

        # Results tracking
        self.results: List[Dict[str, Any]] = []
        self.aggregate: Dict[str, Any] = {
            "generated_at": get_timestamp_iso(),
            "websites": {},
        }

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

        print(f"\n{'=' * 80}")
        print(
            f"RUNNING TASK: {task_id} (Attempt {attempt}/{self.max_retries + 1})"
        )
        print(f"{'=' * 80}")
        print(f"Task: {task_description}")
        if previous_suggestions:
            print(f"\n💡 Previous suggestions:\n{previous_suggestions}")
        print()

        website = (task.get('web_name') or '').strip()
        if not website:
            return {
                'task_id': task_id,
                'attempt': attempt,
                'success': False,
                'error': 'Missing required field: web_name',
            }

        start_url = (task.get('web') or '').strip() or None
        attempt_start_time = time.perf_counter()
        session_log_dir = None
        if self.run_dir is not None:
            session_log_dir = (
                Path(self.run_dir)
                / f"task_{safe_name(str(task_id))}_attempt_{attempt}"
            )

        agent = BrowserAgent(
            use_agent_recovery=True,
            website=website,
            session_log_dir=session_log_dir,
            start_url=start_url,
            step_timeout=self.step_timeout,
            tool_execution_timeout=self.tool_execution_timeout,
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
            agent.save_memory()
            # Save communication log
            agent.save_communication_log()

            # Write a first-pass summary (before subtask extraction), if possible
            summary_path = None
            if session_dir:
                summary_path = session_dir / "summary.json"
                summary = compute_session_summary(
                    session_dir=session_dir,
                    task_id=str(task_id),
                )
                summary["website"] = website
                summary["start_url"] = start_url
                summary["attempt"] = attempt
                summary["attempt_runtime_seconds"] = time.perf_counter() - attempt_start_time
                summary["phase"] = "post_run_pre_extract"
                summary["generated_at"] = get_timestamp_iso()

                summary_path.write_text(
                    json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )

            # Get final snapshot from agent BEFORE closing tabs
            if agent.toolkit:
                try:
                    _snapshot = await agent.toolkit.browser_get_page_snapshot()
                    # _snapshot is a string, can be stored if needed in the future
                    # For now, just capture it to ensure the browser state is recorded
                except Exception as e:
                    print(f"⚠️  Could not get final snapshot: {e}")

                # Capture final Vision-WebJudge evidence (best-effort)
                try:
                    await agent.toolkit.capture_final_evidence()
                except Exception as e:
                    print(f"⚠️  Could not capture final evidence: {e}")

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
            print(f"\n{'=' * 80}")
            print("🔍 VERIFYING TASK COMPLETION")
            print(f"{'=' * 80}")

            verification = self.verifier.verify_task(
                task_description,
                agent_response,
                session_dir=session_dir,
                website=website,
            )

            print("\n✓ Verification complete:")
            print(f"  Success: {verification['success']}")
            print(f"  Reasoning: {verification['reasoning']}")
            if verification.get('suggestions'):
                print(f"  Suggestions: {verification['suggestions']}")

            result = {
                'task_id': task_id,
                'task_description': task_description,
                'website': website,
                'attempt': attempt,
                'attempt_runtime_seconds': time.perf_counter() - attempt_start_time,
                'success': verification['success'],
                'reasoning': verification['reasoning'],
                'suggestions': verification.get('suggestions', ''),
                'session_dir': str(session_dir) if session_dir else None,
                'summary_path': str(summary_path) if summary_path else None,
            }

            # Update summary after verification/analysis
            if session_dir:
                summary_path = (
                    Path(result["summary_path"])
                    if result.get("summary_path")
                    else (session_dir / "summary.json")
                )
                summary = compute_session_summary(
                    session_dir=session_dir,
                    task_id=str(task_id),
                )
                summary["website"] = website
                summary["start_url"] = start_url
                summary["attempt"] = attempt
                summary["attempt_runtime_seconds"] = time.perf_counter() - attempt_start_time
                summary["verification"] = verification
                summary["subtask_analysis"] = result.get("subtask_analysis")
                summary["phase"] = "final"
                summary["generated_at"] = get_timestamp_iso()

                summary_path.write_text(
                    json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                result["summary_path"] = str(summary_path)

                # Update in-memory aggregate for this run
                website_bucket = self.aggregate["websites"].setdefault(
                    website,
                    {
                        "tasks": 0,
                        "attempts": 0,
                    },
                )
                website_bucket["attempts"] += 1
                if verification.get("success"):
                    website_bucket["tasks"] += 1

            return result

        except asyncio.TimeoutError as e:
            agent.save_memory()
            # Save communication log
            agent.save_communication_log()
            print(f"⏱️  Task execution timeout: {e}")
            traceback.print_exc()
            agent.close()
            
            # Write crash summary and verification result on timeout
            if session_log_dir is not None:
                try:
                    crash_summary = {
                        "task_id": str(task_id),
                        "website": website,
                        "start_url": start_url,
                        "attempt": attempt,
                        "attempt_runtime_seconds": time.perf_counter() - attempt_start_time,
                        "phase": "timeout",
                        "generated_at": get_timestamp_iso(),
                        "error": f"TimeoutError: {e}",
                        "error_type": "TimeoutError",
                    }
                    (session_log_dir / "summary.json").write_text(
                        json.dumps(crash_summary, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                except Exception as write_err:
                    print(f"⚠️  Failed to write timeout summary.json: {write_err}")
            
            return {
                'task_id': task_id,
                'attempt': attempt,
                'attempt_runtime_seconds': time.perf_counter() - attempt_start_time,
                'success': False,
                'error': f'TimeoutError: {e}',
                'is_timeout': True,
                'website': website,
                'session_dir': str(session_log_dir)
                if session_log_dir is not None
                else None,
            }

        except Exception as e:
            print(f"❌ Task execution failed: {e}")
            traceback.print_exc()
            
            # Best-effort: save logs
            try:
                agent.save_memory()
                agent.save_communication_log()
            except Exception:
                pass
            
            # Write crash summary and crash file
            if session_log_dir is not None:
                try:
                    crash_path = session_log_dir / "task_crash.txt"
                    crash_path.write_text(
                        f"{type(e).__name__}: {e}\n" + traceback.format_exc(),
                        encoding="utf-8"
                    )
                except Exception as write_err:
                    print(f"⚠️  Failed to write crash file: {write_err}")
                
                try:
                    crash_summary = {
                        "task_id": str(task_id),
                        "website": website,
                        "start_url": start_url,
                        "attempt": attempt,
                        "attempt_runtime_seconds": time.perf_counter() - attempt_start_time,
                        "phase": "crashed",
                        "generated_at": get_timestamp_iso(),
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                    (session_log_dir / "summary.json").write_text(
                        json.dumps(crash_summary, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                except Exception as write_err:
                    print(f"⚠️  Failed to write crash summary.json: {write_err}")

            return {
                'task_id': task_id,
                'attempt': attempt,
                'attempt_runtime_seconds': time.perf_counter() - attempt_start_time,
                'success': False,
                'error': str(e),
                'website': website,
                'session_dir': str(session_log_dir)
                if session_log_dir is not None
                else None,
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
        self, start_index: int = 0, max_tasks: int | None = None
    ):
        """
        Run all tasks from the JSONL file.

        Args:
            start_index: Start from this task index
            max_tasks: Maximum number of tasks to run (None = all)
        """
        tasks = self.load_tasks()

        if self.website_filter:

            def _norm(s: str) -> str:
                return " ".join((s or "").strip().lower().split())

            target = _norm(self.website_filter)
            tasks = [
                t for t in tasks if _norm(t.get("web_name", "")) == target
            ]

        print(f"\n{'=' * 80}")
        print("WEBVOYAGER TASK RUNNER")
        print(f"{'=' * 80}")
        print(f"Total tasks: {len(tasks)}")
        print(f"Start index: {start_index}")
        print(f"Max tasks: {max_tasks or 'all'}")
        print(f"Max retries per task: {self.max_retries}")
        if self.website_filter:
            print(f"Website filter: {self.website_filter}")
        if self.run_dir:
            print(f"Run dir: {self.run_dir}")
        print(f"Run summary out: {self.run_summary_out}")
        print(f"Results out: {self.results_out}")
        print()

        # Slice tasks
        if max_tasks:
            tasks = tasks[start_index : start_index + max_tasks]
        else:
            tasks = tasks[start_index:]

        print(f"Running {len(tasks)} tasks...")

        # Run each task
        for idx, task in enumerate(tasks, start=start_index):
            print(f"\n{'#' * 80}")
            print(f"TASK {idx + 1}/{len(tasks) + start_index}: {task['id']}")
            print(f"{'#' * 80}")

            result = await self.run_task_with_retries(task)
            self.results.append(result)

            # Save intermediate results
            self.save_results()
            self.save_run_summary()

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
        output_file = Path(self.results_out)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {output_file}")

    def save_run_summary(self):
        """Save a concise run summary to JSON."""
        output_file = Path(self.run_summary_out)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "generated_at": get_timestamp_iso(),
            "jsonl_file": str(self.jsonl_file),
            "website_filter": self.website_filter or None,
            "aggregate": self.aggregate,
            "tasks": [],
        }

        for task_result in self.results:
            summary["tasks"].append(
                {
                    "task_id": task_result.get("task_id"),
                    "website": task_result.get("website"),
                    "attempt": task_result.get("attempt"),
                    "success": task_result.get("success"),
                    "session_dir": task_result.get("session_dir"),
                    "summary_path": task_result.get("summary_path"),
                    "reasoning": task_result.get("reasoning"),
                }
            )

        output_file.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def print_summary(self):
        """Print summary of results."""
        print(f"\n{'=' * 80}")
        print("SUMMARY")
        print(f"{'=' * 80}")

        total = len(self.results)

        # Guard against empty results to avoid ZeroDivisionError
        if total == 0:
            print("No tasks were executed.")
            return

        succeeded = sum(1 for r in self.results if r.get('success'))
        failed = total - succeeded

        print(f"Total tasks: {total}")
        print(f"Succeeded: {succeeded} ({succeeded / total * 100:.1f}%)")
        print(f"Failed: {failed} ({failed / total * 100:.1f}%)")

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
    default_session_logs_root = script_dir.parent / "session_logs"
    default_jsonl_candidates = [
        script_dir / "WebVoyager_data.jsonl",
        Path.home() / "Downloads" / "WebVoyager_data_08312025_updated.jsonl",
    ]
    default_jsonl = str(
        next(
            (p for p in default_jsonl_candidates if p.exists()),
            default_jsonl_candidates[0],
        )
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
        "--website-filter",
        default="",
        help="Run only tasks whose web_name matches exactly (case-insensitive).",
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
    parser.add_argument(
        "--step-timeout",
        type=float,
        default=360.0,
        help="ChatAgent step timeout in seconds (0 disables). Default: 180.",
    )
    parser.add_argument(
        "--tool-timeout",
        type=float,
        default=360.0,
        help="Per-tool execution timeout in seconds (0 disables). Default: 180.",
    )
    parser.add_argument(
        "--out-dir",
        default="",
        help=(
            "Output directory for both results and run summary. "
            "When set, writes `results.json` and `run_summary.json` under this directory. "
            "Do not combine with --results-out/--run-summary-out."
        ),
    )
    parser.add_argument(
        "--run-summary-out",
        default="",
        help="Write a concise run summary JSON to this path.",
    )
    parser.add_argument(
        "--results-out",
        default="",
        help="Write the raw per-attempt results JSON to this path.",
    )

    args = parser.parse_args()

    # Unify all outputs under one run folder: <out-root>/session_<timestamp>/...
    # If --out-dir is not provided, default to examples/toolkits/session_logs.
    out_root = (
        Path(args.out_dir).expanduser().resolve()
        if args.out_dir.strip()
        else default_session_logs_root
    )

    if args.out_dir.strip() and (
        args.run_summary_out.strip() or args.results_out.strip()
    ):
        parser.error(
            "--out-dir cannot be combined with --run-summary-out or --results-out"
        )

    # If user provided a directory already named like session_YYYYMMDD_HHMMSS,
    # treat it as the run folder. Otherwise, create a new session_ folder under it.
    session_dir_pattern = re.compile(r"^session_\\d{8}_\\d{6}$")
    if session_dir_pattern.match(out_root.name):
        run_dir = out_root
    else:
        run_dir = out_root / f"session_{get_timestamp_filename()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    # Always write run-level outputs into the run folder unless explicitly overridden.
    if not args.run_summary_out.strip():
        args.run_summary_out = str(run_dir / "run_summary.json")
    if not args.results_out.strip():
        args.results_out = str(run_dir / "results.json")

    runner = WebVoyagerRunner(
        jsonl_file=args.jsonl,
        website_filter=args.website_filter,
        max_retries=args.max_retries,
        run_summary_out=args.run_summary_out,
        results_out=args.results_out,
        run_dir=run_dir,
        step_timeout=None if args.step_timeout <= 0 else args.step_timeout,
        tool_execution_timeout=None
        if args.tool_timeout <= 0
        else args.tool_timeout,
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
