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
"""Run a BrowserAgent on a single task.

Example:
    python -m examples.toolkits.browser.browser_instruction.cli.run_simple_task \\
        --website "google search" \\
        --start-url "https://www.google.com" \\
        --task "Find the current weather in Tokyo"
"""

import argparse
import asyncio

from ..core.agent import (
    BrowserAgent,
)


async def _amain() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--website",
        default="google search",
        help=(
            "Website key matching a block in WEBSITE_GUIDELINES "
            "(e.g. 'google search', 'amazon', 'github')."
        ),
    )
    parser.add_argument(
        "--start-url",
        default="https://www.google.com",
        help="URL the agent should land on before executing the task.",
    )
    parser.add_argument(
        "--task",
        required=True,
        help="Natural-language task for the agent to perform.",
    )
    parser.add_argument(
        "--step-timeout",
        type=float,
        default=600.0,
        help="Per-step ChatAgent timeout in seconds (<=0 disables).",
    )
    parser.add_argument(
        "--tool-timeout",
        type=float,
        default=180.0,
        help="Per-tool-call timeout in seconds (<=0 disables).",
    )
    args = parser.parse_args()

    agent = BrowserAgent(
        website=args.website,
        start_url=args.start_url,
        step_timeout=None if args.step_timeout <= 0 else args.step_timeout,
        tool_execution_timeout=(
            None if args.tool_timeout <= 0 else args.tool_timeout
        ),
    )

    try:
        await agent.initialize()
        await agent.run(args.task)
        agent.print_statistics()
        agent.save_communication_log()
    finally:
        await agent.close()

    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_amain()))


if __name__ == "__main__":
    main()
