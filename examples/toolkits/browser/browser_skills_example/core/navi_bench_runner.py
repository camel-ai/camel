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
"""Run Navi-Bench tasks using the Browser Skills agent (with online evaluator).

Flow (aligned with WebVoyager runner):
1) Run one task case (SkillsAgent)
2) Verify once via navi-bench evaluator (per-step update + final compute)
3) If success: mine skill from the session timeline
4) If fail: retry (per-task <= 5, per-website <= 100)

Important:
- Evaluator JS execution is done via *quiet* ws_wrapper calls and is NOT exposed
  as tools to the agent.
- Skill mining filters out evaluator-only console actions to avoid pollution.
"""

import json
import time
import traceback

from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from navi_bench.base import DatasetItem, instantiate


from examples.toolkits.browser.utils.utils import (
    compute_session_summary,
    count_skills_in_dir,
    count_subtasks_in_dir,
    get_timestamp_iso,
    resolve_website_skills_dir,
    resolve_run_dir,
)

from examples.toolkits.browser.utils.navi_bench_eval_hook import (
    NaviBenchEvalStats,
    navi_bench_on_action_update,
)
from examples.toolkits.browser.utils.navi_bench_common import (
    AttemptResult,
    safe_name,
    pydantic_dump,
    score_from_result,
    extract_token_usage_from_payload,
    normalize_website_key,
    domain_to_website,
    WebJudgeTaskVerifier,
)

from .skill_agent import SkillsAgent
from .subtask_extractor import analyze_with_agent
from .modeling import DEFAULT_MODEL_PLATFORM, DEFAULT_MODEL_TYPE

load_dotenv()

