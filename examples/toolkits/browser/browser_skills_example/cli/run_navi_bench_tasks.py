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
"""Run Navi-Bench tasks using the Browser Skills agent (CLI)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
EXAMPLE_ROOT = SCRIPT_DIR.parent

from examples.toolkits.browser.browser_skills_example.core.navi_bench_runner import (
    NaviBenchRunner,
    _resolve_run_dir,
    _select_items,
    load_dataset_items_from_jsonl,
)


async def _amain() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--jsonl",
        type=str,
        required=True,
        help="Path to a JSONL of navi-bench DatasetItem rows.",
    )
    parser.add_argument(
        "--skills-root",
        type=str,
        required=True,
        help="Root directory for per-website skills.",
    )
    parser.add_argument(
        "--skills-dir",
        type=str,
        default="",
        help="Optional leaf skills dir (requires --domain).",
    )
    parser.add_argument(
        "--domain",
        type=str,
        default="",
        help="Filter by DatasetItem.domain (e.g., google_flights).",
    )
    parser.add_argument(
        "--task-id", type=str, default="", help="Run a single task by task_id."
    )
    parser.add_argument(
        "--start", type=int, default=0, help="Start index for selected items."
    )
    parser.add_argument(
        "--max-tasks", type=int, default=0, help="Max tasks to run (0 = all)."
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="",
        help="Output dir root; creates a session_*/ folder inside.",
    )
    parser.add_argument("--cdp-port", type=int, default=9223)
    parser.add_argument("--max-attempts-per-task", type=int, default=5)
    parser.add_argument("--max-attempts-per-website", type=int, default=100)
    parser.add_argument("--step-timeout", type=float, default=600.0)
    parser.add_argument("--tool-timeout", type=float, default=180.0)
    parser.add_argument("--disable-skills", action="store_true")
    parser.add_argument("--disable-skill-extraction", action="store_true")
    args = parser.parse_args()

    jsonl_path = Path(args.jsonl).expanduser().resolve()
    run_dir = _resolve_run_dir(args.out_dir or None)

    os.environ.setdefault(
        "SKILL_MINING_IGNORE_ACTIONS", "console_exec,console_view"
    )

    items = load_dataset_items_from_jsonl(jsonl_path)
    selected = _select_items(
        items,
        domain_filter=args.domain,
        task_id=args.task_id,
        start=int(args.start or 0),
        max_tasks=(
            int(args.max_tasks) if int(args.max_tasks or 0) > 0 else None
        ),
    )
    if not selected:
        print(
            "No tasks selected. Check --domain/--task-id/--start/--max-tasks.",
            file=sys.stderr,
        )
        return 2

    print(f"Run dir: {run_dir}")
    print(f"Selected tasks: {len(selected)} (from {jsonl_path})")

    runner = NaviBenchRunner(
        skills_root=args.skills_root,
        skills_dir=args.skills_dir,
        domain_filter=args.domain,
        max_attempts_per_task=args.max_attempts_per_task,
        max_attempts_per_website=args.max_attempts_per_website,
        run_dir=run_dir,
        cdp_port=args.cdp_port,
        step_timeout=(None if args.step_timeout <= 0 else args.step_timeout),
        tool_execution_timeout=(
            None if args.tool_timeout <= 0 else args.tool_timeout
        ),
        enable_skills=not args.disable_skills,
        enable_skill_extraction=not args.disable_skill_extraction,
    )

    results: List[Dict[str, Any]] = []
    for item in selected:
        r = await runner.run_single_dataset_item(item)
        results.append(
            {
                "task_id": r.task_id,
                "domain": r.domain,
                "website": r.website,
                "attempt": r.attempt,
                "success": r.success,
                "score": r.score,
                "session_dir": r.session_dir,
                "eval_result_path": r.eval_result_path,
                "error": r.error,
            }
        )

    out_path = run_dir / "navi_bench_results.json"
    out_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"\nResults written to: {out_path}")
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
