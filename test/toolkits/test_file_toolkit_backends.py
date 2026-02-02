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
from __future__ import annotations

from pathlib import Path

from camel.toolkits.backends import StateBackend
from camel.toolkits.file_toolkit import (
    FileToolkit,  # adjust import path if needed
)

r"""
Integration tests for FileToolkit with pluggable storage backends.

These tests verify that FileToolkit correctly delegates file edit operations
to the configured backend implementation. They ensure that:
- A custom backend (StateBackend) can be injected and used at runtime.
- The default behavior (FilesystemBackend) remains functional when no backend
  is explicitly provided.
- User-facing paths are correctly translated into backend logical paths.
"""


def test_file_toolkit_edit_uses_state_backend(tmp_path: Path) -> None:
    r"""
    Verify that FileToolkit.edit_file delegates edit operations to a
    user-provided StateBackend.

    This test ensures that:
    - A StateBackend can be injected into FileToolkit.
    - FileToolkit.edit_file operates purely through the backend abstraction,
      without relying on the local filesystem.
    - Edits performed via the toolkit correctly modify backend-managed state.

    This confirms true backend pluggability and backend-agnostic toolkit logic.
    """
    working_dir = tmp_path / "work"
    working_dir.mkdir(parents=True, exist_ok=True)

    backend = StateBackend()
    toolkit = FileToolkit(
        working_directory=str(working_dir),
        backend=backend,
    )

    # Pre-populate backend directly (bypassing the filesystem)
    backend.write("/foo.txt", "hello world")

    # Edit via toolkit using a user-level relative path
    message = toolkit.edit_file("foo.txt", "hello", "bye")

    assert "Successfully edited" in message
    assert backend.read("/foo.txt") == "bye world"


def test_file_toolkit_edit_with_default_filesystem_backend(
    tmp_path: Path,
) -> None:
    r"""
    Verify that FileToolkit.edit_file works correctly with the default
    FilesystemBackend when no backend is explicitly provided.

    This test ensures that:
    - BackendAwareToolkit falls back to FilesystemBackend by default.
    - Existing FileToolkit behavior is preserved for backward compatibility.
    - File edits correctly modify on-disk files within the working directory.
    """
    working_dir = tmp_path / "work"
    working_dir.mkdir(parents=True, exist_ok=True)

    # No backend passed → FilesystemBackend is used implicitly
    toolkit = FileToolkit(
        working_directory=str(working_dir),
    )

    file_path = working_dir / "note.txt"
    file_path.write_text("old value", encoding="utf-8")

    message = toolkit.edit_file("note.txt", "old", "new")
    assert "Successfully edited" in message

    assert file_path.read_text(encoding="utf-8") == "new value"
