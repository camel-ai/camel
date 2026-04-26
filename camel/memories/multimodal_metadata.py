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

"""Type-safe wrapper for multimodal metadata stored in MemoryRecord.extra_info.

All values are serialized as JSON strings to respect the MemoryRecord.extra_info:
    Dict[str, str] type constraint.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from camel.messages import BaseMessage


@dataclass
class MultimodalMetadata:
    r"""Type-safe wrapper for modality metadata stored in MemoryRecord.extra_info.

    All values are serialized to JSON strings to respect the
    MemoryRecord.extra_info: Dict[str, str] type constraint.

    Attributes:
        modalities: List of present modalities (e.g., ["text"], ["text", "image"]).
        image_count: Number of images in the message.
        has_video: Whether the message contains video.
        has_audio: Whether the message contains audio.
        media_refs: External URI references to stored media assets.
        text_summary: Optional LLM-generated description of images (for
            text-query recall of image-only memories).
    """

    modalities: List[str] = field(default_factory=lambda: ["text"])
    image_count: int = 0
    has_video: bool = False
    has_audio: bool = False
    media_refs: List[str] = field(default_factory=list)
    text_summary: Optional[str] = None

    def to_extra_info(self) -> Dict[str, str]:
        r"""Serialize to Dict[str, str] for MemoryRecord.extra_info.

        Returns:
            A dictionary with string keys and string values suitable for
            merging into MemoryRecord.extra_info.
        """
        return {
            "modalities": json.dumps(self.modalities),
            "image_count": str(self.image_count),
            "has_video": str(self.has_video).lower(),
            "has_audio": str(self.has_audio).lower(),
            "media_refs": json.dumps(self.media_refs),
            "text_summary": self.text_summary or "",
        }

    @classmethod
    def from_extra_info(
        cls, extra_info: Dict[str, str]
    ) -> "MultimodalMetadata":
        r"""Deserialize from MemoryRecord.extra_info.

        Args:
            extra_info: A dictionary from MemoryRecord.extra_info.

        Returns:
            A MultimodalMetadata instance.
        """
        return cls(
            modalities=json.loads(extra_info.get("modalities", '["text"]')),
            image_count=int(extra_info.get("image_count", "0")),
            has_video=extra_info.get("has_video", "false") == "true",
            has_audio=extra_info.get("has_audio", "false") == "true",
            media_refs=json.loads(extra_info.get("media_refs", "[]")),
            text_summary=extra_info.get("text_summary") or None,
        )

    @classmethod
    def from_message(cls, message: "BaseMessage") -> "MultimodalMetadata":
        r"""Extract modality information from a BaseMessage.

        Args:
            message: The BaseMessage to analyze.

        Returns:
            A MultimodalMetadata instance describing the message's modalities.
        """
        modalities = ["text"]
        if message.image_list:
            modalities.append("image")
        if getattr(message, "audio_bytes", None):
            modalities.append("audio")
        return cls(
            modalities=modalities,
            image_count=len(message.image_list) if message.image_list else 0,
            has_video=message.video_bytes is not None,
            has_audio=getattr(message, "audio_bytes", None) is not None,
        )
