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

"""Multimodal embedding adapter for unified text+image vector representations."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Union

if TYPE_CHECKING:
    from PIL import Image
    from camel.messages import BaseMessage

from camel.embeddings.base import BaseEmbedding


class MultimodalEmbeddingAdapter:
    r"""Adapts multimodal messages into unified vector representations.

    Strategy:
    - Pure text message: use text_embedding if provided,
      else multimodal_embedding
    - Pure image message: use multimodal_embedding
    - Mixed text+image message: embed text and first image with
      multimodal_embedding, return weighted average
    - Audio bytes: use audio_embedding when provided

    Note:
        This class is NOT a subclass of :obj:`BaseEmbedding`. It wraps
        :obj:`BaseEmbedding` instances internally. This design avoids generic
        type conflicts (input is :obj:`BaseMessage`, output is ``list[float]``).

    Args:
        multimodal_embedding: A unified text+image embedding model (e.g.,
            :obj:`VisionLanguageEmbedding` or :obj:`JinaEmbedding` with
            ``JINA_CLIP_V2``). This MUST produce same-dimension vectors
            for both text and images. Defaults to :obj:`VisionLanguageEmbedding`.
        text_embedding: Optional text-only embedding used as a fast path for
            pure-text messages. If provided, output dimension MUST match
            multimodal_embedding.get_output_dim(). If None,
            multimodal_embedding is used for text as well.
        audio_embedding: Optional audio embedding used for raw audio bytes.
            If provided, output dimension MUST match
            multimodal_embedding.get_output_dim().
        text_weight: Weight for text vector in mixed-modal averaging.
        image_weight: Weight for image vector in mixed-modal averaging.
        max_images_to_embed: Maximum number of images to embed per message
            (only the first N are used). (default: 1)

    Raises:
        ValueError: If modality-specific embeddings and multimodal_embedding
            have mismatched
            dimensions.
    """

    def __init__(
        self,
        multimodal_embedding: Optional[BaseEmbedding] = None,
        text_embedding: Optional[BaseEmbedding[str]] = None,
        audio_embedding: Optional[BaseEmbedding[bytes]] = None,
        text_weight: float = 0.6,
        image_weight: float = 0.4,
        max_images_to_embed: int = 1,
    ) -> None:
        # Import default here to defer heavy dependency (transformers + torch)
        from camel.embeddings.vlm_embedding import VisionLanguageEmbedding

        self._multimodal: BaseEmbedding = (
            multimodal_embedding or VisionLanguageEmbedding()
        )
        self._text: Optional[BaseEmbedding[str]] = text_embedding
        self._audio: Optional[BaseEmbedding[bytes]] = audio_embedding

        # Dimension compatibility check
        for embedding_name, embedding in (
            ("text_embedding", self._text),
            ("audio_embedding", self._audio),
        ):
            if (
                embedding is not None
                and embedding.get_output_dim()
                != self._multimodal.get_output_dim()
            ):
                raise ValueError(
                    f"Dimension mismatch: {embedding_name} output "
                    f"({embedding.get_output_dim()}) != "
                    f"multimodal_embedding output "
                    f"({self._multimodal.get_output_dim()}). "
                    f"Use a unified model for all modalities, or omit "
                    f"{embedding_name}."
                )

        if text_weight < 0 or image_weight < 0:
            raise ValueError(
                f"text_weight and image_weight must be non-negative, "
                f"got text_weight={text_weight}, image_weight={image_weight}."
            )

        self._text_weight: float = text_weight
        self._image_weight: float = image_weight
        self._max_images: int = max_images_to_embed

    @property
    def _effective_text_embedding(self) -> BaseEmbedding:
        r"""Use text_embedding if provided, otherwise multimodal_embedding."""
        return self._text or self._multimodal

    def embed_message(
        self, message: Union["BaseMessage", bytes]
    ) -> List[float]:
        r"""Embed a BaseMessage containing text/images or raw audio bytes.

        Args:
            message: The message or audio bytes to embed.

        Returns:
            A single embedding vector (list of floats).
        """
        if isinstance(message, bytes):
            if self._audio is None:
                raise ValueError(
                    "audio_embedding is required to embed raw audio bytes."
                )
            return self._audio.embed(message)

        has_text = bool(message.content and message.content.strip())
        has_image = bool(message.image_list)
        audio_bytes = getattr(message, "audio_bytes", None)
        has_audio = isinstance(audio_bytes, bytes) and bool(audio_bytes)

        if has_text and has_image:
            # Mixed: embed both, weighted average
            v_text = self._multimodal.embed(message.content)
            first_image = message.image_list[0]
            v_image = self._multimodal.embed(first_image)
            return self._weighted_average(v_text, v_image)

        elif has_image:
            # Image only
            return self._multimodal.embed(message.image_list[0])

        elif has_audio:
            if self._audio is None:
                raise ValueError(
                    "audio_embedding is required to embed message audio_bytes."
                )
            return self._audio.embed(audio_bytes)

        else:
            # Text only (or empty)
            return self._effective_text_embedding.embed(
                message.content or ""
            )

    def embed_query(
        self, query: Union[str, "Image.Image", bytes]
    ) -> List[float]:
        r"""Embed a retrieval query (text string, PIL Image, or audio bytes).

        Args:
            query: Text string, PIL Image, or audio bytes.

        Returns:
            A single embedding vector (list of floats).
        """
        if isinstance(query, str):
            return self._effective_text_embedding.embed(query)
        elif isinstance(query, bytes):
            if self._audio is None:
                raise ValueError(
                    "audio_embedding is required to embed raw audio bytes."
                )
            return self._audio.embed(query)
        else:
            return self._multimodal.embed(query)

    def get_output_dim(self) -> int:
        r"""Return the embedding output dimension.

        Returns:
            The dimensionality of the output embedding vectors.
        """
        return self._multimodal.get_output_dim()

    def _weighted_average(
        self, v_text: List[float], v_image: List[float]
    ) -> List[float]:
        r"""Compute weighted average of text and image vectors.

        Args:
            v_text: Text embedding vector.
            v_image: Image embedding vector.

        Returns:
            Weighted average vector.
        """
        w_total = self._text_weight + self._image_weight
        if w_total == 0:
            return v_text  # Fallback to text if both weights are 0
        return [
            (self._text_weight * t + self._image_weight * i) / w_total
            for t, i in zip(v_text, v_image)
        ]
