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

"""Tests for MultimodalAgentMemory."""

from pathlib import Path
from unittest.mock import MagicMock, create_autospec, patch

import pytest

from camel.memories import MultimodalAgentMemory
from camel.memories.base import BaseContextCreator
from camel.memories.context_creators.multimodal import MultimodalContextCreator
from camel.memories.blocks import ChatHistoryBlock, MultimodalVectorDBBlock
from camel.memories.media_asset_store import MediaAssetStore
from camel.memories.records import ContextRecord, MemoryRecord
from camel.messages import BaseMessage
from camel.storages import BaseVectorStorage, VectorDBQueryResult
from camel.types import OpenAIBackendRole, RoleType
from camel.utils import BaseTokenCounter
from camel.embeddings.multimodal_adapter import MultimodalEmbeddingAdapter


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture
def mock_chat_history_block():
    return MagicMock(spec=ChatHistoryBlock)


@pytest.fixture
def mock_multimodal_vector_block():
    return MagicMock(spec=MultimodalVectorDBBlock)


@pytest.fixture
def mock_context_creator():
    return MagicMock(spec=BaseContextCreator)


def make_memory_record(
    content: str = "hello",
    role_backend=OpenAIBackendRole.USER,
    image_list=None,
    audio_bytes=None,
) -> MemoryRecord:
    return MemoryRecord(
        message=BaseMessage(
            role_name="user",
            role_type=RoleType.USER,
            meta_dict=None,
            content=content,
            image_list=image_list,
            audio_bytes=audio_bytes,
        ),
        role_at_backend=role_backend,
        agent_id="test_agent",
    )


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

class TestMultimodalAgentMemoryInit:
    """Tests for __init__."""

    def test_init_with_default_components(self, mock_context_creator):
        """Default construction creates ChatHistoryBlock and MultimodalVectorDBBlock."""
        # Mock both internal default components to avoid QdrantStorage import
        mock_vector_block = MagicMock(spec=MultimodalVectorDBBlock)
        with patch(
            "camel.memories.agent_memories.MultimodalVectorDBBlock",
            return_value=mock_vector_block,
        ):
            memory = MultimodalAgentMemory(mock_context_creator)
            assert memory.chat_history_block is not None
            assert memory.multimodal_vector_block is mock_vector_block
            assert memory.retrieve_limit == 3

    def test_init_with_custom_components(
        self,
        mock_chat_history_block,
        mock_multimodal_vector_block,
        mock_context_creator,
    ):
        """Custom blocks are used when provided."""
        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            multimodal_vector_block=mock_multimodal_vector_block,
        )
        assert memory.chat_history_block is mock_chat_history_block
        assert memory.multimodal_vector_block is mock_multimodal_vector_block
        assert memory.retrieve_limit == 3

    def test_init_sets_retrieve_limit(self, mock_context_creator):
        """retrieve_limit is configurable."""
        # Provide mock blocks to avoid QdrantStorage dependency
        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=MagicMock(spec=ChatHistoryBlock),
            multimodal_vector_block=MagicMock(spec=MultimodalVectorDBBlock),
            retrieve_limit=5,
        )
        assert memory.retrieve_limit == 5

    def test_init_sets_agent_id(self, mock_context_creator):
        """agent_id is stored."""
        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=MagicMock(spec=ChatHistoryBlock),
            multimodal_vector_block=MagicMock(spec=MultimodalVectorDBBlock),
            agent_id="my_agent",
        )
        assert memory.agent_id == "my_agent"

    def test_init_binds_media_store_to_multimodal_context_creator(self):
        """MultimodalContextCreator inherits the vector block media store."""
        token_counter = MagicMock(spec=BaseTokenCounter)
        creator = MultimodalContextCreator(token_counter, token_limit=4096)
        media_store = MagicMock()
        vector_block = MagicMock(spec=MultimodalVectorDBBlock)
        vector_block.media_store = media_store

        MultimodalAgentMemory(
            creator,
            chat_history_block=MagicMock(spec=ChatHistoryBlock),
            multimodal_vector_block=vector_block,
        )

        assert creator.media_store is media_store


