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

"""Tests for MultimodalVectorDBBlock."""

from datetime import datetime
from unittest.mock import MagicMock, create_autospec, patch
from uuid import uuid4

import pytest

from camel.embeddings.multimodal_adapter import MultimodalEmbeddingAdapter
from camel.memories.blocks.multimodal_vectordb_block import (
    MultimodalVectorDBBlock,
)
from camel.memories.records import ContextRecord, MemoryRecord
from camel.messages import BaseMessage
from camel.storages import BaseVectorStorage, VectorDBQueryResult, VectorRecord
from camel.types import OpenAIBackendRole, RoleType


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def make_mock_records(num: int = 2, content_prefix: str = "test") -> list:
    """Generate mock MemoryRecord dicts matching MemoryRecord.to_dict() format."""
    return [
        {
            "uuid": str(uuid4()),
            "message": {
                "__class__": "BaseMessage",
                "role_name": "user",
                "role_type": RoleType.USER,
                "meta_dict": None,
                "content": f"{content_prefix} message {i}",
                "image_list": None,
                "video_bytes": None,
                "image_detail": "auto",
                "video_detail": "auto",
                "parsed": None,
                "reasoning_content": None,
            },
            "role_at_backend": "user",
            "extra_info": {},
            "timestamp": datetime.now().timestamp(),
            "agent_id": f"test_agent_{i}",
        }
        for i in range(num)
    ]


def make_memory_record(
    content: str = "test",
    image_list=None,
    audio_bytes=None,
    audio_format=None,
) -> MemoryRecord:
    return MemoryRecord(
        message=BaseMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=None,
            content=content,
            image_list=image_list,
            audio_bytes=audio_bytes,
            audio_format=audio_format,
        ),
        role_at_backend=OpenAIBackendRole.USER,
        agent_id="test_agent",
    )


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture
def mock_storage():
    return create_autospec(BaseVectorStorage)


@pytest.fixture
def mock_adapter():
    mock = MagicMock(spec=MultimodalEmbeddingAdapter)
    mock.get_output_dim.return_value = 512
    mock.embed_message.return_value = [0.1] * 512
    mock.embed_query.return_value = [0.1] * 512
    return mock


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

class TestMultimodalVectorDBBlockInit:
    """Tests for __init__."""

    def test_init_with_custom_components(self, mock_storage, mock_adapter):
        """Init with custom storage and embedding."""
        block = MultimodalVectorDBBlock(
            storage=mock_storage,
            embedding=mock_adapter,
        )
        assert block.storage is mock_storage
        assert block.embedding is mock_adapter

    def test_init_with_default_storage_uses_qdrant(self, mock_adapter):
        """Init without storage creates QdrantStorage with correct dimension."""
        mock_qdrant = MagicMock()
        # QdrantStorage is imported inside __init__ as a lazy import,
        # so we patch where it's looked up in the function's local scope
        with patch(
            "camel.storages.vectordb_storages.qdrant.QdrantStorage",
            return_value=mock_qdrant,
        ):
            block = MultimodalVectorDBBlock(embedding=mock_adapter)
            assert block.storage is mock_qdrant

    def test_init_with_default_embedding(self, mock_storage):
        """Init without embedding creates MultimodalEmbeddingAdapter."""
        with patch(
            "camel.memories.blocks.multimodal_vectordb_block."
            "MultimodalEmbeddingAdapter"
        ) as mock_adapter_cls:
            mock_adapter_cls.return_value = MagicMock(
                spec=MultimodalEmbeddingAdapter
            )
            block = MultimodalVectorDBBlock(storage=mock_storage)
            mock_adapter_cls.assert_called_once()

    def test_init_auto_caption_requires_generator(
        self, mock_storage, mock_adapter
    ):
        """auto_caption=True requires an injected caption generator."""
        with pytest.raises(ValueError, match="caption_generator"):
            MultimodalVectorDBBlock(
                storage=mock_storage,
                embedding=mock_adapter,
                auto_caption=True,
            )


