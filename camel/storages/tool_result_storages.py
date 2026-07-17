# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

_SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
_RESERVED_PATH_PARTS = {".", ".."}


@dataclass(frozen=True)
class ToolResultRecord:
    r"""A complete externalized tool result and its metadata.

    Args:
        result_id (str): Storage-safe identifier for this result.
        scope_id (str): Agent or application scope that owns the result.
        ref (str): Stable reference shown in model context.
        tool_name (str): Name of the tool that produced the result.
        tool_call_id (str): Identifier of the originating tool call.
        content (str): Complete serialized tool output.
        created_at (float): UNIX timestamp when the result was stored.
        expires_at (Optional[float]): Optional UNIX expiration timestamp.
        original_chars (int): Character length of the complete output.
        sha256 (str): SHA-256 digest of ``content``.
        mime_type (str): MIME type of the stored output.
    """

    result_id: str
    scope_id: str
    ref: str
    tool_name: str
    tool_call_id: str
    content: str
    created_at: float
    expires_at: Optional[float]
    original_chars: int
    sha256: str
    mime_type: str = "text/plain"

    @property
    def expired(self) -> bool:
        r"""Return whether this record has expired."""
        return self.expires_at is not None and time.time() >= self.expires_at

    def metadata_dict(self) -> Dict[str, Any]:
        r"""Serialize metadata without including the potentially large body."""
        data = asdict(self)
        data.pop("content")
        return data

    @classmethod
    def from_metadata(
        cls, metadata: Dict[str, Any], content: str
    ) -> "ToolResultRecord":
        r"""Build a record from separately stored metadata and content."""
        return cls(content=content, **metadata)


