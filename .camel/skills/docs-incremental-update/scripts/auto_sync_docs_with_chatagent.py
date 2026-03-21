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
"""Auto-sync impacted docs using CAMEL ChatAgent.

Reads a list of impacted .mdx doc paths plus an optional list of changed
Python files, then asks a CAMEL ChatAgent to inspect and update each target
document directly through TerminalToolkit.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

SKILL_NAME = "docs-incremental-update"

SYSTEM_PROMPT = """\
You are a technical documentation writer for the CAMEL-AI framework.

You will receive:
1. The target doc path.
2. The Python files changed in this run.

Your task:
- First load the docs-incremental-update skill and follow it.
- Use the terminal to inspect the target doc, inspect any relevant code, and
  update only the target document when needed.
- Keep tool-based edits scoped to the current target doc.
- Preserve the target document frontmatter.
- Treat the provided changed Python files as optional context rather than a
  hard restriction.
- CI determines success from the resulting target doc file state. Do not rely
  on special sentinel strings in your final chat reply.
- If no reader-facing update is needed, leave the target doc untouched.
- Rewrite the documentation so it accurately reflects the latest code.
- Preserve the existing writing style, section structure, and Mintlify
  components (Card, Accordion, Tab, CodeGroup, etc.) as much as possible.
- Only change content that is outdated or inaccurate relative to the changed
  Python behavior and the mapped source code.
- Prefer no changes for small internal refactors, logging changes, test-only
  changes, or implementation details that readers do not need.
- If the current doc is already accurate, or the code changes are internal and
  do not affect public API, behavior, configuration, examples, or reader
  understanding, leave the file unchanged.
- Do NOT return the rewritten doc body in chat. A brief status note is fine.
"""


def _read_path_list(list_path: Path) -> list[str]:
    """Read a text file containing one path per line."""
    return [
        line.strip()
        for line in list_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _filter_changed_python_files(changed_files: list[str]) -> list[str]:
    """Keep only normalized Python file paths."""
    filtered: set[str] = set()
    for path in changed_files:
        normalized = Path(path).as_posix()
        if not normalized.endswith(".py"):
            continue
        filtered.add(normalized)
    return sorted(filtered)


def _format_path_section(title: str, paths: list[str]) -> str:
    """Format a markdown section for path lists."""
    if not paths:
        body = "(none)"
    else:
        body = "\n".join(f"- {path}" for path in paths)
    return f"## {title}\n\n{body}"


def _git_status_paths(repo_root: Path) -> set[str] | None:
    """Return modified or untracked repo paths from git status."""
    try:
        output = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.PIPE,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    paths: set[str] = set()
    for line in output.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.add(Path(path).as_posix())
    return paths


def _write_agent_response_log(
    log_dir: Path,
    doc_path: Path,
    result: str,
    status: str,
) -> None:
    """Append the final agent response to a debug log for investigation."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "agent_response.log"
    timestamp = datetime.now(timezone.utc).isoformat()
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {status} {doc_path.as_posix()}\n")
        handle.write(result)
        if not result.endswith("\n"):
            handle.write("\n")
        handle.write("\n")


def _build_user_message(
    doc_path: Path,
    changed_python_files: list[str],
) -> str:
    """Build the user message for a single impacted doc."""
    changed_files_section = _format_path_section(
        "Changed Python files for this run",
        changed_python_files,
    )
    return (
        f"## Target doc\n\n{doc_path.as_posix()}\n\n"
        f"{changed_files_section}\n\n"
        "Use the terminal to inspect this target doc and any relevant code, "
        "then update this target doc directly if needed."
    )


