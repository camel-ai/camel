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
"""Run WebVoyager tasks with Browser Skills agent (CLI)."""

from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
EXAMPLE_ROOT = SCRIPT_DIR.parent

from examples.toolkits.browser.browser_skills_example.core.webvoyager_runner import (
    WebVoyagerRunner,
)
from examples.toolkits.browser.utils.utils import get_timestamp_filename


def _default_webvoyager_jsonl(example_root: Path) -> str:
    candidates = [
        example_root.parent / "data" / "WebVoyager_data.jsonl",
        Path.home() / "Downloads" / "WebVoyager_data_08312025_updated.jsonl",
    ]
    picked = next((p for p in candidates if p.exists()), candidates[0])
    return str(picked)


async def _amain() -> int:
    default_session_logs_root = EXAMPLE_ROOT / "session_logs"

    parser = argparse.ArgumentParser(
        description="Run WebVoyager tasks with subtask agent"
    )
    parser.add_argument(
        "--jsonl",
        default=_default_webvoyager_jsonl(EXAMPLE_ROOT),
        help="Path to WebVoyager JSONL file",
    )
    parser.add_argument(
        "--skills-root",
        default=str(EXAMPLE_ROOT / "skills_store"),
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
        default=600.0,
        help="ChatAgent step timeout in seconds (0 disables). Default: 600.",
    )
    parser.add_argument(
        "--tool-timeout",
        type=float,
        default=600.0,
        help="Per-tool execution timeout in seconds (0 disables). Default: 600.",
    )
    parser.add_argument(
        "--disable-skills",
        action="store_true",
        help="Disable skill loading/usage/mining; run with only atomic tools.",
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
    parser.add_argument("--auto-save-skills", action="store_true")

    args = parser.parse_args()

    max_attempts_per_task = int(args.max_attempts_per_task)
    if max_attempts_per_task <= 0:
        parser.error("--max-attempts-per-task must be > 0")
    if args.max_retries is not None:
        if args.max_retries < 0:
            parser.error("--max-retries must be >= 0")
        max_attempts_per_task = int(args.max_retries) + 1

    max_retries = max(0, max_attempts_per_task - 1)

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

    session_dir_pattern = re.compile(r"^session_\\d{8}_\\d{6}$")
    if session_dir_pattern.match(out_root.name):
        run_dir = out_root
    else:
        run_dir = out_root / f"session_{get_timestamp_filename()}"
    run_dir.mkdir(parents=True, exist_ok=True)

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
        auto_save_skills=args.auto_save_skills,
    )

    await runner.run_all_tasks(
        start_index=args.start, max_tasks=args.max_tasks
    )
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