class TestMultimodalAgentMemoryRetrieve:
    """Tests for retrieve method."""

    def test_retrieve_uses_text_topic_as_query(
        self,
        mock_chat_history_block,
        mock_multimodal_vector_block,
        mock_context_creator,
    ):
        """Text topic from USER message is used for vector retrieval."""
        mock_chat_history_block.retrieve.return_value = []
        mock_multimodal_vector_block.retrieve.return_value = []

        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            multimodal_vector_block=mock_multimodal_vector_block,
        )

        # Write a USER record to set _current_topic
        record = make_memory_record(content="what is this")
        memory.write_records([record])

        memory.retrieve()

        mock_multimodal_vector_block.retrieve.assert_called_with(
            "what is this", limit=3
        )

    def test_retrieve_uses_image_when_topic_is_empty(
        self,
        mock_chat_history_block,
        mock_multimodal_vector_block,
        mock_context_creator,
    ):
        """When _current_topic is empty, first image is used as query."""
        mock_chat_history_block.retrieve.return_value = []
        mock_multimodal_vector_block.retrieve.return_value = []

        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            multimodal_vector_block=mock_multimodal_vector_block,
        )

        fake_image = MagicMock()
        record = make_memory_record(
            content="", image_list=[fake_image]
        )
        memory.write_records([record])
        memory.retrieve()

        mock_multimodal_vector_block.retrieve.assert_called_with(
            fake_image, limit=3
        )

    def test_retrieve_falls_back_to_space_when_no_topic(
        self,
        mock_chat_history_block,
        mock_multimodal_vector_block,
        mock_context_creator,
    ):
        """When both topic and images are empty, uses a space query."""
        mock_chat_history_block.retrieve.return_value = []
        mock_multimodal_vector_block.retrieve.return_value = []

        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            multimodal_vector_block=mock_multimodal_vector_block,
        )

        memory.retrieve()  # No records written

        mock_multimodal_vector_block.retrieve.assert_called_with(
            " ", limit=3
        )

    def test_retrieve_uses_audio_when_text_and_image_are_empty(
        self,
        mock_chat_history_block,
        mock_multimodal_vector_block,
        mock_context_creator,
    ):
        """When text and images are empty, audio bytes are used as query."""
        mock_chat_history_block.retrieve.return_value = []
        mock_multimodal_vector_block.retrieve.return_value = []

        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            multimodal_vector_block=mock_multimodal_vector_block,
        )

        audio_bytes = b"voice note"
        record = make_memory_record(content="", audio_bytes=audio_bytes)
        memory.write_records([record])
        memory.retrieve()

        mock_multimodal_vector_block.retrieve.assert_called_with(
            audio_bytes, limit=3
        )

    def test_retrieve_interleaves_chat_and_vector_results(
        self,
        mock_chat_history_block,
        mock_multimodal_vector_block,
        mock_context_creator,
    ):
        """Pattern: chat[:1] + vector_results + chat[1:]."""
        system_record = ContextRecord(
            memory_record=make_memory_record(
                content="You are a helpful assistant",
                role_backend=OpenAIBackendRole.SYSTEM,
            ),
            score=1.0,
        )
        user_record = ContextRecord(
            memory_record=make_memory_record(content="Hello"),
            score=0.9,
        )
        mock_chat_history_block.retrieve.return_value = [
            system_record,
            user_record,
        ]

        vec_record = ContextRecord(
            memory_record=make_memory_record(content="past context"),
            score=0.8,
        )
        mock_multimodal_vector_block.retrieve.return_value = [vec_record]

        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            multimodal_vector_block=mock_multimodal_vector_block,
        )

        results = memory.retrieve()

        # Expected order: system + vector + user
        assert results[0] is system_record
        assert results[1] is vec_record
        assert results[2] is user_record