class TestMultimodalVectorDBBlockRetrieve:
    """Tests for retrieve method."""

    def test_retrieve_with_text_query(self, mock_storage, mock_adapter):
        """retrieve accepts text string and returns ContextRecords."""
        mock_records = make_mock_records(2)
        mock_adapter.embed_query.return_value = [0.5] * 512

        mock_query_results = [
            VectorDBQueryResult.create(
                similarity=0.9,
                vector=[0.1] * 512,
                id=mock_records[0]["uuid"],
                payload=mock_records[0],
            ),
            VectorDBQueryResult.create(
                similarity=0.7,
                vector=[0.1] * 512,
                id=mock_records[1]["uuid"],
                payload=mock_records[1],
            ),
        ]
        mock_storage.query.return_value = mock_query_results

        block = MultimodalVectorDBBlock(
            storage=mock_storage, embedding=mock_adapter
        )

        results = block.retrieve("search keyword", limit=2)

        assert len(results) == 2
        assert all(isinstance(r, ContextRecord) for r in results)
        assert results[0].score == 0.9
        assert results[1].score == 0.7
        mock_adapter.embed_query.assert_called_with("search keyword")
        mock_storage.query.assert_called_once()

    def test_retrieve_with_image_query(self, mock_storage, mock_adapter):
        """retrieve accepts PIL Image as query for cross-modal retrieval."""
        mock_records = make_mock_records(1)
        fake_image = MagicMock()
        mock_adapter.embed_query.return_value = [0.5] * 512

        mock_query_results = [
            VectorDBQueryResult.create(
                similarity=0.85,
                vector=[0.1] * 512,
                id=mock_records[0]["uuid"],
                payload=mock_records[0],
            ),
        ]
        mock_storage.query.return_value = mock_query_results

        block = MultimodalVectorDBBlock(
            storage=mock_storage, embedding=mock_adapter
        )

        results = block.retrieve(fake_image, limit=1)

        mock_adapter.embed_query.assert_called_with(fake_image)
        assert len(results) == 1
        assert results[0].score == 0.85

    def test_retrieve_with_audio_query(self, mock_storage, mock_adapter):
        """retrieve accepts raw audio bytes for audio-based retrieval."""
        mock_records = make_mock_records(1)
        audio_bytes = b"query audio"
        mock_adapter.embed_query.return_value = [0.5] * 512

        mock_query_results = [
            VectorDBQueryResult.create(
                similarity=0.85,
                vector=[0.1] * 512,
                id=mock_records[0]["uuid"],
                payload=mock_records[0],
            ),
        ]
        mock_storage.query.return_value = mock_query_results

        block = MultimodalVectorDBBlock(
            storage=mock_storage, embedding=mock_adapter
        )

        results = block.retrieve(audio_bytes, limit=1)

        mock_adapter.embed_query.assert_called_with(audio_bytes)
        assert len(results) == 1
        assert results[0].score == 0.85

    def test_retrieve_with_media_store_restores_media(
        self, mock_storage, mock_adapter
    ):
        """When media_store is set, retrieve restores media in records."""
        mock_records = make_mock_records(1)
        mock_adapter.embed_query.return_value = [0.5] * 512
        mock_query_results = [
            VectorDBQueryResult.create(
                similarity=0.9,
                vector=[0.1] * 512,
                id=mock_records[0]["uuid"],
                payload=mock_records[0],
            ),
        ]
        mock_storage.query.return_value = mock_query_results

        mock_media_store = MagicMock()
        mock_media_store.restore_media.side_effect = lambda r: r  # passthrough

        block = MultimodalVectorDBBlock(
            storage=mock_storage,
            embedding=mock_adapter,
            media_store=mock_media_store,
        )

        results = block.retrieve("query", limit=1)

        mock_media_store.restore_media.assert_called_once()
        assert results[0].score == 0.9

    def test_retrieve_skips_null_payload(self, mock_storage, mock_adapter):
        """Records with null payload are skipped."""
        mock_adapter.embed_query.return_value = [0.5] * 512

        mock_query_results = [
            VectorDBQueryResult.create(
                similarity=0.9,
                vector=[0.1] * 512,
                id="id1",
                payload=None,
            ),
            VectorDBQueryResult.create(
                similarity=0.7,
                vector=[0.1] * 512,
                id="id2",
                payload=make_mock_records(1)[0],
            ),
        ]
        mock_storage.query.return_value = mock_query_results

        block = MultimodalVectorDBBlock(
            storage=mock_storage, embedding=mock_adapter
        )

        results = block.retrieve("query", limit=2)
        assert len(results) == 1
        assert results[0].score == 0.7


