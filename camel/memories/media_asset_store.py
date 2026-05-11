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

"""Media asset store for externalizing binary media from vector DB payloads."""

from __future__ import annotations

import json
import shutil
import tempfile
from concurrent.futures import Future, ThreadPoolExecutor
from io import BytesIO
from pathlib import Path, PurePath
from threading import Lock
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, TypeVar

from camel.memories.multimodal_metadata import MultimodalMetadata
from camel.memories.records import MemoryRecord

if TYPE_CHECKING:
    from PIL import Image

    from camel.storages.key_value_storages.base import BaseKeyValueStorage
    from camel.storages.object_storages.base import BaseObjectStorage

T = TypeVar("T")


class MediaAssetStore:
    r"""Manages binary media assets separately from vector DB payloads.

    Default behavior: stores media as files on local filesystem under
    ``local_cache_dir``. Optionally delegates to a :obj:`BaseObjectStorage`
    implementation for cloud storage (S3, Azure, GCS).

    Storage path format: ``{local_cache_dir}/{agent_id}/{uuid}_{index}.{ext}``

    Args:
        object_storage: Cloud storage backend. When None, local filesystem
            is used. (default: :obj:`None`)
        local_cache_dir: Directory for local file caching.
            (default: :obj:`".camel_media_cache"`)
        remote_prefix: Remote object prefix used when ``object_storage`` is
            configured. (default: :obj:`"camel-media"`)
        io_workers: Number of worker threads for upload/download/store I/O.
            Use 1 to disable threaded parallelism. (default: :obj:`4`)
        metadata_storage: Optional key-value storage used to persist remote
            manifest metadata across machines. When None, a local manifest
            file is used as fallback. (default: :obj:`None`)
    """

    _METADATA_RECORD_KIND = "camel_media_asset_remote_refs"

    def __init__(
        self,
        object_storage: Optional["BaseObjectStorage"] = None,
        local_cache_dir: str = ".camel_media_cache",
        remote_prefix: str = "camel-media",
        io_workers: int = 4,
        metadata_storage: Optional["BaseKeyValueStorage"] = None,
    ) -> None:
        self._object_storage = object_storage
        self._local_cache_dir = Path(local_cache_dir)
        self._remote_prefix = PurePath(remote_prefix)
        self._io_workers = max(1, io_workers)
        self._manifest_lock = Lock()
        self._metadata_storage = metadata_storage
        self._executor: Optional[ThreadPoolExecutor] = None
        if self._io_workers > 1:
            self._executor = ThreadPoolExecutor(
                max_workers=self._io_workers,
                thread_name_prefix="camel-media",
            )
        self._local_cache_dir.mkdir(parents=True, exist_ok=True)

    def store_media(
        self,
        record: MemoryRecord,
        agent_id: str = "",
    ) -> Dict[str, str]:
        r"""Extract media from record, store externally, return URI references.

        The original record is NOT modified. Callers should merge the
        returned dict into record.extra_info.

        Args:
            record: MemoryRecord containing images/videos.
            agent_id: Agent identifier for directory namespacing.

        Returns:
            Dict mapping media_ref keys to URI strings.
        """
        refs: Dict[str, str] = {}
        media_dir = self._get_media_dir(agent_id)
        media_dir.mkdir(parents=True, exist_ok=True)
        jobs: List[tuple[str, Callable[[], str]]] = []

        # Store images
        if record.message.image_list:
            for idx, img in enumerate(record.message.image_list):
                jobs.append(
                    (
                        f"image_ref_{idx}",
                        lambda img=img, idx=idx: self._store_image(
                            img, media_dir, agent_id, str(record.uuid), idx
                        ),
                    )
                )

        # Store video
        if record.message.video_bytes:
            jobs.append(
                (
                    "video_ref",
                    lambda: self._store_video(
                        record.message.video_bytes,
                        media_dir,
                        agent_id,
                        str(record.uuid),
                    ),
                )
            )

        # Store audio
        if getattr(record.message, "audio_bytes", None):
            jobs.append(
                (
                    "audio_ref",
                    lambda: self._store_audio(
                        record.message.audio_bytes,
                        media_dir,
                        agent_id,
                        str(record.uuid),
                        getattr(record.message, "audio_format", None),
                    ),
                )
            )

        refs = self._run_jobs(jobs)
        self._record_remote_refs(agent_id, list(refs.values()))

        return refs

    def restore_media(self, record: MemoryRecord) -> MemoryRecord:
        r"""Restore media from external URIs back into a MemoryRecord.

        Reads media_refs from record.extra_info, loads bytes from storage,
        and populates image_list / video_bytes on the record's message.

        Args:
            record: MemoryRecord with media_refs in extra_info.

        Returns:
            MemoryRecord with image_list and video_bytes populated
            from external storage.
        """
        extra = dict(record.extra_info)
        mmeta = MultimodalMetadata.from_extra_info(extra)

        if not mmeta.media_refs:
            return record

        # Restore images and video
        from PIL import Image

        image_refs: List[str] = []
        video_ref: Optional[str] = None
        audio_ref: Optional[str] = None

        for ref in mmeta.media_refs:
            # Video refs contain "_video." in the path
            if "_video." in ref:
                video_ref = ref
            elif "_audio." in ref:
                audio_ref = ref
            else:
                image_refs.append(ref)

        image_bytes_list = self._run_jobs(
            [(str(idx), lambda ref=ref: self._load_bytes(ref))
             for idx, ref in enumerate(image_refs)]
        )
        images: List[Image.Image] = []
        for idx in range(len(image_refs)):
            img = Image.open(BytesIO(image_bytes_list[str(idx)]))
            images.append(img)

        if images:
            record.message.image_list = images

        # Restore video
        if video_ref:
            record.message.video_bytes = self._load_bytes(video_ref)

        # Restore audio
        if audio_ref:
            record.message.audio_bytes = self._load_bytes(audio_ref)
            record.message.audio_format = self._infer_audio_format(audio_ref)

        return record

    def _store_image(
        self,
        img: "Image.Image",
        parent_dir: Path,
        agent_id: str,
        record_uuid: str,
        index: int,
    ) -> str:
        r"""Store a PIL Image to local filesystem, return file:// URI."""
        fmt = getattr(img, "format", None) or "PNG"
        filename = f"{record_uuid}_{index}.{fmt.lower()}"
        filepath = parent_dir / filename

        # Atomic write: temp file + rename
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=parent_dir, delete=False
        ) as tmp:
            img.save(tmp, format=fmt)
            temp_path = Path(tmp.name)
        temp_path.rename(filepath)

        return self._finalize_stored_file(filepath, agent_id)

    def _store_video(
        self,
        video_bytes: bytes,
        parent_dir: Path,
        agent_id: str,
        record_uuid: str,
    ) -> str:
        r"""Store video bytes to local filesystem, return file:// URI."""
        filename = f"{record_uuid}_video.mp4"
        filepath = parent_dir / filename
        filepath.write_bytes(video_bytes)
        return self._finalize_stored_file(filepath, agent_id)

    def _store_audio(
        self,
        audio_bytes: bytes,
        parent_dir: Path,
        agent_id: str,
        record_uuid: str,
        audio_format: Optional[str],
    ) -> str:
        r"""Store audio bytes to local filesystem, return file:// URI."""
        normalized_format = (audio_format or "wav").lower()
        filename = f"{record_uuid}_audio.{normalized_format}"
        filepath = parent_dir / filename
        filepath.write_bytes(audio_bytes)
        return self._finalize_stored_file(filepath, agent_id)

    def _load_bytes(self, uri: str) -> bytes:
        r"""Load media bytes from a URI (file:// or cloud)."""
        if uri.startswith("file://"):
            path = Path(uri[len("file://"):])
            if not path.exists():
                raise FileNotFoundError(
                    f"Media file not found: {path}. "
                    f"Ensure MediaAssetStore is initialized with the same "
                    f"local_cache_dir on both store and restore calls."
                )
            return path.read_bytes()
        elif self._object_storage is not None:
            remote_path = self._remote_path_from_uri(uri)
            local_cache_path = self._local_path_for_remote(remote_path)
            if local_cache_path.exists():
                return local_cache_path.read_bytes()

            local_cache_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=local_cache_path.parent, delete=False
            ) as tmp:
                tmp_path = Path(tmp.name)
            self._object_storage.download_file(tmp_path, remote_path)
            tmp_path.rename(local_cache_path)
            return local_cache_path.read_bytes()
        else:
            raise ValueError(
                f"Unsupported URI scheme or no object_storage configured: {uri}"
            )

    def _get_media_dir(self, agent_id: str) -> Path:
        r"""Get the media directory for an agent."""
        return self._local_cache_dir / (agent_id or "default")

    def _infer_audio_format(self, uri: str) -> str:
        r"""Infer audio format from URI suffix."""
        suffix = Path(uri).suffix.lower().lstrip(".")
        return suffix or "wav"

    def _finalize_stored_file(self, local_path: Path, agent_id: str) -> str:
        r"""Upload to object storage when configured, otherwise return file URI."""
        if self._object_storage is None:
            return f"file://{local_path.absolute()}"

        remote_path = self._remote_path(agent_id, local_path.name)
        self._object_storage.upload_file(local_path, remote_path)
        return self._remote_uri(remote_path)

    def _remote_path(self, agent_id: str, filename: str) -> PurePath:
        r"""Build a remote object path for an agent-scoped asset."""
        return self._remote_prefix / (agent_id or "default") / filename

    def _remote_uri(self, remote_path: PurePath) -> str:
        r"""Build a serialized URI for remote object storage references."""
        return f"remote://{remote_path.as_posix()}"

    def _remote_path_from_uri(self, uri: str) -> PurePath:
        r"""Parse a remote URI or legacy plain path into a remote path."""
        if uri.startswith("remote://"):
            return PurePath(uri[len("remote://"):])
        return PurePath(uri)

    def _local_path_for_remote(self, remote_path: PurePath) -> Path:
        r"""Map a remote path to the local cache path."""
        parts = remote_path.parts
        prefix_parts = self._remote_prefix.parts
        if parts[: len(prefix_parts)] == prefix_parts:
            parts = parts[len(prefix_parts) :]
        return self._local_cache_dir.joinpath(*parts)

    def clear(self, agent_id: str = "") -> None:
        r"""Remove all cached media for an agent (or all if agent_id is empty).

        Args:
            agent_id: If non-empty, only clear media for this agent.
                If empty, clear all media. (default: :obj:`""`)
        """
        if agent_id:
            self._delete_remote_refs(agent_id)
            shutil.rmtree(self._get_media_dir(agent_id), ignore_errors=True)
        else:
            self._delete_remote_refs()
            shutil.rmtree(self._local_cache_dir, ignore_errors=True)
            self._local_cache_dir.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        r"""Release background resources owned by this store."""
        if self._executor is not None:
            self._executor.shutdown(wait=True, cancel_futures=False)
            self._executor = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def _run_jobs(self, jobs: List[tuple[str, Callable[[], T]]]) -> Dict[str, T]:
        r"""Run I/O jobs sequentially or via the shared thread pool."""
        if not jobs:
            return {}
        if self._executor is None or len(jobs) == 1:
            return {key: job() for key, job in jobs}

        futures: Dict[str, Future[T]] = {
            key: self._executor.submit(job) for key, job in jobs
        }
        return {key: future.result() for key, future in futures.items()}

    def _manifest_path(self, agent_id: str) -> Path:
        r"""Return the manifest path for remote refs under an agent namespace."""
        return self._get_media_dir(agent_id) / ".remote_manifest.json"

    def _record_remote_refs(self, agent_id: str, refs: List[str]) -> None:
        r"""Persist remote refs so clear() can delete them later."""
        if self._object_storage is None:
            return
        remote_refs = sorted(ref for ref in refs if ref.startswith("remote://"))
        if not remote_refs:
            return

        with self._manifest_lock:
            existing = set(self._load_remote_refs(agent_id))
            existing.update(remote_refs)
            self._save_remote_refs(agent_id, sorted(existing))

    def _delete_remote_refs(self, agent_id: str = "") -> None:
        r"""Delete all tracked remote refs for one agent or the whole cache."""
        if self._object_storage is None:
            return

        refs_to_delete = self._load_all_remote_refs(agent_id)

        self._run_jobs(
            [
                (
                    ref,
                    lambda ref=ref: self._object_storage.delete_file(
                        self._remote_path_from_uri(ref)
                    ),
                )
                for ref in sorted(set(refs_to_delete))
            ]
        )
        self._clear_remote_refs(agent_id)

    def _load_all_remote_refs(self, agent_id: str = "") -> List[str]:
        r"""Load tracked remote refs for one agent or all agents."""
        if self._metadata_storage is not None:
            records = self._load_metadata_records()
            if agent_id:
                for record in records:
                    if record["agent_id"] == (agent_id or "default"):
                        return list(record.get("remote_refs", []))
                return []

            refs: List[str] = []
            for record in records:
                refs.extend(record.get("remote_refs", []))
            return refs

        manifest_paths: List[Path]
        if agent_id:
            manifest_paths = [self._manifest_path(agent_id)]
        else:
            manifest_paths = list(
                self._local_cache_dir.glob("*/.remote_manifest.json")
            )

        refs_to_delete: List[str] = []
        for manifest_path in manifest_paths:
            refs_to_delete.extend(self._read_manifest_file(manifest_path))
        return refs_to_delete

    def _load_remote_refs(self, agent_id: str) -> List[str]:
        r"""Load tracked remote refs for one agent."""
        return self._load_all_remote_refs(agent_id)

    def _save_remote_refs(self, agent_id: str, refs: List[str]) -> None:
        r"""Persist tracked remote refs for one agent."""
        normalized_agent_id = agent_id or "default"
        if self._metadata_storage is not None:
            metadata_records = self._load_metadata_records()
            metadata_records = [
                record
                for record in metadata_records
                if record["agent_id"] != normalized_agent_id
            ]
            metadata_records.append(
                self._metadata_record(normalized_agent_id, refs)
            )
            self._rewrite_metadata_records(*metadata_records)
            return

        manifest_path = self._manifest_path(agent_id)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(refs), encoding="utf-8")

    def _clear_remote_refs(self, agent_id: str = "") -> None:
        r"""Clear persisted remote ref manifests for one agent or all agents."""
        if self._metadata_storage is not None:
            metadata_records = self._load_metadata_records()
            if agent_id:
                normalized_agent_id = agent_id or "default"
                metadata_records = [
                    record
                    for record in metadata_records
                    if record["agent_id"] != normalized_agent_id
                ]
            else:
                metadata_records = []
            self._rewrite_metadata_records(*metadata_records)
            return

        if agent_id:
            self._manifest_path(agent_id).unlink(missing_ok=True)
        else:
            for manifest_path in self._local_cache_dir.glob("*/.remote_manifest.json"):
                manifest_path.unlink(missing_ok=True)

    def _read_manifest_file(self, manifest_path: Path) -> List[str]:
        r"""Read a local manifest file if present."""
        if not manifest_path.exists():
            return []
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def _load_metadata_records(self) -> List[Dict[str, object]]:
        r"""Load namespaced metadata records from KV storage."""
        assert self._metadata_storage is not None
        return [
            record
            for record in self._metadata_storage.load()
            if record.get("kind") == self._METADATA_RECORD_KIND
        ]

    def _rewrite_metadata_records(self, *records: Dict[str, object]) -> None:
        r"""Rewrite this store's metadata records while preserving other data."""
        assert self._metadata_storage is not None
        existing_records = self._metadata_storage.load()
        preserved_records = [
            record
            for record in existing_records
            if record.get("kind") != self._METADATA_RECORD_KIND
        ]
        self._metadata_storage.clear()
        self._metadata_storage.save(preserved_records + list(records))

    def _metadata_record(
        self, agent_id: str, refs: List[str]
    ) -> Dict[str, object]:
        r"""Build a metadata record for one agent's remote refs."""
        return {
            "kind": self._METADATA_RECORD_KIND,
            "agent_id": agent_id,
            "remote_refs": refs,
        }

    def __repr__(self) -> str:
        return (
            f"MediaAssetStore(local_cache_dir={self._local_cache_dir!r}, "
            f"object_storage={self._object_storage!r}, "
            f"remote_prefix={self._remote_prefix!r}, "
            f"io_workers={self._io_workers!r}, "
            f"metadata_storage={self._metadata_storage!r})"
        )
