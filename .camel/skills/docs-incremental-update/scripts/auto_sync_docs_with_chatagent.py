#!/usr/bin/env python3
"""Auto-sync impacted docs using CAMEL ChatAgent.

Reads a list of impacted .mdx doc paths plus an optional list of changed
Python files, then asks a CAMEL ChatAgent to inspect and update each target
document directly through TerminalToolkit.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

NO_CHANGES_SENTINEL = "__NO_CHANGES__"
SKILL_NAME = "docs-incremental-update"

SYSTEM_PROMPT = """\
You are a technical documentation writer for the CAMEL-AI framework.

You will receive:
1. The target doc path.
2. The Python files changed in this run.

Your task:
- First load the docs-incremental-update skill and follow it.
- Use the terminal to inspect the target doc, read its doc_code_map, inspect
  the mapped Python files, and update only the target document when needed.
- Keep tool-based edits scoped to the current target doc.
- Preserve the target document frontmatter.
- Focus only on the provided changed Python files. Ignore docs-only, workflow,
  YAML, release, and other non-Python changes.
- Rewrite the documentation so it accurately reflects the latest code.
- Preserve the existing writing style, section structure, and Mintlify
  components (Card, Accordion, Tab, CodeGroup, etc.) as much as possible.
- Only change content that is outdated or inaccurate relative to the changed
  Python behavior and the mapped source code.
- If the current doc is already accurate, or the code changes are internal and
  do not affect public API, behavior, configuration, examples, or reader
  understanding, return exactly __NO_CHANGES__.
- Prefer no changes for small internal refactors, logging changes, test-only
  changes, or implementation details that readers do not need.
- If you update the target doc in place, return exactly UPDATED.
- Do NOT return the rewritten doc body in chat.
"""


def _read_path_list(list_path: Path) -> list[str]:
    """Read a text file containing one path per line."""
    return [
        line.strip()
        for line in list_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _filter_changed_python_files(changed_files: list[str]) -> list[str]:
    """Keep only Python files under camel/."""
    filtered: set[str] = set()
    for path in changed_files:
        normalized = Path(path).as_posix()
        if not normalized.endswith(".py"):
            continue
        if normalized.startswith("camel/"):
            filtered.add(normalized)
    return sorted(filtered)


def _format_path_section(title: str, paths: list[str]) -> str:
    """Format a markdown section for path lists."""
    if not paths:
        body = "(none)"
    else:
        body = "\n".join(f"- {path}" for path in paths)
    return f"## {title}\n\n{body}"


def _should_skip_update(text: str) -> bool:
    """Return whether the model requested skipping this doc update."""
    return text.strip() == NO_CHANGES_SENTINEL


def _build_user_message(
    doc_path: Path,
    changed_python_files: list[str],
) -> str:
    """Build the user message for a single impacted doc."""
    return (
        f"## Target doc\n\n{doc_path.as_posix()}\n\n"
        f"{_format_path_section('Changed Python files for this run', changed_python_files)}\n\n"
        "Use the terminal to inspect this target doc, read its "
        "`doc_code_map`, inspect the mapped Python files, and update this "
        "target doc directly if needed."
    )


def _update_single_doc(
    doc_path: Path,
    repo_root: Path,
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

    platform = ModelPlatformType(model_platform)
    model = ModelFactory.create(
        model_platform=platform,
        model_type=model_type,
    )
    skill_toolkit = SkillToolkit(
        working_directory=str(repo_root),
        allowed_skills={SKILL_NAME},
    )
    terminal_toolkit = TerminalToolkit(
        working_directory=str(repo_root),
        safe_mode=False,
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

    if not response.msgs:
        raise RuntimeError("ChatAgent returned empty response")

    current_text = doc_path.read_text(encoding="utf-8")
    doc_changed = current_text != original_text
    result = response.msgs[0].content.strip()

    if _should_skip_update(result):
        if doc_changed:
            raise RuntimeError(
                "Agent returned __NO_CHANGES__ but modified the target doc."
            )
        print(f"  SKIP (no doc update needed): {doc_path}")
        return

    if not doc_changed:
        raise RuntimeError(
            "Agent did not modify the target doc and did not return "
            "__NO_CHANGES__."
        )

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
    success = 0
    fail = 0

    print(f"Auto-syncing {len(doc_paths)} doc(s) ...")
    for doc_path in doc_paths:
        try:
            _update_single_doc(
                doc_path,
                repo_root,
                args.model_platform,
                args.model_type,
                changed_python_files,
            )
            success += 1
        except Exception as exc:
            print(f"  FAIL: {doc_path} — {exc}")
            fail += 1

    print(f"\nDone. success={success} fail={fail}")
    return 1 if fail > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
