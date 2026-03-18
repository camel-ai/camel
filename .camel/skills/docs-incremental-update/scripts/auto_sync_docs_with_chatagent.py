#!/usr/bin/env python3
"""Auto-sync impacted docs using CAMEL ChatAgent.

Reads a list of impacted .mdx doc paths plus an optional list of changed
Python files, resolves source code via doc_code_map, and uses a CAMEL
ChatAgent to regenerate each document body while preserving the original
frontmatter.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# doc_code_map lives in docs/scripts/docs_sync/ — add it to the path
_REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_REPO_ROOT / "docs" / "scripts" / "docs_sync"))

from doc_code_map import _extract_doc_code_map  # noqa: E402

MAX_CODE_CHARS = 120_000
TRUNCATION_MARKER = "\n... (truncated)\n"
NO_CHANGES_SENTINEL = "__NO_CHANGES__"
SKILL_NAME = "docs-incremental-update"

SYSTEM_PROMPT = """\
You are a technical documentation writer for the CAMEL-AI framework.
You have access to only two toolkits:
1. SkillToolkit
2. TerminalToolkit

You will receive:
1. The target doc path.
2. The current documentation body (Mintlify MDX format).
3. The Python files changed in this run.
4. The subset of changed Python files relevant to the target doc.
5. The latest mapped Python source code.

Your task:
- First load the docs-incremental-update skill and follow it.
- Use the terminal when you need to confirm the current doc body, inspect the
  mapped Python files, check the provided Python diff scope, or update the
  impacted documentation directly.
- Keep any direct tool-based edits scoped to the impacted documentation for
  this run, and preserve the target document frontmatter.
- Your final response must still be either the complete updated body for the
  current target doc or __NO_CHANGES__.
- Focus only on the provided changed Python files. Ignore docs-only, workflow,
  YAML, release, and other non-Python changes.
- Rewrite the documentation body so it accurately reflects the latest code.
- Preserve the existing writing style, section structure, and Mintlify
  components (Card, Accordion, Tab, CodeGroup, etc.) as much as possible.
- Only change content that is outdated or inaccurate relative to the changed
  Python behavior and the mapped source code.
- If the current body is already accurate, or the code changes are internal and
  do not affect public API, behavior, configuration, examples, or reader
  understanding, return exactly __NO_CHANGES__.
- Prefer no changes for small internal refactors, logging changes, test-only
  changes, or implementation details that readers do not need.
- Do NOT output frontmatter (the --- block). Only return the body.
- Do NOT wrap the output in markdown code fences.
"""


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_block_including_delimiters, body)."""
    if not text.startswith("---\n"):
        return "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", text
    # include the closing ---\n
    fm_end = end + len("\n---\n")
    return text[:fm_end], text[fm_end:]


