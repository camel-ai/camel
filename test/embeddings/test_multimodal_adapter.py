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

"""Tests for MultimodalEmbeddingAdapter."""

from unittest.mock import MagicMock, patch

import pytest

from camel.embeddings.multimodal_adapter import MultimodalEmbeddingAdapter
from camel.messages import BaseMessage
from camel.types import RoleType


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def make_mock_embedding(dim: int = 512) -> MagicMock:
    """Create a mock BaseEmbedding that returns a fixed-dim vector."""
    mock = MagicMock()
    mock.get_output_dim.return_value = dim
    mock.embed.return_value = [0.1] * dim
    return mock


def make_mock_message(
    content: str = "", image_list=None, video_bytes=None
) -> MagicMock:
    msg = MagicMock(spec=BaseMessage)
    msg.content = content
    msg.image_list = image_list
    msg.video_bytes = video_bytes
    return msg


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

class TestMultimodalEmbeddingAdapterInit:
    """Tests for __init__ dimension validation and parameter handling."""

    def test_init_with_matching_dimensions(self):
        """No error when text_embedding and multimodal_embedding have same dim."""
        mock_mm = make_mock_embedding(dim=512)
        mock_text = make_mock_embedding(dim=512)
        mock_audio = make_mock_embedding(dim=512)

        adapter = MultimodalEmbeddingAdapter(
            multimodal_embedding=mock_mm,
            text_embedding=mock_text,
            audio_embedding=mock_audio,
        )
        assert adapter.get_output_dim() == 512

    def test_init_with_mismatched_dimensions_raises(self):
        """ValueError when text_embedding and multimodal_embedding differ."""
        mock_mm = make_mock_embedding(dim=512)
        mock_text = make_mock_embedding(dim=1536)

        with pytest.raises(ValueError, match="Dimension mismatch"):
            MultimodalEmbeddingAdapter(
                multimodal_embedding=mock_mm,
                text_embedding=mock_text,
            )

    def test_init_with_mismatched_audio_dimensions_raises(self):
        """ValueError when audio_embedding and multimodal_embedding differ."""
        mock_mm = make_mock_embedding(dim=512)
        mock_audio = make_mock_embedding(dim=256)

        with pytest.raises(ValueError, match="audio_embedding"):
            MultimodalEmbeddingAdapter(
                multimodal_embedding=mock_mm,
                audio_embedding=mock_audio,
            )

    def test_init_with_no_text_embedding(self):
        """No error when text_embedding is None (uses multimodal for text)."""
        mock_mm = make_mock_embedding(dim=512)

        adapter = MultimodalEmbeddingAdapter(multimodal_embedding=mock_mm)
        assert adapter.get_output_dim() == 512

    def test_init_default_uses_clip(self):
        """Default multimodal_embedding is VisionLanguageEmbedding (CLIP, dim=512)."""
        mock_clip = make_mock_embedding(dim=512)
        # Patch where VisionLanguageEmbedding is imported (inside __init__)
        with patch(
            "camel.embeddings.vlm_embedding.VisionLanguageEmbedding",
            return_value=mock_clip,
        ):
            adapter = MultimodalEmbeddingAdapter()
            assert isinstance(adapter._multimodal, MagicMock)

    def test_init_negative_weights_raises(self):
        """ValueError when text_weight or image_weight is negative."""
        mock_mm = make_mock_embedding()
        with pytest.raises(ValueError, match="non-negative"):
            MultimodalEmbeddingAdapter(
                multimodal_embedding=mock_mm,
                text_weight=-0.5,
            )
        with pytest.raises(ValueError, match="non-negative"):
            MultimodalEmbeddingAdapter(
                multimodal_embedding=mock_mm,
                image_weight=-0.1,
            )

    def test_get_output_dim_delegates(self):
        """get_output_dim returns the multimodal embedding's dimension."""
        mock_mm = make_mock_embedding(dim=768)
        adapter = MultimodalEmbeddingAdapter(multimodal_embedding=mock_mm)
        assert adapter.get_output_dim() == 768


