#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import asyncio
import sys
from pathlib import Path

from subtask_agent_example import SubtaskAgent


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


def _get_log_paths(agent: SubtaskAgent) -> tuple[Path | None, Path | None]:
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
            "SubtaskAgent and write session logs."
        ),
    )
    parser.add_argument(
        "--skills-dir",
        required=True,
        help=(
            "Directory containing *_subtasks.json (can be empty on first run)."
        ),
    )
    parser.add_argument("--web-name", required=True, help="Website name.")
    parser.add_argument("--web", default="", help="Start URL.")
    parser.add_argument(
        "--task",
        required=True,
        help="User task text (what to do on the website).",
    )
    parser.add_argument(
        "--cdp-port",
        type=int,
        default=9223,
        help="Chrome DevTools Protocol port (default: 9223).",
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

    args = parser.parse_args()

    skills_dir = Path(args.skills_dir)
    skills_dir.mkdir(parents=True, exist_ok=True)

    agent = SubtaskAgent(
        subtask_config_dir=str(skills_dir),
        cdp_port=args.cdp_port,
        use_agent_recovery=not args.no_recovery,
        website=args.web_name.strip(),
        start_url=args.web.strip() or None,
    )

    ok = await agent.initialize()
    if not ok:
        print("Failed to initialize agent", file=sys.stderr)
        return 2

    try:
        raw_before, full_before = _get_log_paths(agent)
        await agent.run(args.task)
        agent.save_communication_log()

        if not agent.session_log_dir:
            print("No session_log_dir found after run", file=sys.stderr)
            return 3

        raw_after, full_after = _get_log_paths(agent)

        if not args.quiet_meta:
            print(f"Session dir: {agent.session_log_dir}")
            print(f"Raw browser log before: {raw_before or ''}")
            print(f"Raw browser log after: {raw_after or ''}")
            print(f"Full log before: {full_before or ''}")
            print(f"Full log after: {full_after or ''}")
        return 0
    finally:
        await agent.close()


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
