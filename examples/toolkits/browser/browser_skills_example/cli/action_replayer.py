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
# -*- coding: utf-8 -*-
"""Replay browser actions from HybridBrowserToolkit log files."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from examples.toolkits.browser.browser_skills_example.core.action_replayer import (
    ActionReplayer,
)


async def _amain() -> int:
    parser = argparse.ArgumentParser(
        description="Replay browser actions from log file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Replay entire log
  python -m examples.toolkits.browser.browser_skills_example.cli.action_replayer my_log.log

  # Replay specific subtask
  python -m examples.toolkits.browser.browser_skills_example.cli.action_replayer my_log.log --subtask-config my_log_subtasks.json --subtask-id 02_enter_departure_location

  # Replay subtask with variable overrides
  python -m examples.toolkits.browser.browser_skills_example.cli.action_replayer my_log.log --subtask-config my_log_subtasks.json --subtask-id 02_enter_departure_location --var departure_city="London"

  # Multiple variables
  python -m examples.toolkits.browser.browser_skills_example.cli.action_replayer my_log.log --subtask-config my_log_subtasks.json --subtask-id 04_set_travel_dates --var departure_date="2026-01-15" --var return_date="2026-01-20"

  # List available subtasks
  python -m examples.toolkits.browser.browser_skills_example.cli.action_replayer my_log.log --subtask-config my_log_subtasks.json --list-subtasks
        """,
    )
    parser.add_argument("log_file", help="Path to the log file to replay")
    parser.add_argument(
        "--port",
        type=int,
        default=9223,
        help="CDP port number (default: 9223)",
    )
    parser.add_argument(
        "--subtask-config",
        help="Path to subtask configuration JSON file",
    )
    parser.add_argument(
        "--subtask-id",
        help="ID of specific subtask to replay",
    )
    parser.add_argument(
        "--var",
        action="append",
        help="Variable override in format key=value (can be used multiple times)",
    )
    parser.add_argument(
        "--list-subtasks",
        action="store_true",
        help="List available subtasks and exit",
    )
    parser.add_argument(
        "--use-agent-recovery",
        action="store_true",
        help="Use ChatAgent for intelligent error recovery when elements are not found",
    )

    args = parser.parse_args()

    if not Path(args.log_file).exists():
        print(f"Error: Log file not found: {args.log_file}", file=sys.stderr)
        return 2

    if args.list_subtasks:
        if not args.subtask_config:
            print(
                "Error: --subtask-config required with --list-subtasks",
                file=sys.stderr,
            )
            return 2

        with open(args.subtask_config, "r", encoding="utf-8") as f:
            config = json.load(f)

        print("=" * 80)
        print("AVAILABLE SUBTASKS")
        print("=" * 80)
        print(f"Log file: {config.get('log_file', 'N/A')}")
        print(f"Task: {config.get('task_description', 'N/A')}")
        print()

        subtasks = config.get("subtasks", [])
        for i, subtask in enumerate(subtasks, 1):
            print(f"{i}. {subtask['id']}")
            print(f"   Name: {subtask['name']}")
            print(f"   Description: {subtask['description']}")
            print(
                f"   Actions: {subtask['start_index']}-{subtask['end_index']} ({subtask['end_index'] - subtask['start_index'] + 1} total)"
            )
            if "notes" in subtask:
                print(f"   Notes: {subtask['notes']}")

            if "variables" in subtask:
                print("   Variables:")
                for var_name, var_config in subtask["variables"].items():
                    print(
                        f"     {var_name}: {var_config['description']} (default: {var_config['default_value']})"
                    )
            print()
        return 0

    variables = {}
    if args.var:
        for var_str in args.var:
            if "=" not in var_str:
                print(
                    f"Error: Invalid variable format '{var_str}'. Expected format: key=value",
                    file=sys.stderr,
                )
                return 2
            key, value = var_str.split("=", 1)
            variables[key.strip()] = value.strip('"').strip("'").strip()

    replayer = ActionReplayer(
        log_file=args.log_file,
        cdp_port=args.port,
        subtask_config=args.subtask_config,
        subtask_id=args.subtask_id,
        variables=variables,
        use_agent_recovery=args.use_agent_recovery,
    )
    await replayer.replay_all()
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
