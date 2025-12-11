from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from .types import (
    FileInfo,
    WriteResult,
    EditResult,
    DeleteResult,
    GrepMatch,
)


class BaseBackend(ABC):
    r"""Abstract base class for all storage backends.

    A backend is responsible for raw storage operations, including reading,
    writing, editing, deleting, listing, and searching content. All paths
    passed to a backend are logical paths, represented as POSIX-style
    string paths, and are typically resolved relative to a backend-specific
    root.
    """

    @abstractmethod
    def read(
        self,
        path: str,
        offset: int = 0,
        limit: int = 2000,
    ) -> str:
        r"""Read text content from a file.

        Args:
            path (str): Logical path of the file to read from.
            offset (int): Offset in characters at which to start reading.
                (default: :obj:`0`)
            limit (int): Maximum number of characters to return. Backends
                may choose to ignore or cap this value.
                (default: :obj:`2000`)

        Returns:
            str: File content starting from ``offset`` with at most
            ``limit`` characters.
        """
        raise NotImplementedError

    @abstractmethod
    def write(self, path: str, content: str) -> WriteResult:
        r"""Write text content to a file.

        This method overwrites any existing content at the given logical
        path. Backends may create parent directories as needed, depending
        on their implementation.

        Args:
            path (str): Logical path of the file to write to.
            content (str): Text content to write into the file.

        Returns:
            WriteResult: Result object indicating success or failure and
            any backend-specific metadata.
        """
        raise NotImplementedError

    @abstractmethod
    def edit(self, path: str, old: str, new: str) -> EditResult:
        r"""Edit file content by replacing occurrences of a substring.

        The backend replaces occurrences of ``old`` with ``new`` in the
        file content located at the given logical path. The exact matching
        and replacement behavior may be backend-specific but should be
        documented by concrete implementations.

        Args:
            path (str): Logical path of the file to edit.
            old (str): Substring pattern to search for.
            new (str): Replacement substring to use instead of ``old``.

        Returns:
            EditResult: Result object containing the number of replacements
            performed and any error information.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        path: str,
        recursive: bool = False,
    ) -> DeleteResult:
        r"""Delete a file or directory.

        Args:
            path (str): Logical path of the file or directory to delete.
            recursive (bool): Whether to delete directories and their
                contents recursively. Behavior for non-empty directories
                when ``recursive`` is :obj:`False` is backend-specific.
                (default: :obj:`False`)

        Returns:
            DeleteResult: Result object indicating success, the number of
            deleted items, and any error information.
        """
        raise NotImplementedError

    @abstractmethod
    def ls_info(self, path: str = "/") -> List[FileInfo]:
        r"""List file and directory entries with metadata.

        Args:
            path (str): Logical directory path to list. Implementations
                may treat non-directory paths differently or raise errors.
                (default: :obj:`"/"`)

        Returns:
            List[FileInfo]: List of metadata objects describing the
            entries at the given path.
        """
        raise NotImplementedError

    @abstractmethod
    def glob_info(
        self,
        pattern: str,
        path: str = "/",
    ) -> List[FileInfo]:
        r"""Glob for files under a directory.

        Args:
            pattern (str): Glob pattern used to select entries, for
                example ``"*.md"`` or ``"**/*.py"``. The exact pattern
                syntax may depend on the backend.
            path (str): Logical base path from which the glob search
                should start.
                (default: :obj:`"/"`)

        Returns:
            List[FileInfo]: List of metadata objects for entries that
            match the given pattern relative to the base path.
        """
        raise NotImplementedError

    @abstractmethod
    def grep_raw(
        self,
        pattern: str,
        path: Optional[str] = None,
    ) -> List[GrepMatch]:
        r"""Search for a pattern across files.

        The backend searches file contents for the given pattern and
        returns structured matches. The interpretation of ``pattern``
        (plain text or regular expression) is backend-defined and should
        be documented by concrete implementations.

        Args:
            pattern (str): Search pattern used to locate matches in file
                contents.
            path (str, optional): Optional logical base path used to
                restrict the search scope. If :obj:`None`, the backend may
                search its entire namespace.
                (default: :obj:`None`)

        Returns:
            List[GrepMatch]: List of match objects that describe where
            and how the pattern was found.
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, path: str) -> bool:
        r"""Check whether a path exists in the backend.

        Args:
            path (str): Logical path whose existence should be checked.

        Returns:
            bool: :obj:`True` if the path exists in the backend,
            otherwise :obj:`False`.
        """
        raise NotImplementedError

    @abstractmethod
    def mkdir(self, path: str) -> WriteResult:
        r"""Create a directory.

        Backends may create intermediate parent directories as needed or
        may require them to exist, depending on their implementation.

        Args:
            path (str): Logical directory path to create.

        Returns:
            WriteResult: Result object indicating success or failure and
            any backend-specific metadata produced during creation.
        """
        raise NotImplementedError
