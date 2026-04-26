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

"""Vector DB block with multimodal embedding support."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Callable, List, Optional, Union

if TYPE_CHECKING:
    from PIL import Image

from camel.embeddings.multimodal_adapter import MultimodalEmbeddingAdapter
from camel.memories.base import MemoryBlock
from camel.memories.media_asset_store import MediaAssetStore
from camel.memories.multimodal_metadata import MultimodalMetadata
from camel.memories.records import ContextRecord, MemoryRecord
from camel.storages.vectordb_storages.base import (
    BaseVectorStorage,
    VectorDBQuery,
    VectorRecord,
)


class MultimodalVectorDBBlock(MemoryBlock):
    r"""Vector DB block with multimodal embedding and optional media externalization.

    Unlike :obj:`VectorDBBlock` which only embeds text content, this block:
    - Embeds text + image content using :obj:`MultimodalEmbeddingAdapter`
    - Optionally externalizes media to :obj:`MediaAssetStore`
    - Supports cross-modal retrieval (text query → image results, etc.)
    - Stores modality metadata in extra_info for filtering

    This class reimplements the :obj:`MemoryBlock` contract
    (:meth:`write_records`, :meth:`clear`) but with a different
    :meth:`retrieve` signature. It does NOT inherit from :obj:`VectorDBBlock`
    to avoid breaking the existing interface.

    Note:
        Media externalization (:obj:`MediaAssetStore`) is optional.
        When ``media_store=None`` (default), media stays inline in payloads,
        same as :obj:`VectorDBBlock`.

    Args:
        storage: Vector storage backend. Defaults to in-memory Qdrant.
            (default: None)
        embedding: Multimodal embedding adapter. Defaults to CLIP-based
            :obj:`MultimodalEmbeddingAdapter`. (default: None)
        media_store: Media asset store for externalizing binary content.
            When None, media stays inline in payloads (same behavior as
            :obj:`VectorDBBlock`). (default: None)
    """

    def __init__(
        self,
        storage: Optional[BaseVectorStorage] = None,
        embedding: Optional[MultimodalEmbeddingAdapter] = None,
        media_store: Optional[MediaAssetStore] = None,
        auto_caption: bool = False,
        caption_generator: Optional[Callable[[MemoryRecord], Optional[str]]] = None,
    ) -> None:
        self._embedding = embedding or MultimodalEmbeddingAdapter()
        self._media_store = media_store
        self._media_agent_ids: set[str] = set()
        self._auto_caption = auto_caption
        self._caption_generator = caption_generator

        if self._auto_caption and self._caption_generator is None:
            raise ValueError(
                "caption_generator is required when auto_caption=True."
            )

        # Import Qdrant lazily to avoid heavy dependency on default path
        if storage is None:
            from camel.storages.vectordb_storages.qdrant import QdrantStorage

            storage = QdrantStorage(
                vector_dim=self._embedding.get_output_dim()
            )
        self._storage = storage

    def retrieve(
        self,
        query: Union[str, "Image.Image", bytes],
        limit: int = 3,
    ) -> List[ContextRecord]:
        r"""Retrieve similar records using text or image query.

        Args:
            query: A text string or PIL Image to search for.
            limit: Maximum number of results to return. (default: 3)

        Returns:
            List of ContextRecords ranked by similarity.
        """
        query_vector = self._embedding.embed_query(query)
        results = self._storage.query(
            VectorDBQuery(query_vector=query_vector, top_k=limit)
        )

        records = []
        for result in results:
            if result.record.payload is None:
                continue
            memory_record = MemoryRecord.from_dict(result.record.payload)

            # Restore media if media_store is configured
            if self._media_store is not None:
                memory_record = self._media_store.restore_media(memory_record)

            records.append(
                ContextRecord(
                    memory_record=memory_record,
                    score=result.similarity,
                    timestamp=result.record.payload.get("timestamp", 0.0),
                )
            )
        return records

    def write_records(
        self,
        records: List[MemoryRecord],
        agent_id: str = "",
    ) -> None:
        r"""Embed multimodal content, optionally externalize media, store vectors.

        Args:
            records: Memory records to write.
            agent_id: Agent identifier for media storage namespacing.
        """
        valid_records = []
        for record in records:
            # Skip completely empty records (no text AND no media)
            is_empty_text = not (
                record.message.content and record.message.content.strip()
            )
            is_empty_media = (
                not record.message.image_list
                and not record.message.video_bytes
                and not getattr(record.message, "audio_bytes", None)
            )
            if is_empty_text and is_empty_media:
                continue

            # Extract modality metadata
            mmeta = MultimodalMetadata.from_message(record.message)
            record_for_embedding = record.model_copy(deep=True)

            if self._auto_caption:
                text_summary = self._generate_text_summary(record)
                if text_summary:
                    mmeta.text_summary = text_summary
                    record_for_embedding = self._append_text_summary(
                        record_for_embedding, text_summary
                    )

            # Externalize media if media_store is configured
            if self._media_store is not None:
                refs = self._media_store.store_media(record, agent_id)
                for uri in refs.values():
                    mmeta.media_refs.append(uri)
                self._media_agent_ids.add(agent_id or "default")

            # Serialize metadata to extra_info
            extra_info = {**record.extra_info, **mmeta.to_extra_info()}

            # Embed the message
            vector = self._embed_record(record_for_embedding)
            payload = self._build_payload(
                record=record,
                extra_info=extra_info,
                media_refs=mmeta.media_refs,
            )

            valid_records.append(
                VectorRecord(
                    vector=vector,
                    payload=payload,
                    id=str(record.uuid),
                )
            )

        if valid_records:
            self._storage.add(valid_records)

    def clear(self) -> None:
        r"""Remove all records from vector storage."""
        self._storage.clear()
        if self._media_store is not None:
            for agent_id in self._media_agent_ids:
                self._media_store.clear(agent_id=agent_id)
            self._media_agent_ids.clear()

    def close(self) -> None:
        r"""Release resources owned by the multimodal vector block."""
        if self._media_store is not None:
            self._media_store.close()

    @property
    def storage(self) -> BaseVectorStorage:
        r"""The underlying vector storage instance."""
        return self._storage

    @property
    def embedding(self) -> MultimodalEmbeddingAdapter:
        r"""The multimodal embedding adapter instance."""
        return self._embedding

    @property
    def media_store(self) -> Optional[MediaAssetStore]:
        r"""The media store used for externalized payloads."""
        return self._media_store

    @property
    def auto_caption(self) -> bool:
        r"""Whether image auto-captioning is enabled."""
        return self._auto_caption

    def _build_payload(
        self,
        record: MemoryRecord,
        extra_info: dict[str, str],
        media_refs: List[str],
    ) -> dict:
        r"""Build a vector payload without mutating the caller's record."""
        payload_record = record.model_copy(deep=True)
        payload_record.extra_info = extra_info

        if self._media_store is None or not media_refs:
            return payload_record.to_dict()

        image_refs = [ref for ref in media_refs if "_video." not in ref]
        audio_refs = [ref for ref in media_refs if "_audio." in ref]
        image_refs = [ref for ref in image_refs if "_audio." not in ref]
        payload_record.message.image_list = (
            copy.deepcopy(image_refs) if image_refs else None
        )
        payload_record.message.video_bytes = None
        payload_record.message.audio_bytes = None
        if audio_refs:
            payload_record.message.audio_format = self._infer_audio_format(
                audio_refs[0]
            )
        return payload_record.to_dict()

    def _generate_text_summary(self, record: MemoryRecord) -> Optional[str]:
        r"""Generate a text summary for image-containing records."""
        if not record.message.image_list or self._caption_generator is None:
            return None
        summary = self._caption_generator(record)
        if summary is None:
            return None
        summary = summary.strip()
        return summary or None

    def _append_text_summary(
        self, record: MemoryRecord, text_summary: str
    ) -> MemoryRecord:
        r"""Append caption text so it contributes to the embedding."""
        content = (record.message.content or "").strip()
        if content:
            record.message.content = f"{content}\n\n{text_summary}"
        else:
            record.message.content = text_summary
        return record

    def _embed_record(self, record: MemoryRecord) -> List[float]:
        r"""Embed a memory record, including audio-only messages."""
        if (
            getattr(record.message, "audio_bytes", None)
            and not (record.message.content and record.message.content.strip())
            and not record.message.image_list
        ):
            return self._embedding.embed_message(record.message.audio_bytes)
        return self._embedding.embed_message(record.message)

    def _infer_audio_format(self, uri: str) -> str:
        r"""Infer audio format from URI suffix."""
        return uri.rsplit(".", 1)[-1].lower() if "." in uri else "wav"
