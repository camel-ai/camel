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

"""Context creator with multimodal-aware token budgeting."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Literal, Optional, Tuple

from camel.memories.context_creators.score_based import ScoreBasedContextCreator
from camel.memories.records import ContextRecord
from camel.messages import OpenAIMessage

if TYPE_CHECKING:
    from camel.memories.media_asset_store import MediaAssetStore
    from camel.utils import BaseTokenCounter


class MultimodalContextCreator(ScoreBasedContextCreator):
    r"""Context creator with multimodal-aware token budgeting.

    Extends :obj:`ScoreBasedContextCreator` with:

    - Configurable max images per context window
    - Automatic ``image_detail`` downgrade under token pressure
    - Optional media restoration from external storage

    Args:
        token_counter: Token counter instance.
        token_limit: Maximum token budget.
        media_store: For restoring externalized media.
            (default: :obj:`None`)
        max_images_per_context: Maximum images in a single context.
            (default: :obj:`10`)
        image_detail_fallback: Fallback image detail when token budget
            is tight. (default: :obj:`"low"`)
    """

    def __init__(
        self,
        token_counter: "BaseTokenCounter",
        token_limit: int,
        media_store: Optional["MediaAssetStore"] = None,
        max_images_per_context: int = 10,
        image_detail_fallback: Literal["auto", "low", "high"] = "low",
    ) -> None:
        super().__init__(token_counter, token_limit)
        self._media_store = media_store
        self._max_images = max_images_per_context
        self._detail_fallback = image_detail_fallback

    @property
    def media_store(self) -> Optional["MediaAssetStore"]:
        r"""The media store used to restore externalized assets."""
        return self._media_store

    def bind_media_store(self, media_store: "MediaAssetStore") -> None:
        r"""Bind a media store after construction."""
        self._media_store = media_store

    def create_context(
        self,
        records: List[ContextRecord],
    ) -> Tuple[List[OpenAIMessage], int]:
        r"""Create context with multimodal token management.

        Strategy:
        1. Restore externalized media if media_store is configured
        2. Count total images across all records
        3. If exceeding ``max_images_per_context``, drop from lowest
           scores first
        4. If estimated tokens exceed 80% of ``token_limit``, downgrade
           image detail
        5. Delegate to parent for chronological sorting and token counting

        Args:
            records: List of context records to process.

        Returns:
            Tuple of (OpenAI messages, total token count).
        """
        records = [record.model_copy(deep=True) for record in records]

        # Step 1: Restore media from external storage
        if self._media_store is not None:
            records = [
                ContextRecord(
                    memory_record=self._media_store.restore_media(
                        record.memory_record
                    ),
                    score=record.score,
                    timestamp=record.timestamp,
                )
                for record in records
            ]

        # Step 2: Enforce max images per context
        records = self._trim_images(records)

        # Step 3: Downgrade detail under token pressure
        records = self._adjust_image_detail(records)

        # Step 4: Delegate to parent
        return super().create_context(records)

    def _trim_images(
        self, records: List[ContextRecord]
    ) -> List[ContextRecord]:
        r"""Remove images from lowest-scored records until under max_images.

        When the total image count exceeds ``max_images_per_context``, images
        are removed from the lowest-scoring records first. The text content
        of those records is preserved.

        Args:
            records: Context records with scores.

        Returns:
            Records with image count within budget.
        """
        total_images = sum(
            len(r.memory_record.message.image_list or [])
            for r in records
        )
        if total_images <= self._max_images:
            return records

        # Sort records by score descending, keep highest-scored images first
        scored = sorted(
            enumerate(records),
            key=lambda x: x[1].score,
            reverse=True,
        )

        images_to_remove = total_images - self._max_images
        removed = 0
        trimmed_indices: set = set()

        # Walk from lowest score (end of list) to remove images
        for orig_idx, record in reversed(scored):
            if removed >= images_to_remove:
                break
            img_count = len(record.memory_record.message.image_list or [])
            if img_count > 0:
                trimmed_indices.add(orig_idx)
                removed += img_count

        # Build result: remove images from flagged records
        result = []
        for idx, record in enumerate(records):
            if idx in trimmed_indices:
                record.memory_record.message.image_list = []
            result.append(record)

        return result

    def _adjust_image_detail(
        self, records: List[ContextRecord]
    ) -> List[ContextRecord]:
        r"""Downgrade image_detail to reduce token cost under pressure.

        When the estimated total token count exceeds 80% of
        ``token_limit``, all records with images have their
        ``image_detail`` set to ``image_detail_fallback``.

        Args:
            records: Context records to adjust.

        Returns:
            Records with potentially downgraded image detail.
        """
        total_estimate = sum(
            self._estimate_message_tokens(
                r.memory_record.to_openai_message()
            )
            for r in records
        )

        if total_estimate <= int(self.token_limit * 0.8):
            return records  # No pressure, keep original detail

        # Downgrade: set all image_detail to fallback level
        for record in records:
            if record.memory_record.message.image_list:
                record.memory_record.message.image_detail = (
                    self._detail_fallback
                )

        return records

    def __repr__(self) -> str:
        return (
            f"MultimodalContextCreator("
            f"token_limit={self._token_limit}, "
            f"max_images={self._max_images}, "
            f"detail_fallback={self._detail_fallback!r})"
        )
