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

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
from modeling import DEFAULT_MODEL_PLATFORM, DEFAULT_MODEL_TYPE

from camel.evaluators.webjudge import (
    WebJudgeVisionConfig,
    WebJudgeVisionEvaluator,
)

load_dotenv()


def _load_task_and_response(
    session_dir: Path,
) -> Tuple[str, str, Optional[str]]:
    task = ""
    website: Optional[str] = None
    agent_response = ""

    timeline_path = session_dir / "action_timeline.json"
    if timeline_path.exists():
        timeline = json.loads(
            timeline_path.read_text(encoding="utf-8", errors="ignore")
        )
        if isinstance(timeline, dict):
            task = str(timeline.get("task_description", "") or task)
            website = timeline.get("website") or website

    comm_path = session_dir / "agent_communication_log.json"
    if comm_path.exists():
        comm = json.loads(
            comm_path.read_text(encoding="utf-8", errors="ignore")
        )
        if isinstance(comm, dict):
            task = str(comm.get("task_description", "") or task)
            website = comm.get("website") or website
            comms = comm.get("communications", [])
            if isinstance(comms, list):
                for entry in reversed(comms):
                    if (
                        isinstance(entry, dict)
                        and entry.get("type") == "main_agent_call"
                    ):
                        agent_response = str(entry.get("response", "") or "")
                        break

    return task, agent_response, str(website) if website else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline Vision-WebJudge evaluation for a browser_skills_example session."
    )
    parser.add_argument("session_dir", help="Path to session directory.")
    parser.add_argument("--task", default="", help="Override task text.")
    parser.add_argument(
        "--agent-response", default="", help="Override agent final response."
    )
    parser.add_argument(
        "--out",
        default="",
        help="Write verification JSON to this path (default: print to stdout).",
    )
    args = parser.parse_args()

    session_dir = Path(args.session_dir).expanduser().resolve()
    task, agent_response, website = _load_task_and_response(session_dir)
    task = (args.task or task).strip()
    agent_response = (args.agent_response or agent_response).strip()

    if not task:
        raise SystemExit(
            "Task text not found. Provide --task or ensure session has action_timeline.json/agent_communication_log.json."
        )

    evaluator = WebJudgeVisionEvaluator(
        config=WebJudgeVisionConfig(
            model_platform=DEFAULT_MODEL_PLATFORM,
            model_type=DEFAULT_MODEL_TYPE,
        )
    )
    verification: Dict[str, Any] = evaluator.evaluate_session(
        task=task,
        session_dir=session_dir,
        agent_response=agent_response,
        website=website,
    )

    payload = json.dumps(verification, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        Path(args.out).expanduser().write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
