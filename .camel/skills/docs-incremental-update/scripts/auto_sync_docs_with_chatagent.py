#!/usr/bin/env python3
"""Auto-sync impacted docs using CAMEL ChatAgent.

Reads a list of .mdx doc paths from a file, resolves source code via
doc_code_map, and uses a CAMEL ChatAgent to regenerate each document
body while preserving the original frontmatter.
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

SYSTEM_PROMPT = """\
You are a technical documentation writer for the CAMEL-AI framework.
You will receive:
1. The current documentation body (Mintlify MDX format).
2. The latest source code that the document maps to.

Your task:
- Rewrite the documentation body so it accurately reflects the latest code.
- Preserve the existing writing style, section structure, and Mintlify
  components (Card, Accordion, Tab, CodeGroup, etc.) as much as possible.
- Only change content that is outdated or inaccurate relative to the code.
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


def _resolve_code(doc_path: Path, repo_root: Path) -> str:
    """Collect source code mapped to *doc_path*, trimmed to budget."""
    patterns = _extract_doc_code_map(doc_path)
    if not patterns:
        return ""

    code_parts: list[str] = []
    total = 0
    for pattern in patterns:
        for path in sorted(repo_root.glob(pattern)):
            if not path.is_file():
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                continue
            rel = path.relative_to(repo_root)
            header = f"# --- {rel} ---\n"
            chunk = header + content + "\n"
            if total + len(chunk) > MAX_CODE_CHARS:
                remaining = MAX_CODE_CHARS - total
                if remaining > len(header) + 200:
                    code_parts.append(
                        header
                        + content[: remaining - len(header)]
                        + "\n... (truncated)\n"
                    )
                break
            code_parts.append(chunk)
            total += len(chunk)
        if total >= MAX_CODE_CHARS:
            break
    return "".join(code_parts)


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


def _update_single_doc(
    doc_path: Path,
    repo_root: Path,
    model_platform: str,
    model_type: str,
) -> None:
    """Update a single .mdx document in place."""
    # Lazy imports so --help works without CAMEL installed
    from camel.agents import ChatAgent
    from camel.models import ModelFactory
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

    user_message = (
        f"## Current documentation body\n\n{body}\n\n"
        f"## Source code\n\n{code}"
    )

    platform = ModelPlatformType(model_platform)
    model = ModelFactory.create(
        model_platform=platform,
        model_type=model_type,
    )
    agent = ChatAgent(system_message=SYSTEM_PROMPT, model=model)
    response = agent.step(user_message)

    if not response.msgs:
        raise RuntimeError("ChatAgent returned empty response")

    new_body = response.msgs[0].content
    new_body = _strip_fences(new_body)
    new_body = _strip_accidental_frontmatter(new_body)

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
        "--model-platform",
        default="openai",
        help="Model platform for CAMEL ChatAgent (default: openai).",
    )
    parser.add_argument(
        "--model-type",
        default="gpt-4o-mini",
        help="Model type for CAMEL ChatAgent (default: gpt-4o-mini).",
    )
    args = parser.parse_args()

    docs_file = Path(args.docs_file)
    if not docs_file.exists():
        print(f"docs-file not found: {docs_file}")
        return 1

    doc_paths = [
        Path(line.strip())
        for line in docs_file.read_text().splitlines()
        if line.strip()
    ]
    if not doc_paths:
        print("No impacted docs listed. Nothing to do.")
        return 0

    repo_root = Path(".").resolve()
    success = 0
    fail = 0

    print(f"Auto-syncing {len(doc_paths)} doc(s) ...")
    for doc_path in doc_paths:
        try:
            _update_single_doc(
                doc_path, repo_root, args.model_platform, args.model_type
            )
            success += 1
        except Exception as exc:
            print(f"  FAIL: {doc_path} — {exc}")
            fail += 1

    print(f"\nDone. success={success} fail={fail}")
    return 1 if fail > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
