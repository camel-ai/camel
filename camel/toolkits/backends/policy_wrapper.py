from __future__ import annotations

from typing import Callable, List, Optional

from .base import BaseBackend
from .types import (
    FileInfo,
    WriteResult,
    EditResult,
    DeleteResult,
    GrepMatch,
)

PolicyFn = Callable[[str, str], None]
# Operation name and logical path. The policy may either return normally
# or raise an exception (for example, PermissionError) to deny the action.


class PolicyWrapper(BaseBackend):
    r"""Backend wrapper that enforces access policies on backend operations.

    This backend delegates all storage operations to an underlying backend
    but applies a user-defined policy function before each operation. The
    policy function is responsible for allowing or denying operations by
    raising an exception when access should be restricted.

    This wrapper is useful for implementing permission checks, read-only
    modes, path-based access control, or auditing logic without modifying
    the underlying backend implementation.
    """

    def __init__(self, backend: BaseBackend, policy: PolicyFn):
        r"""Initialize the policy-enforcing backend wrapper.

        Args:
            backend (BaseBackend): Backend to which operations are
                delegated after policy validation.
            policy (PolicyFn): Callable that receives the operation name
                and logical path. The function should return normally to
                allow the operation, or raise an exception to deny it.
        """
        self.backend = backend
        self.policy = policy

    def _check(self, operation: str, path: str) -> None:
        r"""Apply the policy check for an operation and logical path.

        Args:
            operation (str): Name of the operation being performed,
                such as ``"read"``, ``"write"``, or ``"delete"``.
            path (str): Logical path on which the operation is attempted.

        Raises:
            Exception: Any exception raised by the policy function is
            propagated to the caller to signal denial of the operation.
        """
        self.policy(operation, path)

    def read(self, path: str, offset: int = 0, limit: int = 2000) -> str:
        r"""Read text content from a logical path after policy validation.

        Args:
            path (str): Logical file path to read.
            offset (int): Offset in characters to start reading from.
                (default: :obj:`0`)
            limit (int): Maximum number of characters to return.
                (default: :obj:`2000`)

        Returns:
            str: File content returned by the underlying backend.
        """
        self._check("read", path)
        return self.backend.read(path, offset, limit)

    def write(self, path: str, content: str) -> WriteResult:
        r"""Write text content to a logical path after policy validation.

        Args:
            path (str): Logical file path to write to.
            content (str): Text content to write.

        Returns:
            WriteResult: Result describing the write outcome.
        """
        self._check("write", path)
        return self.backend.write(path, content)

    def edit(self, path: str, old: str, new: str) -> EditResult:
        r"""Edit file content after policy validation.

        Args:
            path (str): Logical file path to edit.
            old (str): Substring to search for.
            new (str): Replacement substring.

        Returns:
            EditResult: Result describing the edit outcome.
        """
        self._check("edit", path)
        return self.backend.edit(path, old, new)

    def delete(self, path: str, recursive: bool = False) -> DeleteResult:
        r"""Delete a file or directory after policy validation.

        Args:
            path (str): Logical path to delete.
            recursive (bool): Whether to recursively delete directory
                contents before removing the directory.
                (default: :obj:`False`)

        Returns:
            DeleteResult: Result describing the deletion outcome.
        """
        self._check("delete", path)
        return self.backend.delete(path, recursive)

    def ls_info(self, path: str = "/") -> List[FileInfo]:
        r"""List directory contents after policy validation.

        Args:
            path (str): Logical directory path to list.
                (default: :obj:`"/"`)

        Returns:
            List[FileInfo]: Metadata for entries under the given path.
        """
        self._check("ls", path)
        return self.backend.ls_info(path)

    def glob_info(self, pattern: str, path: str = "/") -> List[FileInfo]:
        r"""Glob for matching paths after policy validation.

        Args:
            pattern (str): Glob pattern used to match entries.
            path (str): Logical base path used for the glob operation.
                (default: :obj:`"/"`)

        Returns:
            List[FileInfo]: Metadata for matching entries.
        """
        self._check("glob", path)
        return self.backend.glob_info(pattern, path)

    def grep_raw(
        self,
        pattern: str,
        path: Optional[str] = None,
    ) -> List[GrepMatch]:
        r"""Search for a pattern in file contents after policy validation.

        If a logical path is provided, the policy is checked for that path.
        If no path is provided, the search is delegated directly to the
        underlying backend.

        Args:
            pattern (str): Search pattern used to locate matches.
            path (str, optional): Optional logical path to restrict the
                search scope.
                (default: :obj:`None`)

        Returns:
            List[GrepMatch]: Matches returned by the underlying backend.
        """
        if path is not None:
            self._check("grep", path)
        return self.backend.grep_raw(pattern, path)

    def exists(self, path: str) -> bool:
        r"""Check for path existence after policy validation.

        Args:
            path (str): Logical path to check.

        Returns:
            bool: :obj:`True` if the path exists, otherwise :obj:`False`.
        """
        self._check("exists", path)
        return self.backend.exists(path)

    def mkdir(self, path: str) -> WriteResult:
        r"""Create a directory after policy validation.

        Args:
            path (str): Logical directory path to create.

        Returns:
            WriteResult: Result describing the directory creation outcome.
        """
        self._check("mkdir", path)
        return self.backend.mkdir(path)
