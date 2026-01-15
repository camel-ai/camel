#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
import json
import sys
from pathlib import Path

from skill_agent import SkillsAgent
from utils import (
    compute_session_summary,
    count_subtasks_in_dir,
    resolve_website_skills_dir,
)


def _find_newest_browser_log_file(browser_log_dir: Path) -> Path | None:
    candidates = sorted(
        [
            p
            for p in browser_log_dir.glob("hybrid_browser_toolkit_ws_*.log")
            if p.is_file()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _get_log_paths(agent: SkillsAgent) -> tuple[Path | None, Path | None]:
    session_dir = agent.session_log_dir
    if not session_dir:
        return None, None

    browser_log_dir = session_dir / "browser_log"
    newest_raw = (
        _find_newest_browser_log_file(browser_log_dir)
        if browser_log_dir.exists()
        else None
    )
    complete_log = session_dir / "complete_browser_log.log"
    return newest_raw, complete_log if complete_log.exists() else None


async def _amain() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a single browser task with"
            "SkillsAgent and write session logs."
        ),
    )
    parser.add_argument(
        "--skills-dir",
        default="",
        help="Directory containing *_subtasks.json (legacy; overrides --skills-root).",
    )
    parser.add_argument(
        "--skills-root",
        default="",
        help="Root directory for skills, will use a per-website subfolder.",
    )
    parser.add_argument("--web-name", required=True, help="Website name.")
    parser.add_argument("--web", default="", help="Start URL.")
    parser.add_argument(
        "--task",
        required=True,
        help="User task text (what to do on the website).",
    )
    parser.add_argument(
        "--task-id",
        default="",
        help="Optional task identifier for summary output.",
    )
    parser.add_argument(
        "--cdp-port",
        type=int,
        default=9223,
        help="Chrome DevTools Protocol port (default: 9223).",
    )
    parser.add_argument(
        "--step-timeout",
        type=float,
        default=180.0,
        help="ChatAgent step timeout in seconds (0 disables). Default: 180.",
    )
    parser.add_argument(
        "--tool-timeout",
        type=float,
        default=180.0,
        help="Per-tool execution timeout in seconds (0 disables). Default: 180.",
    )
    parser.add_argument(
        "--no-recovery",
        action="store_true",
        help="Disable agent recovery during subtask replay.",
    )
    parser.add_argument(
        "--quiet-meta",
        action="store_true",
        help="Do not print session/log path summary lines.",
    )
    parser.add_argument(
        "--summary-out",
        default="",
        help="Write a JSON summary to this path (default: <session_dir>/summary.json).",
    )

    args = parser.parse_args()

    website = args.web_name.strip()
    if args.skills_dir.strip():
        skills_dir = Path(args.skills_dir)
        skills_dir.mkdir(parents=True, exist_ok=True)
    elif args.skills_root.strip():
        skills_root = Path(args.skills_root)
        skills_root.mkdir(parents=True, exist_ok=True)
        skills_dir = resolve_website_skills_dir(skills_root, website)
    else:
        print(
            "Must provide either --skills-root or --skills-dir",
            file=sys.stderr,
        )
        return 2

    agent = SkillsAgent(
        skills_dir=str(skills_dir),
        cdp_port=args.cdp_port,
        use_agent_recovery=not args.no_recovery,
        website=website,
        start_url=args.web.strip() or None,
        step_timeout=None if args.step_timeout <= 0 else args.step_timeout,
        tool_execution_timeout=None
        if args.tool_timeout <= 0
        else args.tool_timeout,
    )

    ok = await agent.initialize()
    if not ok:
        print("Failed to initialize agent", file=sys.stderr)
        return 2

    try:
        subtasks_before = count_subtasks_in_dir(skills_dir)
        raw_before, full_before = _get_log_paths(agent)
        await agent.run(args.task)
        if agent.toolkit:
            try:
                await agent.toolkit.capture_final_evidence()
            except Exception:
                pass
        agent.save_communication_log()

        if not agent.session_log_dir:
            print("No session_log_dir found after run", file=sys.stderr)
            return 3

        subtasks_after = count_subtasks_in_dir(skills_dir)
        raw_after, full_after = _get_log_paths(agent)

        summary = compute_session_summary(
            session_dir=agent.session_log_dir,
            skills_dir=skills_dir,
            task_id=args.task_id.strip() or None,
        )
        summary["website"] = website
        summary["start_url"] = args.web.strip() or None
        summary["subtasks_available_before"] = subtasks_before
        summary["subtasks_available_after"] = subtasks_after

        if args.summary_out.strip():
            summary_path = Path(args.summary_out).expanduser()
            summary_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            summary_path = agent.session_log_dir / "summary.json"

        summary_path.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        if not args.quiet_meta:
            print(f"Session dir: {agent.session_log_dir}")
            print(f"Raw browser log before: {raw_before or ''}")
            print(f"Raw browser log after: {raw_after or ''}")
            print(f"Full log before: {full_before or ''}")
            print(f"Full log after: {full_after or ''}")
            print(f"Summary JSON: {summary_path}")
        return 0
    finally:
        await agent.close()


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