class TestMultimodalEmbeddingAdapterEmbedMessage:
    """Tests for embed_message method."""

    def test_pure_text_message_uses_text_embedding(self):
        """Text-only message: delegates to text_embedding."""
        mock_mm = make_mock_embedding(dim=512)
        mock_text = make_mock_embedding(dim=512)
        adapter = MultimodalEmbeddingAdapter(
            multimodal_embedding=mock_mm,
            text_embedding=mock_text,
        )

        msg = make_mock_message(content="hello world")
        result = adapter.embed_message(msg)

        mock_text.embed.assert_called_once_with("hello world")
        mock_mm.embed.assert_not_called()
        assert result == [0.1] * 512

    def test_pure_text_without_text_embedding_uses_multimodal(self):
        """Text-only message with no text_embedding: delegates to multimodal."""
        mock_mm = make_mock_embedding(dim=512)
        adapter = MultimodalEmbeddingAdapter(multimodal_embedding=mock_mm)

        msg = make_mock_message(content="hello world")
        adapter.embed_message(msg)

        mock_mm.embed.assert_called_once_with("hello world")

    def test_pure_image_message_uses_multimodal_embedding(self):
        """Image-only message: delegates to multimodal on the image."""
        mock_mm = make_mock_embedding(dim=512)
        mock_text = make_mock_embedding(dim=512)
        fake_image = MagicMock()

        adapter = MultimodalEmbeddingAdapter(
            multimodal_embedding=mock_mm,
            text_embedding=mock_text,
        )

        msg = make_mock_message(content="", image_list=[fake_image])
        result = adapter.embed_message(msg)

        mock_mm.embed.assert_called_once_with(fake_image)
        assert result == [0.1] * 512

    def test_mixed_message_returns_weighted_average(self):
        """Text+image message: returns weighted average of both vectors."""
        mock_mm = make_mock_embedding(dim=512)
        mock_mm.embed.side_effect = [
            [1.0] * 512,  # text vector
            [0.5] * 512,  # image vector
        ]

        adapter = MultimodalEmbeddingAdapter(
            multimodal_embedding=mock_mm,
            text_weight=0.6,
            image_weight=0.4,
        )

        fake_image = MagicMock()
        msg = make_mock_message(content="hello", image_list=[fake_image])
        result = adapter.embed_message(msg)

        assert mock_mm.embed.call_count == 2
        # Weighted average: (0.6*1.0 + 0.4*0.5) / 1.0 = 0.8
        assert result[0] == pytest.approx(0.8)
        assert len(result) == 512

    def test_empty_message_uses_text_embedding(self):
        """Empty message (no text, no image): uses text_embedding with empty string."""
        mock_mm = make_mock_embedding(dim=512)
        mock_text = make_mock_embedding(dim=512)
        adapter = MultimodalEmbeddingAdapter(
            multimodal_embedding=mock_mm,
            text_embedding=mock_text,
        )

        msg = make_mock_message(content="", image_list=None)
        result = adapter.embed_message(msg)

        mock_text.embed.assert_called_once_with("")
        assert result == [0.1] * 512

    def test_empty_message_no_text_embedding_uses_multimodal(self):
        """Empty message with no text_embedding: calls multimodal with empty string."""
        mock_mm = make_mock_embedding(dim=512)
        adapter = MultimodalEmbeddingAdapter(multimodal_embedding=mock_mm)

        msg = make_mock_message(content="", image_list=None)
        adapter.embed_message(msg)

        mock_mm.embed.assert_called_once_with("")

    def test_whitespace_only_content_uses_text_embedding(self):
        """Content with only whitespace: treated as text (non-empty)."""
        mock_mm = make_mock_embedding(dim=512)
        mock_text = make_mock_embedding(dim=512)
        adapter = MultimodalEmbeddingAdapter(
            multimodal_embedding=mock_mm,
            text_embedding=mock_text,
        )

        msg = make_mock_message(content="   ", image_list=None)
        result = adapter.embed_message(msg)

        # Whitespace is truthy in the bool() check inside embed_message
        mock_text.embed.assert_called_once_with("   ")

    def test_audio_bytes_use_audio_embedding(self):
        """Raw audio bytes are embedded with the configured audio embedding."""
        mock_mm = make_mock_embedding(dim=512)
        mock_audio = make_mock_embedding(dim=512)
        adapter = MultimodalEmbeddingAdapter(
            multimodal_embedding=mock_mm,
            audio_embedding=mock_audio,
        )

        audio_bytes = b"fake audio bytes"
        result = adapter.embed_message(audio_bytes)

        mock_audio.embed.assert_called_once_with(audio_bytes)
        assert result == [0.1] * 512

    def test_audio_only_message_uses_audio_embedding(self):
        """Audio-only BaseMessage delegates to audio_embedding."""
        mock_mm = make_mock_embedding(dim=512)
        mock_audio = make_mock_embedding(dim=512)
        adapter = MultimodalEmbeddingAdapter(
            multimodal_embedding=mock_mm,
            audio_embedding=mock_audio,
        )

        msg = make_mock_message(content="", image_list=None)
        msg.audio_bytes = b"audio message"
        result = adapter.embed_message(msg)

        mock_audio.embed.assert_called_once_with(b"audio message")
        assert result == [0.1] * 512

    def test_audio_bytes_without_audio_embedding_raise(self):
        """Raw audio bytes require an audio embedding backend."""
        mock_mm = make_mock_embedding(dim=512)
        adapter = MultimodalEmbeddingAdapter(multimodal_embedding=mock_mm)

        with pytest.raises(ValueError, match="audio_embedding"):
            adapter.embed_message(b"audio")


