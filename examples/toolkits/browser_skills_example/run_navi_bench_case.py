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
"""Run a single Navi-Bench case (thin wrapper over run_navi_bench_tasks.py)."""

import argparse
import asyncio
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from run_navi_bench_tasks import (
    NaviBenchRunner,
    _resolve_run_dir,
    _select_items,
    load_dataset_items_from_jsonl,
)


async def _amain() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl", type=str, required=True)
    parser.add_argument("--task-id", type=str, required=True)
    parser.add_argument("--skills-root", type=str, required=True)
    parser.add_argument("--skills-dir", type=str, default="")
    parser.add_argument("--out-dir", type=str, default="")
    parser.add_argument("--cdp-port", type=int, default=9223)
    parser.add_argument("--max-attempts-per-task", type=int, default=5)
    parser.add_argument("--max-attempts-per-website", type=int, default=100)
    parser.add_argument("--step-timeout", type=float, default=600.0)
    parser.add_argument("--tool-timeout", type=float, default=180.0)
    parser.add_argument("--disable-skills", action="store_true")
    parser.add_argument("--disable-skill-extraction", action="store_true")
    args = parser.parse_args()
    if not args.task_id.strip():
        print("--task-id must be a non-empty string.")
        return 2

    jsonl_path = Path(args.jsonl).expanduser().resolve()
    run_dir = _resolve_run_dir(args.out_dir or None)

    items = load_dataset_items_from_jsonl(jsonl_path)
    selected = _select_items(items, task_id=args.task_id)
    if not selected:
        print(f"Task not found: {args.task_id}")
        return 2

    runner = NaviBenchRunner(
        skills_root=args.skills_root,
        skills_dir=args.skills_dir,
        domain_filter=selected[0].domain,
        max_attempts_per_task=args.max_attempts_per_task,
        max_attempts_per_website=args.max_attempts_per_website,
        run_dir=run_dir,
        cdp_port=args.cdp_port,
        step_timeout=(None if args.step_timeout <= 0 else args.step_timeout),
        tool_execution_timeout=(None if args.tool_timeout <= 0 else args.tool_timeout),
        enable_skills=not args.disable_skills,
        enable_skill_extraction=not args.disable_skill_extraction,
    )

    result = await runner.run_single_dataset_item(selected[0])
    print("\n" + "=" * 80)
    print("FINAL RESULT")
    print("=" * 80)
    print(f"task_id: {result.task_id}")
    print(f"success: {result.success}")
    print(f"score:   {result.score}")
    print(f"attempt: {result.attempt}")
    print(f"session: {result.session_dir}")
    print(f"eval:    {result.eval_result_path}")
    if result.error:
        print(f"error:   {result.error}")
    if result.suggestions:
        print("\nlast suggestions:\n" + result.suggestions)
    return 0 if result.success else 1


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
