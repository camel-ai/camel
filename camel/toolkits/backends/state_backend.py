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

from typing import Dict, List, Optional

from .base import BaseBackend
from .types import (
    DeleteResult,
    EditResult,
    FileInfo,
    GrepMatch,
    WriteResult,
)


class StateBackend(BaseBackend):
    r"""In-memory ephemeral backend for logical paths and content.

    This backend stores all file contents in memory using a simple mapping
    from logical path to text content. Directories are not stored
    explicitly; instead, they are inferred from path prefixes.

    This implementation is useful for tests, temporary state, or scenarios
    where persistence across process restarts is not required.
    """

    def __init__(self) -> None:
        r"""Initialize the in-memory backend.

        The backend starts with an empty mapping from normalized logical
        paths to file content.
        """
        # Map "path" -> content
        self._files: Dict[str, str] = {}

    # ---------- helpers ----------

    def _norm(self, path: str) -> str:
        r"""Normalize a logical path to a canonical form.

        Paths are normalized to always start with a leading slash, such as
        ``"/foo/bar.txt"``. No other normalization (for example, resolving
        ``".."`` segments) is performed.

        Args:
            path (str): Raw logical path string.

        Returns:
            str: Normalized logical path with a leading slash.
        """
        if not path.startswith("/"):
            path = "/" + path
        return path

    # ---------- BaseBackend API ----------

    def read(self, path: str, offset: int = 0, limit: int = 2000) -> str:
        r"""Read text content from a logical path.

        Args:
            path (str): Logical file path to read from.
            offset (int): Character offset from which to start reading.
                (default: :obj:`0`)
            limit (int): Maximum number of characters to return.
                (default: :obj:`2000`)

        Returns:
            str: Substring of the stored content starting at ``offset``
            with length at most ``limit``. Returns an empty string if the
            file does not exist.
        """
        normalized = self._norm(path)
        content = self._files.get(normalized, "")
        return content[offset : offset + limit]

    def write(self, path: str, content: str) -> WriteResult:
        r"""Write text content to a logical path.

        This method overwrites any existing content associated with the
        normalized logical path.

        Args:
            path (str): Logical file path to write to.
            content (str): Text content to store.

        Returns:
            WriteResult: Result indicating success and the normalized path.
        """
        normalized = self._norm(path)
        self._files[normalized] = content
        return WriteResult(success=True, path=normalized)

    def edit(self, path: str, old: str, new: str) -> EditResult:
        r"""Edit text content by replacing occurrences of a substring.

        Args:
            path (str): Logical file path to edit.
            old (str): Substring to search for in the content.
            new (str): Replacement substring.

        Returns:
            EditResult: Result indicating success, number of replacements,
            and any error information. If the file does not exist, the
            operation fails with an error message.
        """
        normalized = self._norm(path)
        if normalized not in self._files:
            return EditResult(
                success=False,
                path=normalized,
                replaced=0,
                error="File not found",
            )

        current = self._files[normalized]
        if old not in current:
            # No occurrences, but this is not considered an error.
            return EditResult(
                success=True,
                path=normalized,
                replaced=0,
                error=None,
            )

        replaced = current.count(old)
        self._files[normalized] = current.replace(old, new)
        return EditResult(
            success=True,
            path=normalized,
            replaced=replaced,
            error=None,
        )

    def delete(self, path: str, recursive: bool = False) -> DeleteResult:
        r"""Delete a file or a group of files under a logical path.

        Args:
            path (str): Logical path to delete.
            recursive (bool): If :obj:`True`, delete all files whose
                paths are equal to the normalized path or start with that
                path plus a trailing slash. If :obj:`False`, only delete
                the exact path entry.
                (default: :obj:`False`)

        Returns:
            DeleteResult: Result indicating success, number of deleted
            entries, and error information if any.
        """
        normalized = self._norm(path)
        deleted = 0

        if recursive:
            prefix = normalized.rstrip("/") + "/"
            to_delete = [
                key
                for key in self._files
                if key == normalized or key.startswith(prefix)
            ]
            for key in to_delete:
                del self._files[key]
                deleted += 1
        else:
            if normalized in self._files:
                del self._files[normalized]
                deleted = 1

        return DeleteResult(
            success=True,
            path=normalized,
            deleted=deleted,
            error=None,
        )

    def ls_info(self, path: str = "/") -> List[FileInfo]:
        r"""List inferred directory entries and files under a logical path.

        Directories are inferred from prefixes of stored file paths rather
        than being explicitly stored.

        Args:
            path (str): Logical directory path to list.
                (default: :obj:`"/"`)

        Returns:
            List[FileInfo]: Metadata entries for direct children under the
            given logical path. Directory entries have ``is_dir=True`` and
            ``size=None``; file entries have ``is_dir=False`` and their
            content length as size.
        """
        base = self._norm(path).rstrip("/") + "/"
        results: List[FileInfo] = []
        seen_dirs = set()

        for stored_path, content in self._files.items():
            if not stored_path.startswith(base):
                continue
            suffix = stored_path[len(base) :]
            if "/" in suffix:
                dirname = suffix.split("/", 1)[0]
                if dirname not in seen_dirs:
                    seen_dirs.add(dirname)
                    results.append(
                        FileInfo(
                            path=base + dirname,
                            is_dir=True,
                            size=None,
                        )
                    )
            else:
                results.append(
                    FileInfo(
                        path=stored_path,
                        is_dir=False,
                        size=len(content),
                    )
                )

        return results

    def glob_info(self, pattern: str, path: str = "/") -> List[FileInfo]:
        r"""Glob for matching files under a logical base path.

        Args:
            pattern (str): Glob pattern applied to normalized paths.
            path (str): Logical base directory path to search from.
                (default: :obj:`"/"`)

        Returns:
            List[FileInfo]: Metadata entries for files whose paths match
            the expanded glob pattern.
        """
        import fnmatch

        base = self._norm(path).rstrip("/") + "/"
        full_pattern = base + pattern.lstrip("/")
        results: List[FileInfo] = []

        for stored_path, content in self._files.items():
            if fnmatch.fnmatch(stored_path, full_pattern):
                results.append(
                    FileInfo(
                        path=stored_path,
                        is_dir=False,
                        size=len(content),
                    )
                )

        return results

    def grep_raw(
        self,
        pattern: str,
        path: Optional[str] = None,
    ) -> List[GrepMatch]:
        r"""Search for a pattern in stored file contents.

        Args:
            pattern (str): Regular expression pattern used to match lines.
            path (str, optional): Optional logical path to restrict the
                search to a single file. If :obj:`None`, all files are
                searched.
                (default: :obj:`None`)

        Returns:
            List[GrepMatch]: List of matches including path, line number,
            and matched line text.
        """
        import re as _re

        regex = _re.compile(pattern)
        matches: List[GrepMatch] = []

        # If a specific file is given, only search that file; otherwise,
        # search all known files.
        if path is not None:
            paths = [self._norm(path)]
        else:
            paths = list(self._files.keys())

        for stored_path in paths:
            text = self._files.get(stored_path, "")
            for i, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    matches.append(
                        GrepMatch(
                            path=stored_path,
                            line_no=i,  # 1-based line number
                            line=line,  # full line text
                        )
                    )

        return matches

    def exists(self, path: str) -> bool:
        r"""Check whether a logical path exists.

        A path is considered to exist if a file is stored at the normalized
        path or if any stored file path has the normalized path as a
        directory prefix.

        Args:
            path (str): Logical path to check.

        Returns:
            bool: :obj:`True` if the path exists as a file or inferred
            directory, otherwise :obj:`False`.
        """
        normalized = self._norm(path)
        if normalized in self._files:
            return True

        prefix = normalized.rstrip("/") + "/"
        return any(key.startswith(prefix) for key in self._files)

    def mkdir(self, path: str) -> WriteResult:
        r"""Create a directory at a logical path.

        Directories are implicit in this backend and do not require
        explicit storage, so this method simply normalizes the path and
        returns a successful result.

        Args:
            path (str): Logical directory path to create.

        Returns:
            WriteResult: Result indicating success and the normalized path.
        """
        normalized = self._norm(path)
        return WriteResult(success=True, path=normalized, error=None)
