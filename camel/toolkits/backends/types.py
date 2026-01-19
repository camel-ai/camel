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
from datetime import datetime
from typing import List, Optional


@dataclass
class FileInfo:
    r"""Metadata describing a file or directory in a backend.

    This data structure provides lightweight metadata for filesystem- or
    backend-backed entries and is returned by listing and glob operations.

    Attributes:
        path (str): Logical path of the file or directory.
        is_dir (bool): Whether the path represents a directory.
        size (Optional[int]): Size of the file in bytes if applicable.
            For directories or unknown sizes, this may be :obj:`None`.
        modified (Optional[datetime]): Last modification timestamp of the
            entry, if available. Backends that do not track modification
            times may leave this as :obj:`None`.
    """

    path: str
    is_dir: bool
    size: Optional[int] = None
    modified: Optional[datetime] = None


@dataclass
class WriteResult:
    r"""Result of a write or directory creation operation.

    This result is returned by write-like operations, such as file writes
    or directory creation, and indicates whether the operation succeeded.

    Attributes:
        success (bool): Whether the operation completed successfully.
        path (str): Logical path that was written to or created.
        error (Optional[str]): Error message if the operation failed,
            otherwise :obj:`None`.
    """

    success: bool
    path: str
    error: Optional[str] = None


@dataclass
class EditResult:
    r"""Result of an edit or replace operation.

    This result captures both the success status and how many replacements
    were performed during the edit operation.

    Attributes:
        success (bool): Whether the edit operation succeeded.
        path (str): Logical path of the edited file.
        replaced (int): Number of replacements that were performed.
        error (Optional[str]): Error message if the operation failed,
            otherwise :obj:`None`.
    """

    success: bool
    path: str
    replaced: int = 0
    error: Optional[str] = None


@dataclass
class DeleteResult:
    r"""Result of a delete operation.

    This result indicates whether a delete operation succeeded and how
    many filesystem or backend entries were removed.

    Attributes:
        success (bool): Whether the delete operation completed
            successfully.
        path (str): Logical path that was targeted for deletion.
        deleted (int): Number of entries removed, including files and
            directories.
        error (Optional[str]): Error message if the operation failed,
            otherwise :obj:`None`.
    """

    success: bool
    path: str
    deleted: int = 0
    error: Optional[str] = None


@dataclass
class GrepMatch:
    r"""Single text match produced by a grep-like search operation.

    This structure represents a single line-level match within a file and
    may optionally include surrounding context lines.

    Attributes:
        path (str): Logical path of the file containing the match.
        line_no (int): One-based line number where the match occurred.
        line (str): Full text of the matching line.
        context_before (Optional[List[str]]): Optional lines immediately
            preceding the match.
        context_after (Optional[List[str]]): Optional lines immediately
            following the match.
    """

    path: str
    line_no: int
    line: str
    context_before: Optional[List[str]] = None
    context_after: Optional[List[str]] = None


__all__ = [
    "FileInfo",
    "WriteResult",
    "EditResult",
    "DeleteResult",
    "GrepMatch",
]