def _read_path_list(list_path: Path) -> list[str]:
    """Read a text file containing one path per line."""
    return [
        line.strip()
        for line in list_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _filter_changed_python_files(changed_files: list[str]) -> list[str]:
    """Keep only Python files under camel/ or services/."""
    filtered: set[str] = set()
    for path in changed_files:
        normalized = Path(path).as_posix()
        if not normalized.endswith(".py"):
            continue
        if normalized.startswith("camel/") or normalized.startswith(
            "services/"
        ):
            filtered.add(normalized)
    return sorted(filtered)


def _resolve_mapped_paths(doc_path: Path, repo_root: Path) -> list[Path]:
    """Resolve mapped source files for *doc_path*."""
    patterns = _extract_doc_code_map(doc_path)
    if not patterns:
        return []

    paths: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for path in sorted(repo_root.glob(pattern)):
            if not path.is_file() or path in seen:
                continue
            seen.add(path)
            paths.append(path)
    return paths


def _resolve_code(doc_path: Path, repo_root: Path) -> str:
    """Collect source code mapped to *doc_path*, trimmed to budget."""
    mapped_paths = _resolve_mapped_paths(doc_path, repo_root)
    if not mapped_paths:
        return ""

    code_parts: list[str] = []
    total = 0
    for path in mapped_paths:
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        rel = path.relative_to(repo_root)
        header = f"# --- {rel} ---\n"
        chunk = header + content + "\n"
        if total + len(chunk) > MAX_CODE_CHARS:
            remaining = MAX_CODE_CHARS - total
            min_required = len(header) + len(TRUNCATION_MARKER) + 200
            if remaining >= min_required:
                content_budget = (
                    remaining - len(header) - len(TRUNCATION_MARKER)
                )
                code_parts.append(
                    header + content[:content_budget] + TRUNCATION_MARKER
                )
            return "".join(code_parts)
        code_parts.append(chunk)
        total += len(chunk)
        if total >= MAX_CODE_CHARS:
            break
    return "".join(code_parts)


def _relevant_changed_python_files(
    doc_path: Path,
    repo_root: Path,
    changed_python_files: list[str],
) -> list[str]:
    """Return changed Python files that map to *doc_path*."""
    mapped = {
        path.relative_to(repo_root).as_posix()
        for path in _resolve_mapped_paths(doc_path, repo_root)
    }
    return [path for path in changed_python_files if path in mapped]


def _format_path_section(title: str, paths: list[str]) -> str:
    """Format a markdown section for path lists."""
    if not paths:
        body = "(none)"
    else:
        body = "\n".join(f"- {path}" for path in paths)
    return f"## {title}\n\n{body}"


def _strip_fences(text: str) -> str:
    """Remove markdown code fences the LLM may have wrapped around output."""
    stripped = text.strip()
    # Remove opening ```mdx or ```markdown or ``` at the very start
    stripped = re.sub(r"^```(?:mdx|markdown|md)?\s*\n", "", stripped)
    # Remove closing ``` at the very end
    stripped = re.sub(r"\n```\s*$", "", stripped)
    return stripped


def _strip_accidental_frontmatter(text: str) -> str:
    """Remove frontmatter if the LLM accidentally included one."""
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            text = text[end + len("\n---\n") :]
    return text


def _should_skip_update(text: str) -> bool:
    """Return whether the model requested skipping this doc update."""
    return text.strip() == NO_CHANGES_SENTINEL


def _doc_was_updated_in_place(
    original_text: str,
    current_text: str,
    frontmatter: str,
) -> bool:
    """Return whether the agent updated the target doc directly."""
    if current_text == original_text:
        return False
    if frontmatter and not current_text.startswith(frontmatter):
        raise RuntimeError(
            "Agent updated the document in place but changed frontmatter."
        )
    return True


def _update_single_doc(
    doc_path: Path,
    repo_root: Path,
    model_platform: str,
    model_type: str,
    changed_python_files: list[str],
) -> None:
    """Update a single .mdx document in place."""
    # Lazy imports so --help works without CAMEL installed
    from camel.agents import ChatAgent
    from camel.models import ModelFactory
    from camel.toolkits import SkillToolkit, TerminalToolkit
    from camel.types import ModelPlatformType

    text = doc_path.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(text)
    if not frontmatter:
        print(f"  SKIP (no frontmatter): {doc_path}")
        return

    code = _resolve_code(doc_path, repo_root)
    if not code:
        print(f"  SKIP (no mapped code): {doc_path}")
        return

    relevant_changed_files = _relevant_changed_python_files(
        doc_path, repo_root, changed_python_files
    )
    user_message = (
        f"## Target doc\n\n{doc_path.as_posix()}\n\n"
        f"{_format_path_section('Changed Python files for this run', changed_python_files)}\n\n"
        f"{_format_path_section('Relevant changed Python files for this doc', relevant_changed_files)}\n\n"
        f"## Current documentation body\n\n{body}\n\n"
        f"## Mapped Python source code\n\n{code}"
    )

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
        safe_mode=True,
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
    if _doc_was_updated_in_place(text, current_text, frontmatter):
        if not current_text.endswith("\n"):
            doc_path.write_text(current_text + "\n", encoding="utf-8")
        print(f"  UPDATED IN PLACE: {doc_path}")
        return

    new_body = response.msgs[0].content
    new_body = _strip_fences(new_body)
    new_body = _strip_accidental_frontmatter(new_body)
    if _should_skip_update(new_body):
        print(f"  SKIP (no doc update needed): {doc_path}")
        return

    doc_path.write_text(frontmatter + new_body + "\n", encoding="utf-8")
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