def _update_single_doc(
    doc_path: Path,
    repo_root: Path,
    log_dir: Path,
    model_platform: str,
    model_type: str,
    changed_python_files: list[str],
) -> None:
    """Update a single .mdx document in place through the agent."""
    # Lazy imports so --help works without CAMEL installed
    from camel.agents import ChatAgent
    from camel.models import ModelFactory
    from camel.toolkits import SkillToolkit, TerminalToolkit
    from camel.types import ModelPlatformType

    original_text = doc_path.read_text(encoding="utf-8")
    user_message = _build_user_message(doc_path, changed_python_files)
    baseline_paths = _git_status_paths(repo_root)

    platform = ModelPlatformType(model_platform)
    model = ModelFactory.create(
        model_platform=platform,
        model_type=model_type,
    )
    skill_toolkit = SkillToolkit(
        working_directory=str(repo_root),
        allowed_skills={SKILL_NAME},
    )
    terminal_log_dir = str(log_dir / "terminal_sessions")
    terminal_toolkit = TerminalToolkit(
        working_directory=str(repo_root),
        safe_mode=True,
        session_logs_dir=terminal_log_dir,
    )
    agent = ChatAgent(
        system_message=SYSTEM_PROMPT,
        model=model,
        tools=[
            *skill_toolkit.get_tools(),
            *terminal_toolkit.get_tools(),
        ],
    )
    response = agent.step(user_message)

    current_paths = _git_status_paths(repo_root)
    target_posix = doc_path.as_posix()
    log_dir_posix = log_dir.relative_to(repo_root).as_posix() + "/"
    if baseline_paths is not None and current_paths is not None:
        unexpected_paths = sorted(
            path
            for path in (current_paths - baseline_paths)
            if path != target_posix and not path.startswith(log_dir_posix)
        )
        if unexpected_paths:
            raise RuntimeError(
                "Agent modified files outside the target doc: "
                + ", ".join(unexpected_paths)
            )

    current_text = doc_path.read_text(encoding="utf-8")
    doc_changed = current_text != original_text
    result = response.msgs[0].content.strip() if response.msgs else ""
    status = "UPDATED" if doc_changed else "NO_WRITE"
    _write_agent_response_log(log_dir, doc_path, result, status)

    if not doc_changed:
        print(f"  SKIP (no doc update needed): {doc_path}")
        return

    if not current_text.endswith("\n"):
        doc_path.write_text(current_text + "\n", encoding="utf-8")
    print(f"  UPDATED: {doc_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Auto-sync impacted Mintlify docs with CAMEL ChatAgent."
    )
    parser.add_argument(
        "--docs-file",
        required=True,
        help="Path to a text file listing impacted .mdx paths (one per line).",
    )
    parser.add_argument(
        "--changed-files-file",
        default=None,
        help="Optional text file listing changed Python files for this run.",
    )
    parser.add_argument(
        "--changed-file",
        action="append",
        default=[],
        help="Changed Python file path. Can be passed multiple times.",
    )
    parser.add_argument(
        "--model-platform",
        default="openai",
        help="Model platform for CAMEL ChatAgent (default: openai).",
    )
    parser.add_argument(
        "--model-type",
        default="gpt-5.4",
        help="Model type for CAMEL ChatAgent (default: gpt-5.4).",
    )
    args = parser.parse_args()

    docs_file = Path(args.docs_file)
    if not docs_file.exists():
        print(f"docs-file not found: {docs_file}")
        return 1

    doc_paths = [Path(line) for line in _read_path_list(docs_file)]
    if not doc_paths:
        print("No impacted docs listed. Nothing to do.")
        return 0

    changed_files = list(args.changed_file)
    if args.changed_files_file:
        changed_files.extend(_read_path_list(Path(args.changed_files_file)))
    changed_python_files = _filter_changed_python_files(changed_files)

    repo_root = Path(".").resolve()
    # Use a dedicated log directory separate from TerminalToolkit's log dir
    # to avoid TerminalToolkit's init from cleaning up our response logs.
    log_dir = repo_root / "docs_sync_logs"
    success = 0
    fail = 0

    print(f"Auto-syncing {len(doc_paths)} doc(s) ...")
    for doc_path in doc_paths:
        try:
            _update_single_doc(
                doc_path,
                repo_root,
                log_dir,
                args.model_platform,
                args.model_type,
                changed_python_files,
            )
            success += 1
        except Exception as exc:
            print(f"  FAIL: {doc_path} — {exc}")
            traceback.print_exc()
            fail += 1

    print(f"\nDone. success={success} fail={fail}")
    return 1 if fail > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