class NaviBenchRunner:
    def __init__(
        self,
        *,
        skills_root: str,
        skills_dir: str = "",
        domain_filter: str = "",
        max_attempts_per_task: int = 5,
        max_attempts_per_website: int = 100,
        run_dir: Optional[Path] = None,
        cdp_port: int = 9223,
        step_timeout: float | None = None,
        tool_execution_timeout: float | None = None,
        enable_skills: bool = True,
        enable_skill_extraction: bool = True,
    ) -> None:
        resolved_root = skills_root.strip()
        if not resolved_root:
            raise ValueError("skills_root must be a non-empty path.")
        self.skills_root = Path(resolved_root).expanduser()
        self.skills_dir_override = (
            Path(skills_dir).expanduser().resolve()
            if skills_dir.strip()
            else None
        )
        self.domain_filter = domain_filter.strip()

        self.max_attempts_per_task = int(max_attempts_per_task)
        if self.max_attempts_per_task <= 0:
            raise ValueError("max_attempts_per_task must be > 0.")
        self.max_attempts_per_website = int(max_attempts_per_website)
        if self.max_attempts_per_website <= 0:
            raise ValueError("max_attempts_per_website must be > 0.")

        self.run_dir = run_dir
        self.cdp_port = int(cdp_port)
        self.step_timeout = step_timeout
        self.tool_execution_timeout = tool_execution_timeout
        self.enable_skills = enable_skills
        self.enable_skill_extraction = enable_skill_extraction
        
        # Initialize WebJudge verifier
        self.webjudge_verifier = WebJudgeTaskVerifier(
            model_platform=DEFAULT_MODEL_PLATFORM,
            model_type=DEFAULT_MODEL_TYPE,
        )

        self._website_attempt_counts: Dict[str, int] = {}

        if self.skills_dir_override is not None:
            # Only safe if user runs a single-domain slice.
            if not self.domain_filter:
                raise ValueError(
                    "skills_dir can only be used together with --domain "
                    "(because Navi-Bench tasks can span multiple websites)."
                )
            self.skills_dir_override.mkdir(parents=True, exist_ok=True)
        else:
            self.skills_root.mkdir(parents=True, exist_ok=True)

    def _website_attempts_used(self, website: str) -> int:
        return int(
            self._website_attempt_counts.get(
                normalize_website_key(website), 0
            )
            or 0
        )

    def _reserve_website_attempt(self, website: str) -> bool:
        key = normalize_website_key(website)
        used = int(self._website_attempt_counts.get(key, 0) or 0)
        if used >= self.max_attempts_per_website:
            return False
        self._website_attempt_counts[key] = used + 1
        return True

    def _resolve_skills_dir_for_task(self, website: str) -> Path:
        if self.skills_dir_override is not None:
            return self.skills_dir_override
        return resolve_website_skills_dir(self.skills_root, website)

    async def run_single_dataset_item(
        self, item: DatasetItem
    ) -> AttemptResult:
        task_id = item.task_id
        domain = (item.domain or "").strip()
        website = domain_to_website(domain)
        skills_dir = self._resolve_skills_dir_for_task(website)

        subtasks_before = (
            count_skills_in_dir(skills_dir)
            if any(skills_dir.glob("*/SKILL.md"))
            else count_subtasks_in_dir(skills_dir)
        )

        task_config = item.generate_task_config()
        evaluator = instantiate(task_config.eval_config)

        previous_suggestions = ""

        for attempt in range(1, self.max_attempts_per_task + 1):
            if not self._reserve_website_attempt(website):
                return AttemptResult(
                    task_id=task_id,
                    domain=domain,
                    website=website,
                    attempt=attempt,
                    success=False,
                    score=None,
                    eval_result_path=None,
                    session_dir=None,
                    error=(
                        f"Per-website attempt cap reached for {website!r}: "
                        f"{self.max_attempts_per_website}"
                    ),
                )

            print("\n" + "=" * 80)
            print(
                f"NAVI-BENCH TASK: {task_id} | domain={domain} | website={website} "
                f"| attempt {attempt}/{self.max_attempts_per_task} "
                f"(website attempts used: {self._website_attempts_used(website)}/{self.max_attempts_per_website})"
            )
            print("=" * 80)
            print(f"Start URL: {task_config.url}")
            print(f"Task: {task_config.task}")
            if previous_suggestions:
                print("\nPrevious attempt notes:\n" + previous_suggestions)

            session_log_dir = None
            if self.run_dir is not None:
                session_log_dir = (
                    Path(self.run_dir)
                    / f"task_{safe_name(task_id)}_attempt_{attempt}"
                )

            agent = SkillsAgent(
                skills_dir=str(skills_dir),
                website=website,
                session_log_dir=session_log_dir,
                start_url=task_config.url,
                use_agent_recovery=True,
                step_timeout=self.step_timeout,
                tool_execution_timeout=self.tool_execution_timeout,
                enable_skills=self.enable_skills,
            )

            score: Optional[float] = None
            eval_result_path: Optional[str] = None
            session_dir: Optional[Path] = None
            attempt_start_time = time.perf_counter()

            try:
                ok = await agent.initialize()
                if not ok:
                    raise RuntimeError("Failed to initialize agent")

                if agent.toolkit is None:
                    raise RuntimeError("Agent toolkit is not initialized")

                # Ensure we always have a session directory even if the attempt crashes
                # before `agent.run(...)` returns (e.g., LLM step timeout).
                session_dir = agent.session_log_dir
                if session_dir is None:
                    raise RuntimeError("Missing agent.session_log_dir")

                # Register evaluator hook at the ws_wrapper layer.
                ws_wrapper = await agent.toolkit._get_ws_wrapper()
                eval_stats = NaviBenchEvalStats()

                async def _hook(
                    event: Dict[str, Any],
                    *,
                    ws_wrapper=ws_wrapper,
                    eval_stats=eval_stats,
                    evaluator=evaluator,
                ) -> None:
                    await navi_bench_on_action_update(
                        evaluator=evaluator,
                        ws_wrapper=ws_wrapper,
                        event=event,
                        stats=eval_stats,
                    )

                # Evaluator reset (record timing for debug).
                t_reset0 = time.time()
                await evaluator.reset()
                eval_stats.reset_calls += 1
                eval_stats.reset_time_s += time.time() - t_reset0
                ws_wrapper.set_action_hook(_hook)

                full_task = task_config.task
                if previous_suggestions:
                    full_task += (
                        "\n\n**IMPORTANT NOTES FROM PREVIOUS ATTEMPT:**\n"
                        f"{previous_suggestions}"
                    )

                response = await agent.run(full_task)

                # Best-effort: capture evidence.
                try:
                    await agent.toolkit.capture_final_evidence()
                except Exception as e:
                    print(f"⚠️  Could not capture final evidence: {e}")
                
                # Get agent's response content
                agent_response = "Task completed."
                if response and response.msgs:
                    agent_response = response.msgs[-1].content or "Task completed."
                elif agent.agent_communication_log:
                    last_entry = agent.agent_communication_log[-1]
                    agent_response = last_entry.get("assistant_response", "Task completed.")
                
                # WebJudge verification (vision-based)
                print(f"\n{'=' * 80}")
                print("🔍 WEBJUDGE VERIFICATION")
                print(f"{'=' * 80}")
                
                webjudge_result = self.webjudge_verifier.verify_task(
                    full_task,
                    agent_response,
                    session_dir=session_dir,
                    website=website,
                )
                
                print("\n✓ WebJudge verification complete:")
                print(f"  Success: {webjudge_result.success}")
                print(f"  Reasoning: {webjudge_result.reasoning}")
                print(f"  Execution time: {webjudge_result.execution_time:.2f}s")
                print(f"  Tokens used: {webjudge_result.token_usage['total']}")
                if webjudge_result.suggestions:
                    print(f"  Suggestions: {webjudge_result.suggestions}")

                # Navi-Bench evaluation (original programmatic evaluator)
                print(f"\n{'=' * 80}")
                print("🧪 NAVI-BENCH EVALUATION")
                print(f"{'=' * 80}")
                
                # Best-effort: force a final update before compute.
                final_url = ""
                try:
                    tabs = await ws_wrapper.get_tab_info_quiet()
                    for tab in tabs:
                        if isinstance(tab, dict) and tab.get("is_current"):
                            final_url = str(tab.get("url") or "")
                            break
                except Exception:
                    final_url = ""

                try:
                    await navi_bench_on_action_update(
                        evaluator=evaluator,
                        ws_wrapper=ws_wrapper,
                        event={"current_url": final_url},
                        stats=eval_stats,
                    )
                except Exception:
                    pass

                t_compute0 = time.time()
                eval_result = await evaluator.compute()
                eval_stats.compute_calls += 1
                eval_stats.compute_time_s += time.time() - t_compute0
                score = score_from_result(eval_result)
                navi_bench_success = bool(score is not None and abs(score - 1.0) < 1e-9)

                if eval_stats.llm_usage is None:
                    eval_stats.llm_usage = extract_token_usage_from_payload(
                        pydantic_dump(eval_result)
                    )

                llm_usage_source = "extracted"
                if eval_stats.llm_usage is None:
                    # Navi-Bench evaluators in this repo are typically programmatic.
                    # When no usage is exposed, treat it as 0 tokens for reporting.
                    llm_usage_source = "assumed_zero"
                    eval_stats.llm_usage = {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                    }

                # Always clear hook once attempt ends.
                ws_wrapper.set_action_hook(None)

                # Save communication log + timeline (calls analyze_session).
                agent.save_communication_log()
                agent.save_memory()

                # Write attempt summary (pre-extract) for debugging.
                summary = compute_session_summary(
                    session_dir=session_dir,
                    skills_dir=skills_dir,
                    task_id=str(task_id),
                )
                summary["website"] = website
                summary["domain"] = domain
                summary["start_url"] = task_config.url
                summary["attempt"] = attempt
                summary["subtasks_available_before"] = subtasks_before
                summary["subtasks_available_after"] = (
                    count_skills_in_dir(skills_dir)
                    if any(skills_dir.glob("*/SKILL.md"))
                    else count_subtasks_in_dir(skills_dir)
                )
                summary["phase"] = "post_run_pre_extract"
                summary["generated_at"] = get_timestamp_iso()
                summary["attempt_runtime_seconds"] = time.perf_counter() - attempt_start_time
                (session_dir / "summary.json").write_text(
                    json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )

                # Write evaluator result.success is the navi_bench success indicator.
                eval_payload = {
                    "task_id": task_id,
                    "domain": domain,
                    "website": website,
                    "attempt": attempt,
                    "attempt_runtime_seconds": time.perf_counter() - attempt_start_time,
                    "score": score,
                    "success": navi_bench_success,
                    "final_url": final_url,
                    "raw_result": pydantic_dump(eval_result),
                    "navi_bench_evaluator_stats": {
                        "reset_calls": eval_stats.reset_calls,
                        "update_calls": eval_stats.update_calls,
                        "compute_calls": eval_stats.compute_calls,
                        "reset_time_s": eval_stats.reset_time_s,
                        "update_time_s": eval_stats.update_time_s,
                        "compute_time_s": eval_stats.compute_time_s,
                        "js_evaluate_calls": eval_stats.js_evaluate_calls,
                        "js_evaluate_time_s": eval_stats.js_evaluate_time_s,
                        "js_code_chars_total": eval_stats.js_code_chars_total,
                        "js_code_chars_max": eval_stats.js_code_chars_max,
                        "last_error": eval_stats.last_error,
                        "llm_usage": eval_stats.llm_usage,
                        "llm_usage_source": llm_usage_source,
                    },
                    "webjudge_evaluation": {
                        "success": webjudge_result.success,
                        "reasoning": webjudge_result.reasoning,
                        "suggestions": webjudge_result.suggestions,
                        "execution_time": webjudge_result.execution_time,
                        "token_usage": webjudge_result.token_usage,
                        "key_points": webjudge_result.key_points,
                        "evidence_count": len(webjudge_result.evidence),
                        "debug_path": webjudge_result.debug_path,
                    },
                }
                eval_path = session_dir / "navi_bench_eval_result.json"
                eval_path.write_text(
                    json.dumps(eval_payload, indent=2, ensure_ascii=False)
                    + "\n",
                    encoding="utf-8",
                )
                eval_result_path = str(eval_path)

                # Print evaluator stats for visibility.
                llm_usage = eval_stats.llm_usage or {}
                tokens_hint = llm_usage.get("total_tokens")
                if tokens_hint is None:
                    tokens_hint = llm_usage.get("prompt_tokens")
                if tokens_hint is None:
                    tokens_hint = llm_usage.get("input_tokens")
                print(
                    "\n🧪 Navi-Bench evaluator stats: "
                    f"updates={eval_stats.update_calls} "
                    f"js_eval={eval_stats.js_evaluate_calls} "
                    f"update_time={eval_stats.update_time_s:.2f}s "
                    f"compute_time={eval_stats.compute_time_s:.2f}s "
                    f"llm_tokens={tokens_hint!r}"
                )
                
                # Print comparison
                print(f"\n{'=' * 80}")
                print("📊 EVALUATION COMPARISON")
                print(f"{'=' * 80}")
                print(f"Navi-Bench: {'✅ Success' if navi_bench_success else '❌ Failed'} (score={score})")
                print(f"WebJudge:   {'✅ Success' if webjudge_result.success else '❌ Failed'}")
                if navi_bench_success != webjudge_result.success:
                    print("⚠️  Evaluators disagree on task success!")
                print(f"{'=' * 80}\n")

                # Close browser after evaluation.
                print("\n🧹 Closing browser...")
                try:
                    await agent.toolkit.browser_close()
                    print("✓ Browser closed successfully")
                except Exception as e:
                    print(f"⚠️  Browser close failed: {e}")

                # At least one evaluator says success: accept it. the webjudge_result to make skill generation easier.
                # Navi-Bench score is recorded for evalution purposes.
                if webjudge_result.success or navi_bench_success:
                    print("\n✅ WebJudge verified successful.")
                    if self.enable_skill_extraction:
                        try:
                            analyze_with_agent(
                                session_folder=str(session_dir),
                                skills_dir=str(skills_dir),
                                auto_save=True,
                            )
                        except Exception as e:
                            print(f"⚠️  Skill extraction failed: {e}")
                    else:
                        print(
                            "⚠️  Skill extraction disabled: skipping skill mining."
                        )
                if navi_bench_success:
                    return AttemptResult(
                        task_id=task_id,
                        domain=domain,
                        website=website,
                        attempt=attempt,
                        success=True,
                        score=score,
                        eval_result_path=eval_result_path,
                        session_dir=str(session_dir),
                    )
                
                # If Navi-Bench says success but WebJudge disagrees, use WebJudge's reasoning
                suggestions_parts: List[str] = []
                if not webjudge_result.success:
                    print("\n⚠️WebJudge failed.")
                    print(f"WebJudge reasoning: {webjudge_result.reasoning}")
                    suggestions_parts.append(webjudge_result.suggestions or "")
                suggestions_parts.append(
                    "- End the attempt on the relevant final page/state and avoid navigating away right before stopping."
                )
                previous_suggestions = "\n".join(suggestions_parts).strip()
                print("\n❌ Navi Bench Verified failed.")
                print(f"score={score!r}")
                print("Notes for retry:\n" + previous_suggestions)

            except Exception as e:
                err = f"{type(e).__name__}: {e}"
                print("\n💥 Attempt crashed:", err)
                traceback.print_exc()

                # Best-effort: clear hook if possible.
                try:
                    if agent.toolkit is not None:
                        ws_wrapper = await agent.toolkit._get_ws_wrapper()
                        ws_wrapper.set_action_hook(None)
                except Exception:
                    pass

                # Best-effort: save logs and close browser.
                try:
                    agent.save_communication_log()
                    agent.save_memory()
                except Exception:
                    pass
                try:
                    if agent.toolkit is not None:
                        await agent.toolkit.browser_close()
                except Exception:
                    pass

                previous_suggestions = (
                    "- The previous attempt crashed. Retry with simpler steps, "
                    "and if the site is stuck, try refreshing or reopening the page."
                )

                # CRITICAL: Write fallback JSON files even on crash
                if session_dir is not None:
                    crash_path = session_dir / "navi_bench_crash.txt"
                    crash_path.write_text(err + "\n" + traceback.format_exc(), encoding="utf-8")
                    
                    # Write fallback summary.json
                    try:
                        crash_summary = {
                            "task_id": str(task_id),
                            "website": website,
                            "domain": domain,
                            "start_url": task_config.url,
                            "attempt": attempt,
                            "attempt_runtime_seconds": time.perf_counter() - attempt_start_time,
                            "subtasks_available_before": subtasks_before,
                            "phase": "crashed",
                            "generated_at": get_timestamp_iso(),
                            "error": err,
                            "error_type": type(e).__name__,
                        }
                        (session_dir / "summary.json").write_text(
                            json.dumps(crash_summary, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8",
                        )
                    except Exception as write_err:
                        print(f"⚠️  Failed to write crash summary.json: {write_err}")
                    
                    # Write fallback navi_bench_eval_result.json
                    try:
                        crash_eval = {
                            "task_id": task_id,
                            "domain": domain,
                            "website": website,
                            "attempt": attempt,
                            "attempt_runtime_seconds": time.perf_counter() - attempt_start_time,
                            "score": None,
                            "success": False,
                            "final_url": "",
                            "error": err,
                            "error_type": type(e).__name__,
                            "raw_result": None,
                            "navi_bench_evaluator_stats": {
                                "error": "Attempt crashed before evaluation"
                            },
                            "webjudge_evaluation": {
                                "success": False,
                                "reasoning": f"Attempt crashed: {err}",
                                "suggestions": previous_suggestions,
                                "execution_time": 0.0,
                                "token_usage": {"prompt": 0, "completion": 0, "total": 0},
                                "key_points": [],
                                "evidence_count": 0,
                                "debug_path": "",
                            },
                        }
                        (session_dir / "navi_bench_eval_result.json").write_text(
                            json.dumps(crash_eval, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8",
                        )
                    except Exception as write_err:
                        print(f"⚠️  Failed to write crash navi_bench_eval_result.json: {write_err}")

        return AttemptResult(
            task_id=task_id,
            domain=domain,
            website=website,
            attempt=self.max_attempts_per_task,
            success=False,
            score=score,
            eval_result_path=eval_result_path,
            session_dir=str(session_dir) if session_dir else None,
            error="Max attempts per task reached",
            suggestions=previous_suggestions,
        )

    @staticmethod
    def resolve_run_dir(out_dir: Optional[str]) -> Path:
        return resolve_run_dir(out_dir, base_file=__file__)


__all__ = [
    "NaviBenchRunner",
]
