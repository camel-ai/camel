#!/usr/bin/env python3
"""Utilities for validating and using doc_code_map in Mintlify docs."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_DOC_ROOTS = (
    Path("docs/mintlify/key_modules"),
    Path("docs/mintlify/mcp"),
)


@dataclass
class DocMap:
    doc_path: Path
    patterns: list[str]


def _iter_docs(roots: Iterable[Path]) -> list[Path]:
    docs: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        docs.extend(sorted(root.glob("*.mdx")))
    return docs


def _extract_doc_code_map(doc_path: Path) -> list[str]:
    text = doc_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return []
    end = text.find("\n---\n", 4)
    if end == -1:
        return []
    frontmatter = text[4:end].splitlines()

    patterns: list[str] = []
    in_block = False
    for line in frontmatter:
        if not in_block:
            if line.startswith("doc_code_map:"):
                in_block = True
            continue
        if line.startswith("  - "):
            item = line[4:].strip()
            if (
                len(item) >= 2
                and item[0] == item[-1]
                and item[0] in ('"', "'")
            ):
                item = item[1:-1]
            if item:
                patterns.append(item)
            continue
        break
    return patterns


def _collect_doc_maps(roots: Iterable[Path]) -> list[DocMap]:
    docs = _iter_docs(roots)
    return [DocMap(doc, _extract_doc_code_map(doc)) for doc in docs]


def _run_git_diff(base_ref: str, head_ref: str) -> list[str]:
    cmd = ["git", "diff", "--name-only", f"{base_ref}..{head_ref}"]
    out = subprocess.check_output(cmd, text=True)
    return [line.strip() for line in out.splitlines() if line.strip()]


def _verify(doc_maps: list[DocMap], repo_root: Path) -> int:
    errors: list[str] = []
    checked = 0
    for doc_map in doc_maps:
        checked += 1
        if not doc_map.patterns:
            errors.append(
                f"{doc_map.doc_path}: missing or empty doc_code_map block"
            )
            continue

        for pattern in doc_map.patterns:
            matches = list(repo_root.glob(pattern))
            if not matches:
                errors.append(
                    f"{doc_map.doc_path}: pattern has no matches -> {pattern}"
                )

    if errors:
        print("doc_code_map verification failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    print(f"doc_code_map verification passed for {checked} documents.")
    return 0


def _impacted_docs(
    doc_maps: list[DocMap],
    changed_files: list[str],
    repo_root: Path,
) -> list[Path]:
    changed = {str(Path(p).as_posix()) for p in changed_files}
    impacted: list[Path] = []
    for doc_map in doc_maps:
        matched = False
        for pattern in doc_map.patterns:
            for path in repo_root.glob(pattern):
                rel = str(path.resolve().relative_to(repo_root).as_posix())
                if rel in changed:
                    matched = True
                    break
            if matched:
                break
        if matched:
            impacted.append(doc_map.doc_path)
    return sorted(impacted)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_p = subparsers.add_parser(
        "verify", help="Verify doc_code_map blocks and pattern matches."
    )
    verify_p.add_argument(
        "--docs-root",
        action="append",
        default=[],
        help="Root directory containing .mdx docs. Can be passed multiple times.",
    )

    impacted_p = subparsers.add_parser(
        "impacted",
        help="Print impacted docs based on changed files or git refs.",
    )
    impacted_p.add_argument(
        "--docs-root",
        action="append",
        default=[],
        help="Root directory containing .mdx docs. Can be passed multiple times.",
    )
    impacted_p.add_argument(
        "--base-ref",
        default=None,
        help="Base git ref for diff, used with --head-ref.",
    )
    impacted_p.add_argument(
        "--head-ref",
        default="HEAD",
        help="Head git ref for diff.",
    )
    impacted_p.add_argument(
        "--changed-file",
        action="append",
        default=[],
        help="Changed file path. Can be passed multiple times.",
    )

    args = parser.parse_args()
    repo_root = Path(".").resolve()

    roots = [Path(p) for p in args.docs_root] if args.docs_root else list(
        DEFAULT_DOC_ROOTS
    )
    doc_maps = _collect_doc_maps(roots)

    if args.command == "verify":
        return _verify(doc_maps, repo_root)

    changed_files: list[str] = []
    if args.changed_file:
        changed_files.extend(args.changed_file)
    elif args.base_ref:
        changed_files.extend(_run_git_diff(args.base_ref, args.head_ref))
    else:
        parser.error(
            "impacted requires either --changed-file or --base-ref/--head-ref."
        )

    impacted = _impacted_docs(doc_maps, changed_files, repo_root)
    for doc in impacted:
        print(str(doc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
