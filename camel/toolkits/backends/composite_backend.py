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

from dataclasses import dataclass
from typing import Dict, List, Optional

from .base import BaseBackend
from .types import (
    DeleteResult,
    EditResult,
    FileInfo,
    GrepMatch,
    WriteResult,
)


@dataclass
class Route:
    r"""Routing rule that maps a path prefix to a backend.

    A route associates a normalized logical path prefix with a backend that
    is responsible for handling all operations under that prefix.

    Attributes:
        prefix (str): Normalized logical path prefix, including leading
            and trailing slashes (for example, ``"/temp/"``).
        backend (BaseBackend): Backend responsible for paths that start
            with the given prefix.
    """

    prefix: str
    backend: BaseBackend


class CompositeBackend(BaseBackend):
    r"""Backend that routes operations to different backends by path prefix.

    This backend does not store data itself. Instead, it delegates each
    operation to one of several underlying backends based on the logical
    path being accessed.

    Routing is performed using longest-prefix matching against a set of
    configured path prefixes. If no prefix matches a given path, the
    default backend is used.

    Example routing configuration:
        - ``"/temp/"``     → in-memory backend
        - ``"/persist/"``  → filesystem backend
        - otherwise        → default backend
    """

    def __init__(self, default: BaseBackend, routes: Dict[str, BaseBackend]):
        r"""Initialize the composite backend.

        Args:
            default (BaseBackend): Backend used when no route prefix
                matches the requested logical path.
            routes (Dict[str, BaseBackend]): Mapping from logical path
                prefixes to backends. Prefixes are normalized internally
                to ensure consistent routing behavior.
        """
        self.default = default
        self.routes: List[Route] = [
            Route(self._normalize_prefix(prefix), backend)
            for prefix, backend in routes.items()
        ]

    def _normalize_prefix(self, prefix: str) -> str:
        r"""Normalize a path prefix to a canonical form.

        The normalized form always includes a leading and trailing slash,
        which simplifies prefix matching during backend selection.

        Args:
            prefix (str): Raw logical path prefix.

        Returns:
            str: Normalized prefix in the form ``"/prefix/"``.
        """
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        if not prefix.endswith("/"):
            prefix += "/"
        return prefix

    def _select(self, path: str) -> BaseBackend:
        r"""Select the backend responsible for a logical path.

        Args:
            path (str): Logical path that determines routing behavior.

        Returns:
            BaseBackend: Backend selected based on the configured routing
            prefixes, or the default backend if no prefix matches.
        """
        best_route = None
        best_length = -1

        for route in self.routes:
            if path.startswith(route.prefix):
                prefix_len = len(route.prefix)
                if prefix_len > best_length:
                    best_route = route
                    best_length = prefix_len

        if best_route is not None:
            return best_route.backend

        return self.default

    def read(self, path: str, offset: int = 0, limit: int = 2000) -> str:
        r"""Read text content from a logical path.

        Args:
            path (str): Logical path of the file to read.
            offset (int): Offset in characters at which to start reading.
                (default: :obj:`0`)
            limit (int): Maximum number of characters to return.
                (default: :obj:`2000`)

        Returns:
            str: File content read from the selected backend.
        """
        return self._select(path).read(path, offset, limit)

    def write(self, path: str, content: str) -> WriteResult:
        r"""Write text content to a logical path.

        Args:
            path (str): Logical path of the file to write to.
            content (str): Text content to write.

        Returns:
            WriteResult: Result object describing the write outcome.
        """
        return self._select(path).write(path, content)

    def edit(self, path: str, old: str, new: str) -> EditResult:
        r"""Edit file content by replacing occurrences of a substring.

        Args:
            path (str): Logical path of the file to edit.
            old (str): Substring to search for.
            new (str): Replacement substring.

        Returns:
            EditResult: Result object describing replacement outcomes.
        """
        return self._select(path).edit(path, old, new)

    def delete(self, path: str, recursive: bool = False) -> DeleteResult:
        r"""Delete a file or directory at a logical path.

        Args:
            path (str): Logical path to delete.
            recursive (bool): Whether directories should be deleted
                recursively.
                (default: :obj:`False`)

        Returns:
            DeleteResult: Result object describing deletion outcomes.
        """
        return self._select(path).delete(path, recursive)

    def ls_info(self, path: str = "/") -> List[FileInfo]:
        r"""List files and directories with metadata.

        Args:
            path (str): Logical directory path to list.
                (default: :obj:`"/"`)

        Returns:
            List[FileInfo]: Metadata for entries under the given path.
        """
        return self._select(path).ls_info(path)

    def glob_info(self, pattern: str, path: str = "/") -> List[FileInfo]:
        r"""Glob for matching files under a directory.

        Args:
            pattern (str): Glob pattern used to select entries.
            path (str): Logical base path to search from.
                (default: :obj:`"/"`)

        Returns:
            List[FileInfo]: Metadata objects for matching entries.
        """
        return self._select(path).glob_info(pattern, path)

    def grep_raw(
        self,
        pattern: str,
        path: Optional[str] = None,
    ) -> List[GrepMatch]:
        r"""Search for a pattern across file contents.

        If a logical path is provided, the search is delegated to the
        backend responsible for that path. If no path is provided, the
        search is performed across all configured backends and results
        are deduplicated.

        Args:
            pattern (str): Search pattern used to locate matches.
            path (str, optional): Logical base path that restricts the
                search scope. If :obj:`None`, all backends are searched.
                (default: :obj:`None`)

        Returns:
            List[GrepMatch]: Deduplicated list of matches across backends.
        """
        if path is not None:
            return self._select(path).grep_raw(pattern, path)

        matches: List[GrepMatch] = []
        seen = set()

        seen = set()
        seen_backends = set()
        matches = []

        for route in self.routes:
            backend = route.backend
            if backend in seen_backends:
                continue
            seen_backends.add(backend)

            for match in backend.grep_raw(pattern, None):
                key = (match.path, match.line_no, match.line)
                if key not in seen:
                    seen.add(key)
                    matches.append(match)

        for match in self.default.grep_raw(pattern, None):
            key = (match.path, match.line_no, match.line)
            if key not in seen:
                seen.add(key)
                matches.append(match)

        return matches

    def exists(self, path: str) -> bool:
        r"""Check whether a logical path exists.

        Args:
            path (str): Logical path whose existence should be checked.

        Returns:
            bool: :obj:`True` if the path exists, otherwise :obj:`False`.
        """
        return self._select(path).exists(path)

    def mkdir(self, path: str) -> WriteResult:
        r"""Create a directory at a logical path.

        Args:
            path (str): Logical directory path to create.

        Returns:
            WriteResult: Result object describing the creation outcome.
        """
        return self._select(path).mkdir(path)
