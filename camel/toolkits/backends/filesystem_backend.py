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

import os
from pathlib import Path
from typing import List, Optional

from camel.logger import get_logger

from .base import BaseBackend
from .types import (
    DeleteResult,
    EditResult,
    FileInfo,
    GrepMatch,
    WriteResult,
)

logger = get_logger(__name__)


class FilesystemBackend(BaseBackend):
    r"""Filesystem-backed storage rooted at a sandbox directory.

    All logical paths are resolved relative to :attr:`root_dir` and are
    prevented from escaping the sandbox. This backend provides text-based
    read, write, edit, delete, listing, and search operations on the local
    filesystem.
    """

    def __init__(
        self,
        root_dir: Path,
        default_encoding: str = "utf-8",
        backup_enabled: bool = True,
    ) -> None:
        r"""Initialize the filesystem backend.

        Args:
            root_dir (Path): Root directory of the sandbox. All logical
                paths are resolved under this directory.
            default_encoding (str): Default encoding used for reading and
                writing text files.
                (default: :obj:`"utf-8"`)
            backup_enabled (bool): Whether to create timestamped ``.bak``
                files before overwriting existing files.
                (default: :obj:`True`)
        """
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.default_encoding = default_encoding
        self.backup_enabled = backup_enabled

    # ---------- internal helpers ----------

    def _resolve(self, path: str) -> Path:
        r"""Resolve a logical path to a filesystem path inside the sandbox.

        Absolute-looking logical paths are treated as relative to the
        sandbox root, with the leading ``"/"`` stripped. If the resolved
        path would escape :attr:`root_dir`, a :class:`PermissionError`
        is raised.

        Args:
            path (str): Logical POSIX-style path (for example,
                ``"foo/bar.txt"``).

        Returns:
            Path: Resolved filesystem path located under :attr:`root_dir`.

        Raises:
            PermissionError: If the resolved path would escape the sandbox
                root directory.
        """
        path_obj = Path(path)
        if not path_obj.is_absolute():
            full = (self.root_dir / path_obj).resolve()
        else:
            # Treat absolute-like logical paths as relative to root
            full = (self.root_dir / path_obj.relative_to("/")).resolve()

        try:
            full.relative_to(self.root_dir)
        except ValueError:
            raise PermissionError(f"Path {path} escapes sandbox")
        return full

    def _create_backup(self, file_path: Path) -> Optional[Path]:
        r"""Create a timestamped backup of a file if backups are enabled.

        The backup is created in the same directory as ``file_path`` and
        uses an additional ``.YYYYMMDD_HHMMSS.bak`` suffix.

        Args:
            file_path (Path): Path of the file to back up.

        Returns:
            Optional[Path]: Path to the backup file if it was created,
            otherwise :obj:`None`.
        """
        if not self.backup_enabled or not file_path.exists():
            return None

        import shutil
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.parent / f"{file_path.name}.{timestamp}.bak"

        try:
            shutil.copy2(file_path, backup_path)
            logger.info("[FilesystemBackend] Created backup: %s", backup_path)
            return backup_path
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "[FilesystemBackend] Failed to create backup %s: %s",
                file_path,
                exc,
            )
            return None

    # ---------- BaseBackend API ----------

    def read(self, path: str, offset: int = 0, limit: int = 2000) -> str:
        r"""Read text content from a file.

        Args:
            path (str): Logical file path to read.
            offset (int): Byte offset in the file to start reading from.
                (default: :obj:`0`)
            limit (int): Maximum number of bytes to read.
                (default: :obj:`2000`)

        Returns:
            str: File content as a string, or an empty string if the file
            does not exist or is not a regular file.
        """
        file_path = self._resolve(path)
        if not file_path.exists() or not file_path.is_file():
            raise FileNotFoundError(
                f"Cannot read non-regular file: {file_path}"
            )

        with file_path.open("r", encoding=self.default_encoding) as file_obj:
            if offset:
                file_obj.seek(offset)
            return file_obj.read(limit)

    def write(self, path: str, content: str) -> WriteResult:
        r"""Write text content to a file, overwriting existing content.

        If the file already exists and backups are enabled, a timestamped
        backup is created before writing new content.

        Args:
            path (str): Logical file path to write to.
            content (str): Text content to write.

        Returns:
            WriteResult: Result object indicating success or failure and
            any error information.
        """
        file_path = self._resolve(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if file_path.exists():
            self._create_backup(file_path)

        try:
            with file_path.open(
                "w", encoding=self.default_encoding
            ) as file_obj:
                file_obj.write(content)
            return WriteResult(success=True, path=path)
        except Exception as exc:
            logger.error(
                "[FilesystemBackend] Error writing %s: %s",
                file_path,
                exc,
            )
            return WriteResult(success=False, path=path, error=str(exc))

    def edit(self, path: str, old: str, new: str) -> EditResult:
        r"""Edit a file by replacing occurrences of a substring.

        The file is read as text, occurrences of ``old`` are replaced with
        ``new``, and the result is written back. If the file exists and
        backups are enabled, a backup is created before writing.

        Args:
            path (str): Logical file path to edit.
            old (str): Substring to search for.
            new (str): Replacement substring.

        Returns:
            EditResult: Result including the number of replacements and
            any error information.
        """
        file_path = self._resolve(path)
        if not file_path.exists() or not file_path.is_file():
            return EditResult(
                success=False,
                path=path,
                replaced=0,
                error="File not found",
            )

        try:
            text = file_path.read_text(encoding=self.default_encoding)
        except Exception as exc:
            return EditResult(
                success=False,
                path=path,
                replaced=0,
                error=f"Read error: {exc}",
            )

        if old not in text:
            return EditResult(
                success=True,
                path=path,
                replaced=0,
                error=None,
            )

        replaced_count = text.count(old)
        new_text = text.replace(old, new)

        self._create_backup(file_path)

        try:
            file_path.write_text(new_text, encoding=self.default_encoding)
            return EditResult(
                success=True,
                path=path,
                replaced=replaced_count,
                error=None,
            )
        except Exception as exc:
            return EditResult(
                success=False,
                path=path,
                replaced=0,
                error=f"Write error after edit: {exc}",
            )

    def delete(self, path: str, recursive: bool = False) -> DeleteResult:
        r"""Delete a file or directory.

        Args:
            path (str): Logical path to delete.
            recursive (bool): Whether to recursively delete directory
                contents before removing the directory itself.
                (default: :obj:`False`)

        Returns:
            DeleteResult: Result indicating success, number of deleted
            entries, and any error information.
        """
        file_path = self._resolve(path)
        deleted = 0

        try:
            if file_path.is_dir():
                if recursive:
                    for root, dirs, files in os.walk(file_path, topdown=False):
                        for name in files:
                            Path(root, name).unlink()
                            deleted += 1
                        for name in dirs:
                            Path(root, name).rmdir()
                    file_path.rmdir()
                    deleted += 1
                else:
                    file_path.rmdir()
                    deleted += 1
            elif file_path.exists():
                file_path.unlink()
                deleted = 1

            return DeleteResult(
                success=True,
                path=path,
                deleted=deleted,
                error=None,
            )
        except Exception as exc:
            return DeleteResult(
                success=False,
                path=path,
                deleted=deleted,
                error=str(exc),
            )

    def ls_info(self, path: str = "/") -> List[FileInfo]:
        r"""List direct children of a directory with basic metadata.

        Args:
            path (str): Logical directory path to list.
                (default: :obj:`"/"`)

        Returns:
            List[FileInfo]: Metadata entries for files and directories
            directly under the given path. Returns an empty list if the
            path does not exist or is not a directory.
        """
        dir_path = self._resolve(path)
        if not dir_path.exists() or not dir_path.is_dir():
            return []

        result: List[FileInfo] = []
        for entry in dir_path.iterdir():
            result.append(
                FileInfo(
                    path="/" + entry.relative_to(self.root_dir).as_posix(),
                    is_dir=entry.is_dir(),
                    size=None if entry.is_dir() else entry.stat().st_size,
                )
            )
        return result

    def glob_info(self, pattern: str, path: str = "/") -> List[FileInfo]:
        r"""Glob for files and directories under a base path.

        Args:
            pattern (str): Glob pattern (for example, ``"*.md"`` or
                ``"**/*.py"``).
            path (str): Logical base directory path to search from.
                (default: :obj:`"/"`)

        Returns:
            List[FileInfo]: Metadata entries for matching files and
            directories.
        """
        base = self._resolve(path)
        result: List[FileInfo] = []
        for entry in base.glob(pattern):
            result.append(
                FileInfo(
                    path="/" + entry.relative_to(self.root_dir).as_posix(),
                    is_dir=entry.is_dir(),
                    size=None if entry.is_dir() else entry.stat().st_size,
                )
            )
        return result

    def grep_raw(
        self,
        pattern: str,
        path: Optional[str] = None,
    ) -> List[GrepMatch]:
        r"""Search for a pattern in file contents.

        Args:
            pattern (str): Regular expression pattern used to match lines.
            path (str, optional): Optional logical path to restrict the
                search. If provided and points to a file, only that file
                is searched. If :obj:`None`, all files in the sandbox are
                searched.
                (default: :obj:`None`)

        Returns:
            List[GrepMatch]: Matches including file path, line number, and
            matched line content.
        """
        import re as _re

        regex = _re.compile(pattern)
        matches: List[GrepMatch] = []

        def _grep_file(file_path: Path) -> None:
            try:
                text = file_path.read_text(encoding=self.default_encoding)
            except Exception:
                return
            rel_path = "/" + file_path.relative_to(self.root_dir).as_posix()
            for i, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    matches.append(
                        GrepMatch(
                            path=rel_path,
                            line_no=i,  # line number (int)
                            line=line,
                        )
                    )

        if path is not None:
            file_path = self._resolve(path)
            if file_path.is_file():
                _grep_file(file_path)
        else:
            for root, _, files in os.walk(self.root_dir):
                for name in files:
                    _grep_file(Path(root) / name)

        return matches

    def exists(self, path: str) -> bool:
        r"""Check whether a logical path exists in the sandbox.

        Args:
            path (str): Logical path to check.

        Returns:
            bool: :obj:`True` if the resolved path exists, otherwise
            :obj:`False`.
        """
        return self._resolve(path).exists()

    def mkdir(self, path: str) -> WriteResult:
        r"""Create a directory at the given logical path.

        Parent directories are created as needed.

        Args:
            path (str): Logical directory path to create.

        Returns:
            WriteResult: Result indicating success or failure and any
            error message.
        """
        dir_path = self._resolve(path)
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            return WriteResult(success=True, path=path)
        except Exception as exc:
            logger.error(
                "[FilesystemBackend] Error creating dir %s: %s",
                dir_path,
                exc,
            )
            return WriteResult(success=False, path=path, error=str(exc))
