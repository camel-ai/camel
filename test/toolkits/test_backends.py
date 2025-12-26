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
r"""Tests for backend implementations in camel.toolkits.backends.

This module verifies the behavior of the in-memory, filesystem, composite,
and policy-wrapped backends. The tests cover basic read, write, edit, and
delete operations, routing semantics, sandboxing guarantees, and policy
enforcement.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from camel.toolkits.backends import (
    CompositeBackend,
    FilesystemBackend,
    PolicyWrapper,
    StateBackend,
)

# -------------------------
# StateBackend tests
# -------------------------


def test_state_backend_write_read_edit_delete() -> None:
    r"""StateBackend supports write, read, edit, and delete operations."""
    backend = StateBackend()

    # write
    write_result = backend.write("/foo/bar.txt", "hello state")
    assert write_result.success

    # read
    assert backend.read("/foo/bar.txt") == "hello state"

    # edit
    edit_result = backend.edit("/foo/bar.txt", "hello", "bye")
    assert edit_result.success
    assert edit_result.replaced == 1
    assert backend.read("/foo/bar.txt") == "bye state"

    # delete (non-recursive)
    delete_result = backend.delete("/foo/bar.txt", recursive=False)
    assert delete_result.success
    assert delete_result.deleted == 1
    assert not backend.exists("/foo/bar.txt")


def test_state_backend_ls_and_glob() -> None:
    r"""StateBackend lists and globs files using inferred directories."""
    backend = StateBackend()

    backend.write("/dir1/file1.txt", "a")
    backend.write("/dir1/file2.txt", "b")
    backend.write("/dir2/other.md", "c")

    # ls_info should show children of /dir1
    entries = backend.ls_info("/dir1")
    paths = sorted(file_info.path for file_info in entries)
    assert paths == ["/dir1/file1.txt", "/dir1/file2.txt"]

    # glob_info
    md_entries = backend.glob_info("*.md", "/dir2")
    assert len(md_entries) == 1
    assert md_entries[0].path == "/dir2/other.md"

    # grep_raw
    matches = backend.grep_raw("b", "/dir1/file2.txt")
    assert len(matches) == 1
    assert matches[0].path == "/dir1/file2.txt"
    assert matches[0].line_no == 1
    assert matches[0].line == "b"


# -------------------------
# FilesystemBackend tests
# -------------------------


def test_filesystem_backend_write_read(tmp_path: Path) -> None:
    r"""FilesystemBackend writes to and reads from the sandbox directory."""
    root = tmp_path / "root"  # Path("camel_working_dir")
    backend = FilesystemBackend(root_dir=root)

    result = backend.write("/note.txt", "hello fs")
    assert result.success

    # The physical file should be under root
    physical_file = root / "note.txt"
    assert physical_file.exists()
    assert physical_file.read_text(encoding="utf-8") == "hello fs"

    # read via backend
    assert backend.read("/note.txt") == "hello fs"


def test_filesystem_backend_edit_and_delete(tmp_path: Path) -> None:
    r"""FilesystemBackend supports edit and delete operations."""
    root = tmp_path / "root"
    backend = FilesystemBackend(root_dir=root)

    backend.write("/docs/file.txt", "old value")
    edit_result = backend.edit("/docs/file.txt", "old", "new")
    assert edit_result.success
    assert edit_result.replaced == 1
    assert backend.read("/docs/file.txt") == "new value"

    delete_result = backend.delete("/docs/file.txt", recursive=False)
    assert delete_result.success
    assert delete_result.deleted == 1
    assert not backend.exists("/docs/file.txt")


def test_filesystem_backend_sandboxing_maps_absolute_under_root(
    tmp_path: Path,
) -> None:
    r"""Absolute-style logical paths are sandboxed under the backend root."""
    root = tmp_path / "root"
    backend = FilesystemBackend(root_dir=root)

    # This should NOT touch real /etc, but map under root_dir/etc/passwd
    result = backend.write("/etc/passwd", "fake")
    assert result.success

    physical_file = root / "etc" / "passwd"
    assert physical_file.exists()
    assert physical_file.read_text(encoding="utf-8") == "fake"


# -------------------------
# CompositeBackend tests
# -------------------------


def test_composite_backend_routes_to_correct_backend(tmp_path: Path) -> None:
    r"""CompositeBackend routes paths to the correct underlying backend."""
    root = tmp_path / "root"
    fs_backend = FilesystemBackend(root_dir=root)
    mem_backend = StateBackend()

    backend = CompositeBackend(
        default=mem_backend,
        routes={
            "/persist/": fs_backend,
        },
    )

    # /persist/* -> filesystem
    backend.write("/persist/a.txt", "from fs")
    # /temp/*    -> state backend (default)
    backend.write("/temp/b.txt", "from mem")

    # Check filesystem
    physical_file = root / "persist" / "a.txt"
    assert physical_file.exists()
    assert physical_file.read_text(encoding="utf-8") == "from fs"

    # Check in-memory
    assert mem_backend.read("/temp/b.txt") == "from mem"


# -------------------------
# PolicyWrapper tests
# -------------------------


def test_policy_wrapper_blocks_forbidden_paths(tmp_path: Path) -> None:
    r"""PolicyWrapper blocks operations on forbidden logical paths."""
    root = tmp_path / "root"
    fs_backend = FilesystemBackend(root_dir=root)

    blocked_paths: List[str] = []

    def policy(operation: str, path: str) -> None:
        if path.startswith("/secret/"):
            blocked_paths.append(f"{operation}:{path}")
            raise PermissionError("Access to /secret is forbidden")

    backend = PolicyWrapper(fs_backend, policy)

    # Allowed path
    result = backend.write("/public.txt", "ok")
    assert result.success

    # Forbidden path
    with pytest.raises(PermissionError):
        backend.write("/secret/data.txt", "blocked")

    assert blocked_paths == ["write:/secret/data.txt"]