class TestMultimodalAgentMemoryWriteRecords:
    """Tests for write_records method."""

    def test_write_records_writes_to_both_blocks(
        self,
        mock_chat_history_block,
        mock_multimodal_vector_block,
        mock_context_creator,
    ):
        """write_records delegates to both chat_history and vector blocks."""
        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            multimodal_vector_block=mock_multimodal_vector_block,
        )

        record = make_memory_record(content="test message")
        memory.write_records([record])

        mock_chat_history_block.write_records.assert_called_once_with([record])
        mock_multimodal_vector_block.write_records.assert_called_once()

    def test_write_records_tracks_text_topic(
        self,
        mock_chat_history_block,
        mock_multimodal_vector_block,
        mock_context_creator,
    ):
        """USER message content sets _current_topic."""
        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            multimodal_vector_block=mock_multimodal_vector_block,
        )

        record = make_memory_record(content="user query about cats")
        memory.write_records([record])

        assert memory._current_topic == "user query about cats"
        assert memory._current_query_images == []
        assert memory._current_query_audio is None

    def test_write_records_tracks_image_when_no_text(
        self,
        mock_chat_history_block,
        mock_multimodal_vector_block,
        mock_context_creator,
    ):
        """Image-only USER message sets _current_query_images."""
        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            multimodal_vector_block=mock_multimodal_vector_block,
        )

        fake_image = MagicMock()
        record = make_memory_record(content="", image_list=[fake_image])
        memory.write_records([record])

        assert memory._current_topic == ""
        assert memory._current_query_images == [fake_image]
        assert memory._current_query_audio is None

    def test_write_records_tracks_audio_when_no_text_or_image(
        self,
        mock_chat_history_block,
        mock_multimodal_vector_block,
        mock_context_creator,
    ):
        """Audio-only USER message sets _current_query_audio."""
        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            multimodal_vector_block=mock_multimodal_vector_block,
        )

        audio_bytes = b"voice note"
        record = make_memory_record(content="", audio_bytes=audio_bytes)
        memory.write_records([record])

        assert memory._current_topic == ""
        assert memory._current_query_images == []
        assert memory._current_query_audio == audio_bytes

    def test_write_records_clears_images_when_text_topic_set(
        self,
        mock_chat_history_block,
        mock_multimodal_vector_block,
        mock_context_creator,
    ):
        """Subsequent USER message with text clears _current_query_images."""
        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            multimodal_vector_block=mock_multimodal_vector_block,
        )

        # First: image-only message
        fake_image = MagicMock()
        memory.write_records([make_memory_record(content="", image_list=[fake_image])])
        assert memory._current_query_images == [fake_image]

        # Second: text message
        memory.write_records(
            [make_memory_record(content="new topic")]
        )
        assert memory._current_topic == "new topic"
        assert memory._current_query_images == []
        assert memory._current_query_audio is None

    def test_write_records_audio_clears_existing_image_query(
        self,
        mock_chat_history_block,
        mock_multimodal_vector_block,
        mock_context_creator,
    ):
        """Audio-only USER message clears previous image query state."""
        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            multimodal_vector_block=mock_multimodal_vector_block,
        )

        fake_image = MagicMock()
        memory.write_records([make_memory_record(content="", image_list=[fake_image])])
        assert memory._current_query_images == [fake_image]

        audio_bytes = b"voice note"
        memory.write_records([make_memory_record(content="", audio_bytes=audio_bytes)])

        assert memory._current_topic == ""
        assert memory._current_query_images == []
        assert memory._current_query_audio == audio_bytes

    def test_write_records_propagates_agent_id(
        self,
        mock_chat_history_block,
        mock_multimodal_vector_block,
        mock_context_creator,
    ):
        """Agent ID is propagated to records without one."""
        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            multimodal_vector_block=mock_multimodal_vector_block,
            agent_id="my_agent_id",
        )

        record = make_memory_record(content="test")
        record.agent_id = ""  # Empty agent_id
        memory.write_records([record])

        written = mock_chat_history_block.write_records.call_args[0][0]
        assert written[0].agent_id == "my_agent_id"


