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
# ruff: noqa: E402
#!/usr/bin/env python3
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
import json
import re
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Add path first
sys.path.insert(0, str(Path(__file__).parent))

from skill_agent import SkillsAgent
from utils import (
    compute_session_summary,
    count_skills_in_dir,
    count_subtasks_in_dir,
    get_timestamp_filename,
    get_timestamp_iso,
    resolve_website_skills_dir,
    update_cumulative_subtask_stats,
)

load_dotenv()

from modeling import DEFAULT_MODEL_PLATFORM, DEFAULT_MODEL_TYPE

from camel.evaluators.webjudge import (
    WebJudgeVisionConfig,
    WebJudgeVisionEvaluator,
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
        skills_root: str,
        skills_dir: str = "",
        website_filter: str = "",
        max_retries: int = 4,
        max_attempts_per_website: int = 100,
        run_summary_out: str = "",
        results_out: str = "",
        run_dir: Path | None = None,
        step_timeout: float | None = 180.0,
        tool_execution_timeout: float | None = 180.0,
        enable_skills: bool = True,
    ):
        """
        Initialize the runner.

        Args:
            jsonl_file: Path to WebVoyager JSONL file
            skills_root: Root directory for per-website skills.
            max_retries: Maximum retry attempts per task
            enable_skills: Enable skill loading, usage, and generation (default: True)
        """
        self.jsonl_file = Path(jsonl_file)
        resolved_root = skills_root.strip()
        if not resolved_root:
            raise ValueError("skills_root must be a non-empty path.")
        self.skills_root = Path(resolved_root).expanduser()
        self.skills_dir_override = (
            Path(skills_dir).expanduser().resolve()
            if skills_dir.strip()
            else None
        )
        self.website_filter = website_filter.strip()
        self.max_retries = max_retries
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0.")
        self.max_attempts_per_website = int(max_attempts_per_website)
        if self.max_attempts_per_website <= 0:
            raise ValueError("max_attempts_per_website must be > 0.")
        self.run_summary_out = (
            run_summary_out.strip() or "webvoyager_run_summary.json"
        )
        self.results_out = results_out.strip() or "webvoyager_results_1.json"
        self.run_dir = run_dir
        self.step_timeout = step_timeout
        self.tool_execution_timeout = tool_execution_timeout
        self.enable_skills = enable_skills
        self.verifier = WebJudgeTaskVerifier()

        # Ensure skills directories exist
        self._ensure_skills_dirs_exist()

        # Results tracking
        self.results: List[Dict[str, Any]] = []
        self.aggregate: Dict[str, Any] = {
            "generated_at": get_timestamp_iso(),
            "websites": {},
        }
        self._website_attempt_counts: Dict[str, int] = {}

    @staticmethod
    def _normalize_website_key(website: str) -> str:
        return " ".join((website or "").strip().lower().split())

    def _website_attempts_used(self, website: str) -> int:
        return int(
            self._website_attempt_counts.get(
                self._normalize_website_key(website), 0
            )
            or 0
        )

    def _reserve_website_attempt(self, website: str) -> bool:
        website_key = self._normalize_website_key(website)
        used = int(self._website_attempt_counts.get(website_key, 0) or 0)
        if used >= self.max_attempts_per_website:
            return False
        self._website_attempt_counts[website_key] = used + 1
        return True

    def _ensure_skills_dirs_exist(self):
        """Ensure configured skills directories exist."""
        if self.skills_dir_override is not None:
            if not self.website_filter:
                raise ValueError(
                    "skills_dir can only be used together with --website-filter "
                    "(because WebVoyager tasks can span multiple websites)."
                )
            self.skills_dir_override.mkdir(parents=True, exist_ok=True)
            return

        base_path = self.skills_root

        if not base_path.exists():
            print(f"\n⚠️  Skills directory not found: {base_path}")
            print(f"📁 Creating directory: {base_path}")
            base_path.mkdir(parents=True, exist_ok=True)
            print("✓ Directory created successfully\n")
        elif not base_path.is_dir():
            raise ValueError(
                f"Skills path exists but is not a directory: {base_path}"
            )

    def _resolve_skills_dir_for_task(self, website: str) -> Path:
        if self.skills_dir_override is not None:
            return self.skills_dir_override
        return resolve_website_skills_dir(self.skills_root, website)

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
        started_at = get_timestamp_iso()
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
                'started_at': started_at,
                'finished_at': get_timestamp_iso(),
            }

        start_url = (task.get('web') or '').strip() or None

        skills_dir = self._resolve_skills_dir_for_task(website)
        subtasks_before = (
            count_skills_in_dir(skills_dir)
            if any(skills_dir.glob("*/SKILL.md"))
            else count_subtasks_in_dir(skills_dir)
        )

        session_log_dir = None
        if self.run_dir is not None:
            session_log_dir = (
                Path(self.run_dir)
                / f"task_{safe_name(str(task_id))}_attempt_{attempt}"
            )

        agent = SkillsAgent(
            skills_dir=str(skills_dir),
            use_agent_recovery=True,
            website=website,
            session_log_dir=session_log_dir,
            start_url=start_url,
            step_timeout=self.step_timeout,
            tool_execution_timeout=self.tool_execution_timeout,
            enable_skills=self.enable_skills,
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

            # Write a first-pass summary (before subtask extraction), if possible
            summary_path = None
            if session_dir:
                summary_path = session_dir / "summary.json"
                summary = compute_session_summary(
                    session_dir=session_dir,
                    skills_dir=skills_dir,
                    task_id=str(task_id),
                )
                summary["website"] = website
                summary["start_url"] = start_url
                summary["attempt"] = attempt
                summary["subtasks_available_before"] = subtasks_before
                summary["subtasks_available_after"] = (
                    count_skills_in_dir(skills_dir)
                    if any(skills_dir.glob("*/SKILL.md"))
                    else count_subtasks_in_dir(skills_dir)
                )
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

            # Extract subtasks ONLY after we have a verified successful run.
            # This prevents unstable/failed trajectories from polluting skills.
            subtask_analysis = None
            if self.enable_skills and session_dir and verification.get("success"):
                print(f"\n{'=' * 80}")
                print("🔎 EXTRACTING SUBTASKS (SKILLS)")
                print(f"{'=' * 80}")
                try:
                    from subtask_extractor import analyze_with_agent

                    subtask_analysis = analyze_with_agent(
                        session_folder=str(session_dir),
                        skills_dir=str(skills_dir),
                        auto_save=True,
                    )
                except Exception as e:
                    print(f"⚠️  Subtask extraction failed: {e}")
                    import traceback

                    traceback.print_exc()
                    subtask_analysis = {
                        "status": "failed",
                        "error": str(e),
                    }
            elif not self.enable_skills and session_dir and verification.get("success"):
                # Skills disabled - skip extraction
                subtask_analysis = {
                    "status": "skipped",
                    "reason": "skills_disabled",
                }
                print(f"\n⚠️  Skills disabled: Skipping subtask extraction\n")
            elif session_dir:
                subtask_analysis = {
                    "status": "skipped",
                    "reason": "task_not_successful",
                }

            result = {
                'task_id': task_id,
                'task_description': task_description,
                'website': website,
                'skills_dir': str(skills_dir),
                'attempt': attempt,
                'success': verification['success'],
                'verification': verification,
                'reasoning': verification['reasoning'],
                'suggestions': verification.get('suggestions', ''),
                'agent_response': agent_response,
                'session_dir': str(session_dir) if session_dir else None,
                'summary_path': str(summary_path) if summary_path else None,
                'subtask_analysis': subtask_analysis,
                'started_at': started_at,
                'finished_at': get_timestamp_iso(),
            }
            if session_dir:
                debug_path = Path(session_dir) / "webjudge_debug.json"
                result["webjudge_debug_path"] = (
                    str(debug_path) if debug_path.exists() else None
                )
            else:
                result["webjudge_debug_path"] = None

            # Update summary after verification/analysis
            if session_dir:
                summary_path = (
                    Path(result["summary_path"])
                    if result.get("summary_path")
                    else (session_dir / "summary.json")
                )
                summary = compute_session_summary(
                    session_dir=session_dir,
                    skills_dir=skills_dir,
                    task_id=str(task_id),
                )
                summary["website"] = website
                summary["start_url"] = start_url
                summary["attempt"] = attempt
                summary["verification"] = verification
                summary["subtask_analysis"] = result.get("subtask_analysis")
                summary["subtasks_available_before"] = subtasks_before
                summary["subtasks_available_after"] = (
                    count_skills_in_dir(skills_dir)
                    if any(skills_dir.glob("*/SKILL.md"))
                    else count_subtasks_in_dir(skills_dir)
                )
                summary["phase"] = "final"
                summary["generated_at"] = get_timestamp_iso()

                summary_path.write_text(
                    json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                result["summary_path"] = str(summary_path)

                # Update per-website cumulative subtask success stats
                try:
                    update_cumulative_subtask_stats(
                        stats_path=(skills_dir / "subtask_stats.json"),
                        website=website,
                        session_subtask_stats=summary.get("subtask_stats", []),
                    )
                except Exception:
                    pass

                # Update in-memory aggregate for this run
                website_bucket = self.aggregate["websites"].setdefault(
                    website,
                    {
                        "tasks": 0,
                        "attempts": 0,
                        "reuse_ratio_actions": [],
                        "reuse_ratio_calls": [],
                        "subtasks": {},
                    },
                )
                website_bucket["attempts"] += 1
                if verification.get("success"):
                    website_bucket["tasks"] += 1

                reuse = (
                    summary.get("reuse", {})
                    if isinstance(summary, dict)
                    else {}
                )
                if reuse.get("reuse_ratio_actions") is not None:
                    website_bucket["reuse_ratio_actions"].append(
                        reuse.get("reuse_ratio_actions")
                    )
                if reuse.get("reuse_ratio_calls") is not None:
                    website_bucket["reuse_ratio_calls"].append(
                        reuse.get("reuse_ratio_calls")
                    )

                for s in summary.get("subtask_stats", []) or []:
                    if not isinstance(s, dict):
                        continue
                    subtask_id = str(s.get("subtask_id", "unknown"))
                    st = website_bucket["subtasks"].setdefault(
                        subtask_id,
                        {
                            "subtask_id": subtask_id,
                            "subtask_name": s.get("subtask_name", ""),
                            "calls_total": 0,
                            "success": 0,
                            "partial_success": 0,
                            "error": 0,
                            "other": 0,
                        },
                    )
                    st["subtask_name"] = s.get(
                        "subtask_name", st.get("subtask_name", "")
                    )
                    for key in (
                        "calls_total",
                        "success",
                        "partial_success",
                        "error",
                        "other",
                    ):
                        st[key] = int(st.get(key, 0) or 0) + int(
                            s.get(key, 0) or 0
                        )

                for st in website_bucket["subtasks"].values():
                    calls_total = int(st.get("calls_total", 0) or 0)
                    if calls_total:
                        st["success_rate"] = (
                            int(st.get("success", 0) or 0) / calls_total
                        )
                        st["failure_rate"] = (
                            int(st.get("partial_success", 0) or 0)
                            + int(st.get("error", 0) or 0)
                        ) / calls_total
                    else:
                        st["success_rate"] = 0.0
                        st["failure_rate"] = 0.0

            return result

        except asyncio.TimeoutError as e:
            print(f"⏱️  Task execution timeout: {e}")
            traceback.print_exc()

            return {
                'task_id': task_id,
                'attempt': attempt,
                'success': False,
                'error': f'TimeoutError: {e}',
                'is_timeout': True,
                'website': website,
                'skills_dir': str(skills_dir),
                'session_dir': str(session_log_dir)
                if session_log_dir is not None
                else None,
                'traceback': traceback.format_exc(),
                'started_at': started_at,
                'finished_at': get_timestamp_iso(),
            }

        except Exception as e:
            print(f"❌ Task execution failed: {e}")
            traceback.print_exc()

            return {
                'task_id': task_id,
                'attempt': attempt,
                'success': False,
                'error': str(e),
                'website': website,
                'skills_dir': str(skills_dir),
                'session_dir': str(session_log_dir)
                if session_log_dir is not None
                else None,
                'traceback': traceback.format_exc(),
                'started_at': started_at,
                'finished_at': get_timestamp_iso(),
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
        task_id = task.get('id', 'unknown')
        task_description = task.get('ques', '')
        website = (task.get('web_name') or '').strip()
        if not website:
            return {
                "task_id": task_id,
                "task_description": task_description,
                "website": website or None,
                "attempt": 0,
                "total_attempts": 0,
                "retry_count": 0,
                "success": False,
                "error": "Missing required field: web_name",
                "attempt_history": [],
            }

        attempt = 1
        suggestions = ""
        attempt_history = []  # Track all attempts

        while attempt <= self.max_retries + 1:
            if not self._reserve_website_attempt(website):
                used = self._website_attempts_used(website)
                attempt_history.append(
                    {
                        "attempt_number": attempt,
                        "status": "skipped",
                        "success": False,
                        "skip_reason": "website_attempt_cap_reached",
                        "website_attempts_used": used,
                        "website_attempt_limit": self.max_attempts_per_website,
                    }
                )
                return {
                    "task_id": task_id,
                    "task_description": task_description,
                    "website": website,
                    "attempt": 0,
                    "total_attempts": attempt - 1,
                    "retry_count": max(0, attempt - 1),
                    "success": False,
                    "skipped": True,
                    "skip_reason": "website_attempt_cap_reached",
                    "website_attempts_used": used,
                    "website_attempt_limit": self.max_attempts_per_website,
                    "attempt_history": attempt_history,
                }

            suggestions_used = suggestions
            result = await self.run_single_task(task, attempt, suggestions)

            # Record this attempt in history
            attempt_history.append(
                {
                    'attempt_number': attempt,
                    'status': (
                        "success" if result.get("success") else "failed"
                    ),
                    'success': result.get('success', False),
                    'verification': result.get('verification', None),
                    'reasoning': result.get('reasoning', ''),
                    'suggestions': result.get('suggestions', ''),
                    'error': result.get('error', ''),
                    'traceback': result.get('traceback', ''),
                    'session_dir': result.get('session_dir', ''),
                    'summary_path': result.get('summary_path', ''),
                    'webjudge_debug_path': result.get(
                        'webjudge_debug_path', ''
                    ),
                    'agent_response': result.get('agent_response', ''),
                    'is_timeout': result.get('is_timeout', False),
                    'previous_suggestions': suggestions_used,
                    'started_at': result.get('started_at', ''),
                    'finished_at': result.get('finished_at', ''),
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
                else:
                    print(
                        f"\n🔄 Task failed. Retrying (attempt {attempt + 1}/{self.max_retries + 1})..."
                    )
                attempt += 1
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
        print(
            f"Max attempts per task: {self.max_retries + 1} (max_retries={self.max_retries})"
        )
        print(
            f"Max attempts per website: {self.max_attempts_per_website}"
        )
        if self.website_filter:
            print(f"Website filter: {self.website_filter}")
        print(f"Skills root: {self.skills_root}")
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

            # Wait 2 seconds before next task
            if (
                idx < len(tasks) + start_index - 1
            ):  # Don't wait after last task
                print("\n⏳ Waiting 2 seconds before next task...")
                await asyncio.sleep(2)
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
            "skills_root": str(self.skills_root),
            "skills_dir": str(self.skills_dir_override)
            if self.skills_dir_override is not None
            else None,
            "website_filter": self.website_filter or None,
            "max_attempts_per_task": self.max_retries + 1,
            "max_attempts_per_website": self.max_attempts_per_website,
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
                    "skipped": task_result.get("skipped", False),
                    "skip_reason": task_result.get("skip_reason", ""),
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
        "--skills-root",
        default=str(script_dir / "skills_store"),
        help="Root directory for per-website skills.",
    )
    parser.add_argument(
        "--skills-dir",
        default="",
        help=(
            "Directory for a single website's skills (leaf). "
            "Use together with --website-filter to avoid accidental double nesting."
        ),
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
        "--max-attempts-per-task",
        type=int,
        default=5,
        help="Maximum total runs per task (including the first attempt).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help=(
            "DEPRECATED: Maximum retry attempts per task (total attempts = max_retries + 1). "
            "Overrides --max-attempts-per-task when set."
        ),
    )
    parser.add_argument(
        "--max-attempts-per-website",
        type=int,
        default=100,
        help="Maximum total runs per website (web_name) across all tasks.",
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
    parser.add_argument(
        "--disable-skills",
        action="store_true",
        help="Disable skill loading, usage, and generation (agent uses only browser tools)",
    )

    args = parser.parse_args()

    max_attempts_per_task = int(args.max_attempts_per_task)
    if max_attempts_per_task <= 0:
        parser.error("--max-attempts-per-task must be > 0")
    if args.max_retries is not None:
        if args.max_retries < 0:
            parser.error("--max-retries must be >= 0")
        max_attempts_per_task = int(args.max_retries) + 1

    max_retries = max(0, max_attempts_per_task - 1)

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
        skills_root=args.skills_root,
        skills_dir=args.skills_dir,
        website_filter=args.website_filter,
        max_retries=max_retries,
        max_attempts_per_website=args.max_attempts_per_website,
        run_summary_out=args.run_summary_out,
        results_out=args.results_out,
        run_dir=run_dir,
        step_timeout=None if args.step_timeout <= 0 else args.step_timeout,
        tool_execution_timeout=None
        if args.tool_timeout <= 0
        else args.tool_timeout,
        enable_skills=not args.disable_skills,
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