class TestMultimodalVectorDBBlockWriteRecords:
    """Tests for write_records method."""

    def test_write_records_embeds_multimodal_message(
        self, mock_storage, mock_adapter
    ):
        """write_records calls embed_message with the record's message."""
        fake_image = MagicMock()
        record = make_memory_record(content="analyze this", image_list=[fake_image])

        block = MultimodalVectorDBBlock(
            storage=mock_storage, embedding=mock_adapter
        )
        block.write_records([record])

        mock_adapter.embed_message.assert_called_once()
        call_args = mock_adapter.embed_message.call_args[0][0]
        assert call_args.content == "analyze this"
        assert call_args.image_list == [fake_image]

    def test_write_records_with_media_store_externalizes(
        self, mock_storage, mock_adapter
    ):
        """When media_store is set, write_records externalizes media."""
        fake_image = MagicMock()
        record = make_memory_record(content="test", image_list=[fake_image])

        mock_media_store = MagicMock()
        mock_media_store.store_media.return_value = {
            "image_ref_0": "file:///cache/abc.png"
        }

        block = MultimodalVectorDBBlock(
            storage=mock_storage,
            embedding=mock_adapter,
            media_store=mock_media_store,
        )
        block.write_records([record], agent_id="agent_1")

        mock_media_store.store_media.assert_called_once()
        mock_storage.add.assert_called_once()

        # Verify the stored payload contains media_refs
        stored_records = mock_storage.add.call_args[0][0]
        assert len(stored_records) == 1

    def test_write_records_auto_caption_populates_text_summary(
        self, mock_storage, mock_adapter
    ):
        """Image records store generated caption in extra_info and embedding."""
        fake_image = MagicMock()
        record = make_memory_record(content="", image_list=[fake_image])
        caption_generator = MagicMock(return_value="a red car in the street")

        block = MultimodalVectorDBBlock(
            storage=mock_storage,
            embedding=mock_adapter,
            auto_caption=True,
            caption_generator=caption_generator,
        )
        block.write_records([record])

        caption_generator.assert_called_once_with(record)
        embed_message_arg = mock_adapter.embed_message.call_args[0][0]
        assert embed_message_arg.content == "a red car in the street"
        assert embed_message_arg.image_list == [fake_image]

        stored_records = mock_storage.add.call_args[0][0]
        payload = stored_records[0].payload
        assert payload["extra_info"]["text_summary"] == "a red car in the street"

    def test_write_records_auto_caption_appends_existing_text(
        self, mock_storage, mock_adapter
    ):
        """Generated captions are appended when the record already has text."""
        fake_image = MagicMock()
        record = make_memory_record(content="user note", image_list=[fake_image])
        caption_generator = MagicMock(return_value="a red car in the street")

        block = MultimodalVectorDBBlock(
            storage=mock_storage,
            embedding=mock_adapter,
            auto_caption=True,
            caption_generator=caption_generator,
        )
        block.write_records([record])

        embed_message_arg = mock_adapter.embed_message.call_args[0][0]
        assert embed_message_arg.content == (
            "user note\n\na red car in the street"
        )

    def test_write_records_auto_caption_ignores_blank_summary(
        self, mock_storage, mock_adapter
    ):
        """Blank captions are ignored and not persisted."""
        fake_image = MagicMock()
        record = make_memory_record(content="", image_list=[fake_image])
        caption_generator = MagicMock(return_value="   ")

        block = MultimodalVectorDBBlock(
            storage=mock_storage,
            embedding=mock_adapter,
            auto_caption=True,
            caption_generator=caption_generator,
        )
        block.write_records([record])

        embed_message_arg = mock_adapter.embed_message.call_args[0][0]
        assert embed_message_arg.content == ""
        stored_records = mock_storage.add.call_args[0][0]
        payload = stored_records[0].payload
        assert payload["extra_info"]["text_summary"] == ""

    def test_write_records_replaces_inline_media_with_uri_refs(
        self, mock_storage, mock_adapter
    ):
        """Externalized payload stores URI refs instead of inline base64."""
        fake_image = MagicMock()
        record = make_memory_record(content="test", image_list=[fake_image])

        mock_media_store = MagicMock()
        mock_media_store.store_media.return_value = {
            "image_ref_0": "file:///cache/abc.png"
        }

        block = MultimodalVectorDBBlock(
            storage=mock_storage,
            embedding=mock_adapter,
            media_store=mock_media_store,
        )
        block.write_records([record], agent_id="agent_1")

        stored_records = mock_storage.add.call_args[0][0]
        payload = stored_records[0].payload

        assert payload["message"]["image_list"] == [
            {"type": "url", "data": "file:///cache/abc.png"}
        ]
        assert payload["message"].get("video_bytes") is None
        assert payload["extra_info"]["media_refs"] == "[\"file:///cache/abc.png\"]"

    def test_write_records_audio_only_uses_audio_embedding(
        self, mock_storage, mock_adapter
    ):
        """Audio-only records are embedded through the audio branch."""
        record = make_memory_record(
            content="",
            audio_bytes=b"audio sample",
            audio_format="wav",
        )

        block = MultimodalVectorDBBlock(
            storage=mock_storage, embedding=mock_adapter
        )
        block.write_records([record])

        mock_adapter.embed_message.assert_called_once_with(b"audio sample")
        mock_storage.add.assert_called_once()

    def test_write_records_externalizes_audio_payload(
        self, mock_storage, mock_adapter
    ):
        """Audio payload stores refs instead of inline base64 when externalized."""
        record = make_memory_record(
            content="",
            audio_bytes=b"audio sample",
            audio_format="mp3",
        )

        mock_media_store = MagicMock()
        mock_media_store.store_media.return_value = {
            "audio_ref": "file:///cache/abc_audio.mp3"
        }

        block = MultimodalVectorDBBlock(
            storage=mock_storage,
            embedding=mock_adapter,
            media_store=mock_media_store,
        )
        block.write_records([record], agent_id="agent_1")

        payload = mock_storage.add.call_args[0][0][0].payload
        assert payload["message"].get("audio_bytes") is None
        assert payload["message"]["audio_format"] == "mp3"
        assert payload["extra_info"]["has_audio"] == "true"

    def test_write_records_filters_empty_records(
        self, mock_storage, mock_adapter
    ):
        """Records with no text AND no media are skipped."""
        record = make_memory_record(content="", image_list=None)
        record.message.video_bytes = None

        block = MultimodalVectorDBBlock(
            storage=mock_storage, embedding=mock_adapter
        )
        block.write_records([record])

        mock_adapter.embed_message.assert_not_called()
        mock_storage.add.assert_not_called()

    def test_write_records_filters_whitespace_only_content(
        self, mock_storage, mock_adapter
    ):
        """Records with only whitespace content are skipped."""
        record = make_memory_record(content="   ", image_list=None)

        block = MultimodalVectorDBBlock(
            storage=mock_storage, embedding=mock_adapter
        )
        block.write_records([record])

        mock_adapter.embed_message.assert_not_called()
        mock_storage.add.assert_not_called()

    def test_write_records_adds_valid_records_to_storage(
        self, mock_storage, mock_adapter
    ):
        """Valid records are added to storage as VectorRecords."""
        record = make_memory_record(content="hello world")
        mock_adapter.embed_message.return_value = [0.1] * 512

        block = MultimodalVectorDBBlock(
            storage=mock_storage, embedding=mock_adapter
        )
        block.write_records([record])

        mock_storage.add.assert_called_once()
        added = mock_storage.add.call_args[0][0]
        assert len(added) == 1
        assert isinstance(added[0], VectorRecord)
        assert added[0].vector == [0.1] * 512

    def test_write_records_adds_multimodal_metadata_to_extra_info(
        self, mock_storage, mock_adapter
    ):
        """write_records populates extra_info with modality metadata."""
        fake_image = MagicMock()
        record = make_memory_record(
            content="look at this", image_list=[fake_image]
        )

        block = MultimodalVectorDBBlock(
            storage=mock_storage, embedding=mock_adapter
        )
        block.write_records([record])

        added = mock_storage.add.call_args[0][0]
        payload = added[0].payload
        extra = payload.get("extra_info", {})

        # Metadata fields should be present
        assert "modalities" in extra
        assert "image_count" in extra