class BaseToolResultStore(ABC):
    r"""Storage interface for externalized tool results."""

    @abstractmethod
    def save(self, record: ToolResultRecord) -> None:
        r"""Persist a complete tool result."""

    @abstractmethod
    def get(self, scope_id: str, result_id: str) -> Optional[ToolResultRecord]:
        r"""Load a result, or return ``None`` when it does not exist."""

    @abstractmethod
    def list(
        self,
        scope_id: str,
        tool_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        r"""List newest result metadata in one scope."""

    @abstractmethod
    def delete(self, scope_id: str, result_id: str) -> None:
        r"""Delete one result if it exists."""


class InMemoryToolResultStore(BaseToolResultStore):
    r"""Thread-safe, process-local tool result storage."""

    def __init__(self) -> None:
        self._records: Dict[tuple[str, str], ToolResultRecord] = {}
        self._lock = threading.RLock()

    def save(self, record: ToolResultRecord) -> None:
        with self._lock:
            self._records[(record.scope_id, record.result_id)] = record

    def get(self, scope_id: str, result_id: str) -> Optional[ToolResultRecord]:
        key = (scope_id, result_id)
        with self._lock:
            record = self._records.get(key)
            if record is not None and record.expired:
                self._records.pop(key, None)
                return None
            return record

    def list(
        self,
        scope_id: str,
        tool_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            expired_keys = [
                key
                for key, record in self._records.items()
                if key[0] == scope_id and record.expired
            ]
            for key in expired_keys:
                self._records.pop(key, None)
            records = [
                record
                for (record_scope, _), record in self._records.items()
                if record_scope == scope_id
                and (tool_name is None or record.tool_name == tool_name)
            ]
        records.sort(key=lambda record: record.created_at, reverse=True)
        return [record.metadata_dict() for record in records[:limit]]

    def delete(self, scope_id: str, result_id: str) -> None:
        with self._lock:
            self._records.pop((scope_id, result_id), None)


class FileToolResultStore(BaseToolResultStore):
    r"""File-backed tool result storage for persistence across processes.

    Each result is stored as an ``output.txt`` payload and a separate
    ``metadata.json`` file below ``directory/<scope_id>/<result_id>``.

    Args:
        directory (Union[str, Path]): Root directory for stored results.
    """

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory).expanduser().resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    @staticmethod
    def _validate_id(value: str, label: str) -> None:
        if (
            value in _RESERVED_PATH_PARTS
            or _SAFE_ID_PATTERN.fullmatch(value) is None
        ):
            raise ValueError(f"Invalid {label}: {value!r}")

    def _result_dir(self, scope_id: str, result_id: str) -> Path:
        self._validate_id(scope_id, "scope_id")
        self._validate_id(result_id, "result_id")
        result_dir = (self.directory / scope_id / result_id).resolve()
        try:
            result_dir.relative_to(self.directory)
        except ValueError as exc:
            raise ValueError(
                "Tool result path must stay within the storage directory"
            ) from exc
        return result_dir

    @staticmethod
    def _validate_record_identity(
        record: ToolResultRecord, scope_id: str, result_id: str
    ) -> None:
        if record.scope_id != scope_id or record.result_id != result_id:
            raise ValueError(
                "Tool result metadata identity does not match its path"
            )

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Optional[Path] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                delete=False,
            ) as temporary:
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def save(self, record: ToolResultRecord) -> None:
        result_dir = self._result_dir(record.scope_id, record.result_id)
        metadata = json.dumps(
            record.metadata_dict(), ensure_ascii=False, indent=2
        )
        with self._lock:
            self._atomic_write(result_dir / "output.txt", record.content)
            self._atomic_write(result_dir / "metadata.json", metadata)

    def get(self, scope_id: str, result_id: str) -> Optional[ToolResultRecord]:
        result_dir = self._result_dir(scope_id, result_id)
        try:
            with self._lock:
                metadata = json.loads(
                    (result_dir / "metadata.json").read_text(encoding="utf-8")
                )
                content = (result_dir / "output.txt").read_text(
                    encoding="utf-8"
                )
        except FileNotFoundError:
            return None

        record = ToolResultRecord.from_metadata(metadata, content)
        self._validate_record_identity(record, scope_id, result_id)
        if record.expired:
            self.delete(scope_id, result_id)
            return None
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        if digest != record.sha256:
            raise ValueError(f"Tool result {record.ref} failed SHA-256 check")
        return record

    def list(
        self,
        scope_id: str,
        tool_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        self._validate_id(scope_id, "scope_id")
        scope_dir = (self.directory / scope_id).resolve()
        try:
            scope_dir.relative_to(self.directory)
        except ValueError as exc:
            raise ValueError(
                "Tool result path must stay within the storage directory"
            ) from exc
        if not scope_dir.exists():
            return []

        records: List[Dict[str, Any]] = []
        with self._lock:
            for result_dir in scope_dir.iterdir():
                if not result_dir.is_dir():
                    continue
                try:
                    metadata = json.loads(
                        (result_dir / "metadata.json").read_text(
                            encoding="utf-8"
                        )
                    )
                    record = ToolResultRecord.from_metadata(metadata, "")
                    self._validate_record_identity(
                        record, scope_id, result_dir.name
                    )
                    expired = record.expired
                except (
                    FileNotFoundError,
                    ValueError,
                    json.JSONDecodeError,
                    TypeError,
                ):
                    continue
                if expired:
                    self.delete(scope_id, result_dir.name)
                    continue
                if tool_name is None or record.tool_name == tool_name:
                    records.append(record.metadata_dict())
        records.sort(key=lambda record: record["created_at"], reverse=True)
        return records[:limit]

    def delete(self, scope_id: str, result_id: str) -> None:
        result_dir = self._result_dir(scope_id, result_id)
        with self._lock:
            for name in ("output.txt", "metadata.json"):
                try:
                    (result_dir / name).unlink()
                except FileNotFoundError:
                    pass
            try:
                result_dir.rmdir()
            except (FileNotFoundError, OSError):
                pass
            try:
                result_dir.parent.rmdir()
            except (FileNotFoundError, OSError):
                pass