class TestMultimodalAgentMemoryClear:
    """Tests for clear method."""

    def test_clear_clears_both_blocks(
        self,
        mock_chat_history_block,
        mock_multimodal_vector_block,
        mock_context_creator,
    ):
        """clear delegates to both blocks and resets topic state."""
        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            multimodal_vector_block=mock_multimodal_vector_block,
        )
        # Set state
        memory._current_topic = "old topic"
        memory._current_query_images = [MagicMock()]
        memory._current_query_audio = b"voice note"

        memory.clear()

        mock_chat_history_block.clear.assert_called_once()
        mock_multimodal_vector_block.clear.assert_called_once()
        assert memory._current_topic == ""
        assert memory._current_query_images == []
        assert memory._current_query_audio is None

    def test_close_closes_multimodal_vector_block(
        self,
        mock_chat_history_block,
        mock_multimodal_vector_block,
        mock_context_creator,
    ):
        """close delegates to the multimodal vector block."""
        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            multimodal_vector_block=mock_multimodal_vector_block,
        )

        memory.close()

        mock_multimodal_vector_block.close.assert_called_once()


class TestMultimodalAgentMemoryAgentId:
    """Tests for agent_id property."""

    def test_agent_id_setter(
        self, mock_chat_history_block, mock_multimodal_vector_block,
        mock_context_creator
    ):
        """agent_id can be set after construction."""
        memory = MultimodalAgentMemory(
            mock_context_creator,
            chat_history_block=mock_chat_history_block,
            multimodal_vector_block=mock_multimodal_vector_block,
        )
        memory.agent_id = "new_id"
        assert memory.agent_id == "new_id"


class TestMultimodalAgentMemoryIntegration:
    """Integration tests for Phase 1 multimodal memory flow."""

    def test_get_context_restores_externalized_media(self, tmp_path):
        """Write -> retrieve -> create_context works with externalized media."""
        token_counter = MagicMock(spec=BaseTokenCounter)
        token_counter.count_tokens_from_messages.return_value = 42
        media_store = MediaAssetStore(
            local_cache_dir=str(tmp_path / "media_cache")
        )
        storage = create_autospec(BaseVectorStorage)
        adapter = MagicMock(spec=MultimodalEmbeddingAdapter)
        adapter.get_output_dim.return_value = 512
        adapter.embed_message.return_value = [0.1] * 512
        adapter.embed_query.return_value = [0.1] * 512
        stored_records = []

        def add_records(records):
            stored_records.extend(records)

        def query_records(_query):
            return [
                VectorDBQueryResult.create(
                    similarity=0.9,
                    vector=stored_records[0].vector,
                    id=stored_records[0].id,
                    payload=stored_records[0].payload,
                )
            ]

        storage.add.side_effect = add_records
        storage.query.side_effect = query_records

        vector_block = MultimodalVectorDBBlock(
            storage=storage,
            embedding=adapter,
            media_store=media_store,
        )
        context_creator = MultimodalContextCreator(
            token_counter=token_counter,
            token_limit=4096,
        )
        memory = MultimodalAgentMemory(
            context_creator=context_creator,
            chat_history_block=ChatHistoryBlock(),
            multimodal_vector_block=vector_block,
            agent_id="agent_1",
        )

        from PIL import Image

        image = Image.new("RGB", (10, 10), color="green")
        record = make_memory_record(content="look at this", image_list=[image])
        record.agent_id = ""

        memory.write_records([record])
        messages, token_count = memory.get_context()

        assert token_count == 42
        assert context_creator.media_store is media_store
        assert stored_records[0].payload["message"]["image_list"][0]["type"] == "url"
        assert stored_records[0].payload["message"]["image_list"][0][
            "data"
        ].startswith("file://")

        user_messages = [msg for msg in messages if msg["role"] == "user"]
        assert user_messages
        assert any(isinstance(msg["content"], list) for msg in user_messages)
        multimodal_message = next(
            msg for msg in user_messages if isinstance(msg["content"], list)
        )
        assert any(
            part.get("type") == "image_url"
            for part in multimodal_message["content"]
            if isinstance(part, dict)
        )
