# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
"""
Examples of using the pluggable backend system with FileToolkit and backends.

This script demonstrates:

1. Using FileToolkit with an in-memory StateBackend.
2. Using the raw backend APIs (FilesystemBackend, CompositeBackend,
   PolicyWrapper) to control where data is stored and which paths are allowed.
"""

from __future__ import annotations

import os
from pathlib import Path

from camel.toolkits.backends import (
    CompositeBackend,
    FilesystemBackend,
    PolicyWrapper,
    StateBackend,
)
from camel.toolkits.file_toolkit import FileToolkit


def example_1_filetoolkit_with_state_backend(base_dir: Path) -> None:
    """Show FileToolkit delegating edits to an in-memory StateBackend."""
    print("=== Example 1: FileToolkit + StateBackend (in-memory) ===")

    working_dir = base_dir / "workspace_state"
    working_dir.mkdir(parents=True, exist_ok=True)

    # All file content lives only in this backend dict, not on disk.
    backend = StateBackend()

    # FileToolkit will use our custom backend for edit_file.
    toolkit = FileToolkit(
        working_directory=str(working_dir),
        backend=backend,
    )

    # Pre-populate the backend directly.
    backend.write("/notes/todo.txt", "buy milk and eggs")

    # Edit via the toolkit using a *user* path (no leading slash).
    msg = toolkit.edit_file("notes/todo.txt", "milk", "bread")
    print("edit_file() →", msg)

    # Read from backend to prove it really changed in StateBackend.
    final_content = backend.read("/notes/todo.txt")
    print("backend.read('/notes/todo.txt') →", repr(final_content))
    print()


def example_2_composite_and_policy_backends(base_dir: Path) -> None:
    """Show CompositeBackend routing and PolicyWrapper blocking paths."""
    print(
        "=== Example 2: CompositeBackend + PolicyWrapper (backend layer) ==="
    )

    # Two filesystem sandboxes
    persist_root = base_dir / "persist_root"
    temp_root = base_dir / "temp_root"
    persist_root.mkdir(parents=True, exist_ok=True)
    temp_root.mkdir(parents=True, exist_ok=True)

    fs_persist = FilesystemBackend(root_dir=persist_root)
    fs_temp = FilesystemBackend(root_dir=temp_root)

    # Default backend will be the temp filesystem
    composite = CompositeBackend(
        default=fs_temp,
        routes={
            "/persist/": fs_persist,
        },
    )

    # Policy: completely block access to /secret/*
    blocked_ops: list[str] = []

    def policy(op: str, path: str) -> None:
        if path.startswith("/secret/"):
            blocked_ops.append(f"{op}:{path}")
            raise PermissionError("Access to /secret is forbidden")

    secured = PolicyWrapper(composite, policy)

    # 1) Write under /persist/ → goes to fs_persist
    print("--- Writing to /persist/report.txt (persist_root) ---")
    secured.write("/persist/report.txt", "report content")
    print(
        "Files under persist_root:",
        [p.relative_to(persist_root) for p in persist_root.rglob("*")],
    )

    # 2) Write under /temp/ → goes to fs_temp (default backend)
    print("\n--- Writing to /temp/log.txt (temp_root) ---")
    secured.write("/temp/log.txt", "log content")
    print(
        "Files under temp_root:",
        [p.relative_to(temp_root) for p in temp_root.rglob("*")],
    )

    # 3) Attempt to write under /secret/ → blocked by PolicyWrapper
    print(
        "\n--- Attempting to write to /secret/plan.txt (should be blocked) ---"
    )
    try:
        secured.write("/secret/plan.txt", "top secret")
    except PermissionError as e:
        print("Blocked as expected:", e)

    print("Recorded blocked operations:", blocked_ops)
    print()


def main() -> None:
    base_dir = Path("./examples/toolkits/filecreation_outputs").resolve()
    os.makedirs(base_dir, exist_ok=True)

    example_1_filetoolkit_with_state_backend(base_dir)
    example_2_composite_and_policy_backends(base_dir)

    print("Done. Inspect", base_dir, "for filesystem-backed content.")


if __name__ == "__main__":
    main()