class TestMultimodalEmbeddingAdapterEmbedQuery:
    """Tests for embed_query method."""

    def test_text_query_uses_text_embedding(self):
        """Text query string: delegates to text_embedding."""
        mock_mm = make_mock_embedding(dim=512)
        mock_text = make_mock_embedding(dim=512)
        adapter = MultimodalEmbeddingAdapter(
            multimodal_embedding=mock_mm,
            text_embedding=mock_text,
        )

        result = adapter.embed_query("search term")

        mock_text.embed.assert_called_once_with("search term")
        assert result == [0.1] * 512

    def test_image_query_uses_multimodal_embedding(self):
        """PIL Image query: delegates to multimodal_embedding."""
        mock_mm = make_mock_embedding(dim=512)
        mock_text = make_mock_embedding(dim=512)
        fake_image = MagicMock()

        adapter = MultimodalEmbeddingAdapter(
            multimodal_embedding=mock_mm,
            text_embedding=mock_text,
        )

        result = adapter.embed_query(fake_image)

        mock_mm.embed.assert_called_once_with(fake_image)
        assert result == [0.1] * 512

    def test_query_no_text_embedding_uses_multimodal(self):
        """Text query with no text_embedding: uses multimodal_embedding."""
        mock_mm = make_mock_embedding(dim=512)
        adapter = MultimodalEmbeddingAdapter(multimodal_embedding=mock_mm)

        adapter.embed_query("search term")
        mock_mm.embed.assert_called_once_with("search term")

    def test_audio_query_uses_audio_embedding(self):
        """Audio query bytes delegate to audio_embedding."""
        mock_mm = make_mock_embedding(dim=512)
        mock_audio = make_mock_embedding(dim=512)
        adapter = MultimodalEmbeddingAdapter(
            multimodal_embedding=mock_mm,
            audio_embedding=mock_audio,
        )

        audio_bytes = b"query audio"
        result = adapter.embed_query(audio_bytes)

        mock_audio.embed.assert_called_once_with(audio_bytes)
        assert result == [0.1] * 512

    def test_audio_query_without_audio_embedding_raises(self):
        """Audio query bytes require audio_embedding."""
        mock_mm = make_mock_embedding(dim=512)
        adapter = MultimodalEmbeddingAdapter(multimodal_embedding=mock_mm)

        with pytest.raises(ValueError, match="audio_embedding"):
            adapter.embed_query(b"query audio")


class TestWeightedAverage:
    """Tests for the internal weighted average computation."""

    def test_weighted_average_combines_vectors(self):
        """Weighted average correctly combines text and image vectors."""
        mock_mm = make_mock_embedding(dim=3)
        mock_mm.embed.side_effect = [
            [1.0, 2.0, 3.0],  # text
            [3.0, 2.0, 1.0],  # image
        ]

        adapter = MultimodalEmbeddingAdapter(
            multimodal_embedding=mock_mm,
            text_weight=0.5,
            image_weight=0.5,
        )

        fake_image = MagicMock()
        msg = make_mock_message(content="test", image_list=[fake_image])
        result = adapter.embed_message(msg)

        # (0.5*1.0 + 0.5*3.0) / 1.0 = 2.0
        assert result[0] == pytest.approx(2.0)
        assert result[1] == pytest.approx(2.0)
        assert result[2] == pytest.approx(2.0)

    def test_weighted_average_respects_weights(self):
        """Higher text_weight biases toward text vector."""
        mock_mm = make_mock_embedding(dim=2)
        mock_mm.embed.side_effect = [
            [10.0, 10.0],  # text
            [0.0, 0.0],    # image
        ]

        adapter = MultimodalEmbeddingAdapter(
            multimodal_embedding=mock_mm,
            text_weight=0.9,
            image_weight=0.1,
        )

        fake_image = MagicMock()
        msg = make_mock_message(content="test", image_list=[fake_image])
        result = adapter.embed_message(msg)

        # 0.9*10 + 0.1*0 = 9.0
        assert result[0] == pytest.approx(9.0)
        assert result[1] == pytest.approx(9.0)

    def test_zero_total_weight_falls_back_to_text(self):
        """When both weights are 0, returns text vector unchanged."""
        mock_mm = make_mock_embedding(dim=2)
        mock_mm.embed.side_effect = [
            [5.0, 5.0],
            [1.0, 1.0],
        ]

        adapter = MultimodalEmbeddingAdapter(
            multimodal_embedding=mock_mm,
            text_weight=0.0,
            image_weight=0.0,
        )

        fake_image = MagicMock()
        msg = make_mock_message(content="test", image_list=[fake_image])
        result = adapter.embed_message(msg)

        assert result == [5.0, 5.0]