class TestMultimodalVectorDBBlockClear:
    """Tests for clear method."""

    def test_clear_calls_storage_clear(self, mock_storage, mock_adapter):
        """clear delegates to storage.clear()."""
        block = MultimodalVectorDBBlock(
            storage=mock_storage, embedding=mock_adapter
        )
        block.clear()
        mock_storage.clear.assert_called_once()

    def test_clear_clears_externalized_media_namespaces(
        self, mock_storage, mock_adapter
    ):
        """clear also removes externalized media for touched agent IDs."""
        fake_image = MagicMock()
        record = make_memory_record(content="test", image_list=[fake_image])

        mock_media_store = MagicMock()
        mock_media_store.store_media.return_value = {
            "image_ref_0": "file:///cache/abc.png"
        }

        block = MultimodalVectorDBBlock(
            storage=mock_storage,
            embedding=mock_adapter,
            media_store=mock_media_store,
        )
        block.write_records([record], agent_id="agent_1")
        block.write_records([record], agent_id="")

        block.clear()

        mock_storage.clear.assert_called_once()
        mock_media_store.clear.assert_any_call(agent_id="agent_1")
        mock_media_store.clear.assert_any_call(agent_id="default")


class TestMultimodalVectorDBBlockClose:
    """Tests for close method."""

    def test_close_closes_media_store(self, mock_storage, mock_adapter):
        """close delegates to the external media store when configured."""
        mock_media_store = MagicMock()
        block = MultimodalVectorDBBlock(
            storage=mock_storage,
            embedding=mock_adapter,
            media_store=mock_media_store,
        )

        block.close()

        mock_media_store.close.assert_called_once()
