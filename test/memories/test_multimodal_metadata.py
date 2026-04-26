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

"""Tests for MultimodalMetadata helper."""

import pytest
from unittest.mock import MagicMock

from camel.memories.multimodal_metadata import MultimodalMetadata


class TestMultimodalMetadata:
    """Tests for MultimodalMetadata serialization and deserialization."""

    def test_from_message_text_only(self):
        """Text-only message has image/video/audio counters cleared."""
        mock_message = MagicMock()
        mock_message.content = "Hello world"
        mock_message.image_list = None
        mock_message.video_bytes = None
        mock_message.audio_bytes = None

        meta = MultimodalMetadata.from_message(mock_message)

        assert meta.modalities == ["text"]
        assert meta.image_count == 0
        assert meta.has_video is False
        assert meta.has_audio is False
        assert meta.media_refs == []
        assert meta.text_summary is None

    def test_from_message_with_image(self):
        """Message with image has modalities=['text', 'image'] and correct count."""
        mock_message = MagicMock()
        mock_message.content = "Look at this"
        mock_message.image_list = [MagicMock(), MagicMock()]
        mock_message.video_bytes = None
        mock_message.audio_bytes = None

        meta = MultimodalMetadata.from_message(mock_message)

        assert "text" in meta.modalities
        assert "image" in meta.modalities
        assert meta.image_count == 2
        assert meta.has_video is False

    def test_from_message_with_video(self):
        """Message with video has has_video=True."""
        mock_message = MagicMock()
        mock_message.content = "Check out this video"
        mock_message.image_list = None
        mock_message.video_bytes = b"video data"
        mock_message.audio_bytes = None

        meta = MultimodalMetadata.from_message(mock_message)

        assert meta.has_video is True
        assert meta.image_count == 0

    def test_from_message_with_audio(self):
        """Message with audio has has_audio=True and audio modality."""
        mock_message = MagicMock()
        mock_message.content = ""
        mock_message.image_list = None
        mock_message.video_bytes = None
        mock_message.audio_bytes = b"audio data"

        meta = MultimodalMetadata.from_message(mock_message)

        assert meta.has_audio is True
        assert "audio" in meta.modalities

    def test_from_message_image_only(self):
        """Image-only message has modalities=['text', 'image'] even with no text."""
        mock_message = MagicMock()
        mock_message.content = ""
        mock_message.image_list = [MagicMock()]
        mock_message.video_bytes = None
        mock_message.audio_bytes = None

        meta = MultimodalMetadata.from_message(mock_message)

        assert "image" in meta.modalities
        assert meta.image_count == 1

    def test_to_extra_info_full(self):
        """to_extra_info produces Dict[str, str] compatible with MemoryRecord."""
        meta = MultimodalMetadata(
            modalities=["text", "image"],
            image_count=2,
            has_video=True,
            has_audio=True,
            media_refs=["file:///path/uuid.png"],
            text_summary="A cat sitting on a mat",
        )

        extra = meta.to_extra_info()

        assert isinstance(extra, dict)
        assert all(isinstance(v, str) for v in extra.values())
        assert '"text"' in extra["modalities"]
        assert extra["image_count"] == "2"
        assert extra["has_video"] == "true"
        assert extra["has_audio"] == "true"
        assert "uuid.png" in extra["media_refs"]
        assert extra["text_summary"] == "A cat sitting on a mat"

    def test_to_extra_info_defaults(self):
        """Default MultimodalMetadata serializes correctly."""
        meta = MultimodalMetadata()
        extra = meta.to_extra_info()

        assert extra["modalities"] == '["text"]'
        assert extra["image_count"] == "0"
        assert extra["has_video"] == "false"
        assert extra["has_audio"] == "false"
        assert extra["media_refs"] == "[]"
        assert extra["text_summary"] == ""

    def test_from_extra_info_full(self):
        """from_extra_info reconstructs MultimodalMetadata from serialized dict."""
        extra = {
            "modalities": '["text", "image"]',
            "image_count": "3",
            "has_video": "true",
            "has_audio": "true",
            "media_refs": '["s3://bucket/1.png", "s3://bucket/2.png"]',
            "text_summary": "A sunset over the ocean",
        }

        meta = MultimodalMetadata.from_extra_info(extra)

        assert meta.modalities == ["text", "image"]
        assert meta.image_count == 3
        assert meta.has_video is True
        assert meta.has_audio is True
        assert len(meta.media_refs) == 2
        assert meta.text_summary == "A sunset over the ocean"

    def test_from_extra_info_empty(self):
        """from_extra_info handles missing keys gracefully."""
        meta = MultimodalMetadata.from_extra_info({})

        assert meta.modalities == ["text"]
        assert meta.image_count == 0
        assert meta.has_video is False
        assert meta.has_audio is False
        assert meta.media_refs == []
        assert meta.text_summary is None

    def test_roundtrip(self):
        """Serialization + deserialization is lossless for full metadata."""
        original = MultimodalMetadata(
            modalities=["text", "image"],
            image_count=5,
            has_video=True,
            has_audio=True,
            media_refs=["file:///cache/abc.png", "file:///cache/def.jpg"],
            text_summary="A busy city street",
        )

        restored = MultimodalMetadata.from_extra_info(original.to_extra_info())

        assert restored.modalities == original.modalities
        assert restored.image_count == original.image_count
        assert restored.has_video == original.has_video
        assert restored.has_audio == original.has_audio
        assert restored.media_refs == original.media_refs
        assert restored.text_summary == original.text_summary

    def test_extra_info_type_compatible_with_memory_record(self):
        """All values in extra_info are strings (compatible with MemoryRecord)."""
        meta = MultimodalMetadata(
            modalities=["text", "image"],
            image_count=10,
            has_video=False,
            has_audio=True,
            media_refs=["uri1", "uri2"],
            text_summary=None,
        )

        extra = meta.to_extra_info()

        # MemoryRecord.extra_info is Dict[str, str]
        assert extra["modalities"] == '["text", "image"]'  # str, not list
        assert extra["image_count"] == "10"  # str, not int
        assert extra["has_video"] == "false"  # str, not bool
        assert extra["has_audio"] == "true"  # str, not bool
